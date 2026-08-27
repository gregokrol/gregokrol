-- PawMatch initial schema
-- People meet people; pet ownership (proven by a required pet photo) is the entry
-- requirement, not a thing being matched on its own.

create extension if not exists "pgcrypto";

-- ---------------------------------------------------------------------------
-- Profiles
-- ---------------------------------------------------------------------------
create table profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  name text not null check (char_length(name) between 1 and 60),
  birthdate date,
  bio text not null default '' check (char_length(bio) <= 500),
  pet_name text not null default '' check (char_length(pet_name) <= 60),
  pet_type text not null default '' check (char_length(pet_type) <= 60),
  is_complete boolean not null default false,
  created_at timestamptz not null default now()
);

alter table profiles enable row level security;

create policy "profiles are readable by any authenticated user"
  on profiles for select
  to authenticated
  using (true);

create policy "users manage their own profile"
  on profiles for insert
  to authenticated
  with check (auth.uid() = id);

create policy "users update their own profile"
  on profiles for update
  to authenticated
  using (auth.uid() = id)
  with check (auth.uid() = id);

-- ---------------------------------------------------------------------------
-- Profile photos (human + pet). is_complete is recomputed whenever these change.
-- ---------------------------------------------------------------------------
create type photo_kind as enum ('human', 'pet');

create table profile_photos (
  id uuid primary key default gen_random_uuid(),
  profile_id uuid not null references profiles (id) on delete cascade,
  url text not null,
  kind photo_kind not null,
  position integer not null default 0,
  created_at timestamptz not null default now()
);

alter table profile_photos enable row level security;

create policy "photos are readable by any authenticated user"
  on profile_photos for select
  to authenticated
  using (true);

create policy "users manage their own photos"
  on profile_photos for insert
  to authenticated
  with check (auth.uid() = profile_id);

create policy "users delete their own photos"
  on profile_photos for delete
  to authenticated
  using (auth.uid() = profile_id);

create or replace function recompute_profile_completeness() returns trigger as $$
declare
  target_profile_id uuid;
begin
  target_profile_id := coalesce(new.profile_id, old.profile_id);

  update profiles
  set is_complete = (
    exists (select 1 from profile_photos where profile_id = target_profile_id and kind = 'human')
    and exists (select 1 from profile_photos where profile_id = target_profile_id and kind = 'pet')
  )
  where id = target_profile_id;

  return null;
end;
$$ language plpgsql security definer;

create trigger profile_photos_recompute_completeness
  after insert or delete on profile_photos
  for each row execute function recompute_profile_completeness();

-- ---------------------------------------------------------------------------
-- Swipes + matches
-- ---------------------------------------------------------------------------
create type swipe_direction as enum ('like', 'pass');

create table swipes (
  id uuid primary key default gen_random_uuid(),
  swiper_id uuid not null references profiles (id) on delete cascade,
  swiped_id uuid not null references profiles (id) on delete cascade,
  direction swipe_direction not null,
  created_at timestamptz not null default now(),
  unique (swiper_id, swiped_id),
  check (swiper_id <> swiped_id)
);

alter table swipes enable row level security;

create policy "users see their own swipes"
  on swipes for select
  to authenticated
  using (auth.uid() = swiper_id);

create policy "users create their own swipes"
  on swipes for insert
  to authenticated
  with check (auth.uid() = swiper_id);

create table matches (
  id uuid primary key default gen_random_uuid(),
  user_a uuid not null references profiles (id) on delete cascade,
  user_b uuid not null references profiles (id) on delete cascade,
  created_at timestamptz not null default now(),
  unique (user_a, user_b),
  check (user_a < user_b)
);

alter table matches enable row level security;

create policy "matched users see their match"
  on matches for select
  to authenticated
  using (auth.uid() = user_a or auth.uid() = user_b);

-- A match forms the moment both sides have liked each other.
create or replace function create_match_on_mutual_like() returns trigger as $$
declare
  reciprocal_like_exists boolean;
  lo uuid;
  hi uuid;
begin
  if new.direction <> 'like' then
    return new;
  end if;

  select exists (
    select 1 from swipes
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

    insert into matches (user_a, user_b)
    values (lo, hi)
    on conflict (user_a, user_b) do nothing;
  end if;

  return new;
end;
$$ language plpgsql security definer;

create trigger swipes_create_match_on_mutual_like
  after insert on swipes
  for each row execute function create_match_on_mutual_like();

-- ---------------------------------------------------------------------------
-- Messages
-- ---------------------------------------------------------------------------
create table messages (
  id uuid primary key default gen_random_uuid(),
  match_id uuid not null references matches (id) on delete cascade,
  sender_id uuid not null references profiles (id) on delete cascade,
  content text not null check (char_length(content) between 1 and 1000),
  created_at timestamptz not null default now()
);

alter table messages enable row level security;

create policy "match participants read messages"
  on messages for select
  to authenticated
  using (
    exists (
      select 1 from matches
      where matches.id = messages.match_id
        and (matches.user_a = auth.uid() or matches.user_b = auth.uid())
    )
  );

create policy "match participants send messages"
  on messages for insert
  to authenticated
  with check (
    sender_id = auth.uid()
    and exists (
      select 1 from matches
      where matches.id = messages.match_id
        and (matches.user_a = auth.uid() or matches.user_b = auth.uid())
    )
  );

-- ---------------------------------------------------------------------------
-- Billing scaffolding (no payment gateway wired up yet — data model only)
-- ---------------------------------------------------------------------------
create table plans (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  price_cents integer not null default 0,
  is_active boolean not null default false
);

insert into plans (name, price_cents, is_active) values ('Free', 0, true);
insert into plans (name, price_cents, is_active) values ('Premium', 999, false);

create table coupons (
  id uuid primary key default gen_random_uuid(),
  code text not null unique check (char_length(code) between 3 and 32),
  discount_percent integer not null check (discount_percent between 1 and 100),
  is_active boolean not null default true,
  created_at timestamptz not null default now()
);

create type subscription_status as enum ('active', 'trialing', 'canceled');

create table user_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles (id) on delete cascade,
  plan_id uuid not null references plans (id),
  status subscription_status not null default 'active',
  discount_percent integer default 0 check (discount_percent between 0 and 100),
  coupon_id uuid references coupons (id),
  created_at timestamptz not null default now(),
  unique (user_id)
);

alter table plans enable row level security;
alter table coupons enable row level security;
alter table user_subscriptions enable row level security;

-- Plans/coupons are managed from the Supabase dashboard only (no admin UI in the MVP).
create policy "plans are readable by any authenticated user"
  on plans for select
  to authenticated
  using (true);

create policy "users read their own subscription"
  on user_subscriptions for select
  to authenticated
  using (auth.uid() = user_id);
