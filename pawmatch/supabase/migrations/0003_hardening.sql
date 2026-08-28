-- PawMatch hardening and correctness fixes.

-- ---------------------------------------------------------------------------
-- Draft profiles + age gate
-- ---------------------------------------------------------------------------
-- A newly authenticated user needs a profile row before profile_photos can satisfy
-- its foreign key. Allow an empty name while the profile is still a draft.
alter table profiles drop constraint if exists profiles_name_check;
alter table profiles drop constraint if exists profiles_name_length_check;
alter table profiles add constraint profiles_name_length_check check (char_length(name) <= 60);

alter table profiles drop constraint if exists profiles_birthdate_check;
alter table profiles add constraint profiles_birthdate_check
  check (birthdate is null or birthdate <= current_date);

create or replace function public.handle_new_user_profile() returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, name)
  values (new.id, '')
  on conflict (id) do nothing;
  return new;
end;
$$;

revoke all on function public.handle_new_user_profile() from public;

drop trigger if exists on_auth_user_created_create_profile on auth.users;
create trigger on_auth_user_created_create_profile
  after insert on auth.users
  for each row execute function public.handle_new_user_profile();

-- Backfill users who signed up before this migration but never managed to create a profile.
insert into public.profiles (id, name)
select u.id, ''
from auth.users u
left join public.profiles p on p.id = u.id
where p.id is null
on conflict (id) do nothing;

-- is_complete is server-owned. It requires a name, an adult birthdate and both photo kinds.
create or replace function public.enforce_profile_completeness() returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  new.is_complete := (
    btrim(new.name) <> ''
    and new.birthdate is not null
    and new.birthdate <= (current_date - interval '18 years')::date
    and exists (
      select 1 from public.profile_photos
      where profile_id = new.id and kind = 'human'
    )
    and exists (
      select 1 from public.profile_photos
      where profile_id = new.id and kind = 'pet'
    )
  );
  return new;
end;
$$;

revoke all on function public.enforce_profile_completeness() from public;

drop trigger if exists profiles_enforce_completeness on public.profiles;
create trigger profiles_enforce_completeness
  before insert or update on public.profiles
  for each row execute function public.enforce_profile_completeness();

create or replace function public.recompute_profile_completeness() returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  target_profile_id uuid;
begin
  target_profile_id := coalesce(new.profile_id, old.profile_id);

  -- Any UPDATE invokes profiles_enforce_completeness, which calculates the value
  -- from trusted server-side state instead of accepting a client-supplied flag.
  update public.profiles
  set is_complete = is_complete
  where id = target_profile_id;

  return null;
end;
$$;

revoke all on function public.recompute_profile_completeness() from public;

-- Re-evaluate profiles created under the old photo-only completion rule.
update public.profiles set is_complete = is_complete;

-- ---------------------------------------------------------------------------
-- Private photo storage + cleanup metadata
-- ---------------------------------------------------------------------------
alter table public.profile_photos
  add column if not exists storage_path text;

update public.profile_photos
set storage_path = regexp_replace(
  url,
  '^.*/storage/v1/object/public/profile-photos/',
  ''
)
where storage_path is null
  and url like '%/storage/v1/object/public/profile-photos/%';

alter table public.profile_photos drop constraint if exists profile_photos_storage_path_owner_check;
alter table public.profile_photos add constraint profile_photos_storage_path_owner_check
  check (
    storage_path is null
    or (
      split_part(storage_path, '/', 1) = kind::text
      and split_part(storage_path, '/', 2) = profile_id::text
    )
  );

update storage.buckets
set public = false
where id = 'profile-photos';

drop policy if exists "profile photos are publicly readable" on storage.objects;
drop policy if exists "authenticated users can read profile photos" on storage.objects;

create policy "authenticated users can read profile photos"
  on storage.objects for select
  to authenticated
  using (
    bucket_id = 'profile-photos'
    and (
      (storage.foldername(name))[2] = auth.uid()::text
      or exists (
        select 1 from public.profile_photos pp
        where pp.storage_path = storage.objects.name
      )
    )
  );

