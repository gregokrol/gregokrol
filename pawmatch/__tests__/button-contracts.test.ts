import fs from 'fs';
import path from 'path';

const projectRoot = path.resolve(__dirname, '..');

function read(relPath: string) {
  return fs.readFileSync(path.join(projectRoot, relPath), 'utf8');
}

describe('button contracts', () => {
  it('welcome screen primary and secondary CTA buttons navigate to sign-up and sign-in', () => {
    const content = read('app/welcome.tsx');
    expect(content).toContain("router.push('/(auth)/sign-up')");
    expect(content).toContain("router.push('/(auth)/sign-in')");
  });

  it('sign-in screen submits credentials on button press', () => {
    const content = read('app/(auth)/sign-in.tsx');
    expect(content).toContain('onPress={handleSignIn}');
  });

  it('sign-up screen submits credentials on button press', () => {
    const content = read('app/(auth)/sign-up.tsx');
    expect(content).toContain('onPress={handleSignUp}');
  });

  it('swipe screen keeps both pass and like actions wired', () => {
    const content = read('app/(tabs)/swipe.tsx');
    expect(content).toContain("handleSwipe('pass')");
    expect(content).toContain("handleSwipe('like')");
    expect(content).toContain('onPress={() => void loadCandidates(petTypeQuery)}');
  });

  it('profile screen save and sign-out buttons stay wired', () => {
    const content = read('app/(tabs)/profile.tsx');
    expect(content).toContain('onPress={handleSave}');
    expect(content).toContain('onPress={handleSignOut}');
  });

  it('chat screen send button stays wired and guarded against empty drafts', () => {
    const content = read('app/chat/[matchId].tsx');
    expect(content).toContain('onPress={handleSend}');
    expect(content).toContain('draft.trim().length === 0');
  });

  it('photo uploader keeps add and remove actions wired', () => {
    const content = read('components/PhotoUploader.tsx');
    expect(content).toContain('onPress={pickAndUpload}');
    expect(content).toContain('onLongPress={() => confirmRemove(photo)}');
  });
});
