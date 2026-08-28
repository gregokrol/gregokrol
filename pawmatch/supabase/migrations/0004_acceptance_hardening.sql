-- PawMatch acceptance hardening.
-- Rules validated by the acceptance suite:
-- * discovery requires an adult owner with a real pet profile
-- * one human photo + one pet photo are required
-- * incomplete users cannot swipe or be swiped on through the API
-- * blank messages are rejected even if a client bypasses the UI
-- * only one photo per required kind is accepted in the current MVP

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
    and btrim(new.pet_name) <> ''
    and btrim(new.pet_type) <> ''
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

-- Recompute all existing profiles using the stricter pet-owner rule.
update public.profiles set is_complete = is_complete;

-- Keep the MVP data model deterministic: exactly one current human and pet photo.
create or replace function public.enforce_single_photo_per_kind() returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  if exists (
    select 1
    from public.profile_photos
    where profile_id = new.profile_id
      and kind = new.kind
  ) then
    raise exception 'Only one % photo is allowed per profile', new.kind;
  end if;
  return new;
end;
$$;

revoke all on function public.enforce_single_photo_per_kind() from public;

drop trigger if exists profile_photos_single_kind on public.profile_photos;
create trigger profile_photos_single_kind
  before insert on public.profile_photos
  for each row execute function public.enforce_single_photo_per_kind();

-- A malicious or outdated client cannot swipe unless both profiles are eligible.
drop policy if exists "users create their own swipes" on public.swipes;
create policy "complete users swipe complete profiles"
  on public.swipes for insert
  to authenticated
  with check (
    auth.uid() = swiper_id
    and exists (
      select 1 from public.profiles me
      where me.id = auth.uid() and me.is_complete
    )
    and exists (
      select 1 from public.profiles target
      where target.id = swiped_id and target.is_complete
    )
  );

-- Reject whitespace-only messages even when bypassing the app UI.
alter table public.messages
  drop constraint if exists messages_nonblank_content_check;
alter table public.messages
  add constraint messages_nonblank_content_check
  check (char_length(btrim(content)) between 1 and 1000);
