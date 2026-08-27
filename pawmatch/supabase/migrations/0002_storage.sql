-- Storage bucket for profile photos: <kind>/<user-id>/<filename>, kind in ('human', 'pet').
insert into storage.buckets (id, name, public)
values ('profile-photos', 'profile-photos', true)
on conflict (id) do nothing;

create policy "profile photos are publicly readable"
  on storage.objects for select
  using (bucket_id = 'profile-photos');

create policy "users upload photos into their own folder"
  on storage.objects for insert
  to authenticated
  with check (
    bucket_id = 'profile-photos'
    and (storage.foldername(name))[2] = auth.uid()::text
  );

create policy "users delete their own photos"
  on storage.objects for delete
  to authenticated
  using (
    bucket_id = 'profile-photos'
    and (storage.foldername(name))[2] = auth.uid()::text
  );