-- ---------------------------------------------------------------------------
-- RLS + public projection: exact birthdate stays visible only to its owner.
-- Other users consume visible_profiles, which intentionally excludes birthdate.
-- ---------------------------------------------------------------------------
drop policy if exists "profiles are readable by any authenticated user" on public.profiles;
drop policy if exists "profiles visible to owner discoverable users and matches" on public.profiles;
drop policy if exists "users read their own profile" on public.profiles;

create policy "users read their own profile"
  on public.profiles for select
  to authenticated
  using (id = auth.uid());

drop view if exists public.visible_profiles;
create view public.visible_profiles
with (security_barrier = true)
as
select
  p.id,
  p.name,
  p.bio,
  p.pet_name,
  p.pet_type,
  p.is_complete,
  p.created_at
from public.profiles p
where p.id = auth.uid()
   or p.is_complete
   or exists (
     select 1 from public.matches m
     where (m.user_a = auth.uid() and m.user_b = p.id)
        or (m.user_b = auth.uid() and m.user_a = p.id)
   );

revoke all on public.visible_profiles from public;
grant select on public.visible_profiles to authenticated;

-- Candidate retrieval is done server-side so the client never builds a huge NOT IN
-- URL from the user's entire swipe history.
create or replace function public.get_swipe_candidates(
  p_pet_type text default '',
  p_limit integer default 20
)
returns table (
  id uuid,
  name text,
  bio text,
  pet_name text,
  pet_type text,
  is_complete boolean,
  created_at timestamptz
)
language sql
stable
security definer
set search_path = public
as $$
  select
    p.id,
    p.name,
    p.bio,
    p.pet_name,
    p.pet_type,
    p.is_complete,
    p.created_at
  from public.profiles p
  where auth.uid() is not null
    and p.id <> auth.uid()
    and p.is_complete
    and not exists (
      select 1 from public.swipes s
      where s.swiper_id = auth.uid()
        and s.swiped_id = p.id
    )
    and (
      coalesce(btrim(p_pet_type), '') = ''
      or p.pet_type ilike ('%' || p_pet_type || '%')
    )
  order by p.created_at desc
  limit least(greatest(p_limit, 1), 50);
$$;

revoke all on function public.get_swipe_candidates(text, integer) from public;
grant execute on function public.get_swipe_candidates(text, integer) to authenticated;

drop policy if exists "photos are readable by any authenticated user" on public.profile_photos;
drop policy if exists "photos visible with their profile" on public.profile_photos;
create policy "photos visible with their profile"
  on public.profile_photos for select
  to authenticated
  using (
    profile_id = auth.uid()
    or exists (
      select 1 from public.visible_profiles vp
      where vp.id = profile_photos.profile_id
    )
  );

-- Harden the mutual-match trigger function's search path.
create or replace function public.create_match_on_mutual_like() returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  reciprocal_like_exists boolean;
  lo uuid;
  hi uuid;
begin
  if new.direction <> 'like' then
    return new;
  end if;

  select exists (
    select 1 from public.swipes
    where swiper_id = new.swiped_id
      and swiped_id = new.swiper_id
      and direction = 'like'
  ) into reciprocal_like_exists;

  if reciprocal_like_exists then
    if new.swiper_id < new.swiped_id then
      lo := new.swiper_id;
      hi := new.swiped_id;
    else
      lo := new.swiped_id;
      hi := new.swiper_id;
    end if;

    insert into public.matches (user_a, user_b)
    values (lo, hi)
    on conflict (user_a, user_b) do nothing;
  end if;

  return new;
end;
$$;

revoke all on function public.create_match_on_mutual_like() from public;

-- ---------------------------------------------------------------------------
-- Realtime + indexes used by hot paths
-- ---------------------------------------------------------------------------
create index if not exists profile_photos_profile_id_idx
  on public.profile_photos (profile_id, position);
create index if not exists matches_user_b_created_at_idx
  on public.matches (user_b, created_at desc);
create index if not exists messages_match_id_created_at_idx
  on public.messages (match_id, created_at);

do $$
begin
  if exists (select 1 from pg_publication where pubname = 'supabase_realtime')
     and not exists (
       select 1 from pg_publication_tables
       where pubname = 'supabase_realtime'
         and schemaname = 'public'
         and tablename = 'messages'
     ) then
    alter publication supabase_realtime add table public.messages;
  end if;
end $$;
