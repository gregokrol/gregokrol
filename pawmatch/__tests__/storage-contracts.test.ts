import fs from 'fs';
import path from 'path';

const root = path.resolve(__dirname, '..');
const uploader = fs.readFileSync(path.join(root, 'components/PhotoUploader.tsx'), 'utf8');
const hardening = fs.readFileSync(path.join(root, 'supabase/migrations/0003_hardening.sql'), 'utf8');
const acceptance = fs.readFileSync(path.join(root, 'supabase/migrations/0004_acceptance_hardening.sql'), 'utf8');

describe('storage and DB security contracts', () => {
  it('uploads to <kind>/<user-id>/<file> to match RLS and DB constraints', () => {
    expect(uploader).toContain('`${kind}/${profileId}/${Date.now()}.${ext}`');
    expect(hardening).toContain("split_part(storage_path, '/', 1) = kind::text");
    expect(hardening).toContain("split_part(storage_path, '/', 2) = profile_id::text");
  });

  it('keeps profile photos private', () => {
    expect(hardening).toContain("set public = false");
    expect(hardening).toContain('authenticated users can read profile photos');
  });

  it('requires pet identity fields for a complete profile', () => {
    expect(acceptance).toContain("btrim(new.pet_name) <> ''");
    expect(acceptance).toContain("btrim(new.pet_type) <> ''");
  });

  it('blocks API swipes for incomplete users and targets', () => {
    expect(acceptance).toContain('me.is_complete');
    expect(acceptance).toContain('target.is_complete');
  });

  it('rejects whitespace-only DB messages', () => {
    expect(acceptance).toContain('char_length(btrim(content)) between 1 and 1000');
  });
});
