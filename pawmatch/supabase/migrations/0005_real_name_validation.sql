-- Enforce plausible human names at the database boundary as well as in the UI.
-- This validates format, not legal identity.
-- The '' (empty) case stays allowed: 0003's new-user trigger creates a draft
-- profile with name = '' before the person has filled anything in, and
-- enforce_profile_completeness() already refuses to mark that profile complete
-- until a real plausible name is set.

create or replace function public.is_plausible_person_name(value text) returns boolean
language sql
immutable
as $$
  select
    value is not null
    and char_length(btrim(value)) between 2 and 40
    and (
      btrim(value) ~ '^[A-Za-z]{2,}( [A-Za-z]{2,}){0,2}$'
      or btrim(value) ~ '^[א-ת]{2,}( [א-ת]{2,}){0,2}$'
      or btrim(value) ~ '^[А-Яа-яЁё]{2,}( [А-Яа-яЁё]{2,}){0,2}$'
      or btrim(value) ~ '^[ء-ي]{2,}( [ء-ي]{2,}){0,2}$'
    )
    and lower(btrim(value)) !~ '(^| )(test|testing|admin|administrator|user|qwerty|asdf|zxcv|xxx|abc|unknown|fake|none|noname|anonymous|anon|טסט|בדיקה|משתמש|אדמין|פלוני|אלמוני|שם)( |$)'
    and btrim(value) !~* '(.)\1\1';
$$;

revoke all on function public.is_plausible_person_name(text) from public;
grant execute on function public.is_plausible_person_name(text) to authenticated;

alter table public.profiles
  drop constraint if exists profiles_plausible_name_check;
alter table public.profiles
  add constraint profiles_plausible_name_check
  check (btrim(name) = '' or public.is_plausible_person_name(name));

create or replace function public.enforce_profile_completeness() returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  new.is_complete := (
    public.is_plausible_person_name(new.name)
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

-- Re-evaluate existing profiles. Invalid-name profiles become incomplete.
update public.profiles set is_complete = is_complete;
