import { useState } from 'react';
import { Alert, Image, Pressable, StyleSheet, Text, View } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { decode } from 'base64-arraybuffer';
import { MAX_IMAGE_BYTES, MAX_PHOTOS_PER_KIND, base64DecodedByteLength } from '@/lib/logic';
import { supabase } from '@/lib/supabase';
import type { PhotoKind, ProfilePhoto } from '@/lib/types';
import { colors, radii, spacing } from '@/lib/theme';

interface PhotoUploaderProps {
  kind: PhotoKind;
  label: string;
  profileId: string;
  photos: ProfilePhoto[];
  onChanged: () => Promise<void>;
}

function getStoragePath(photo: ProfilePhoto): string | null {
  return photo.storage_path ?? null;
}

export function PhotoUploader({ kind, label, profileId, photos, onChanged }: PhotoUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const kindPhotos = photos.filter((photo) => photo.kind === kind);
  const atLimit = kindPhotos.length >= MAX_PHOTOS_PER_KIND;

  async function pickAndUpload() {
    if (atLimit || uploading) return;

    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert('אין הרשאה', 'יש לאפשר גישה לגלריה כדי להעלות תמונה.');
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ['images'],
      allowsEditing: true,
      quality: 0.8,
      base64: true,
    });

    if (result.canceled) return;
    const asset = result.assets[0];
    if (!asset.base64) {
      Alert.alert('שגיאה', 'לא התקבל תוכן תמונה.');
      return;
    }
    if (base64DecodedByteLength(asset.base64) > MAX_IMAGE_BYTES) {
      Alert.alert('התמונה גדולה מדי', 'יש לבחור תמונה בגודל של עד 8MB.');
      return;
    }

    const ext = asset.mimeType?.split('/')[1] ?? 'jpg';
    const path = `${kind}/${profileId}/${Date.now()}.${ext}`;
    let uploadedPath: string | null = null;

    try {
      setUploading(true);

      const { error: profileEnsureError } = await supabase.from('profiles').upsert({ id: profileId });
      if (profileEnsureError) throw profileEnsureError;

      const { error: uploadError } = await supabase.storage.from('profile-photos').upload(path, decode(asset.base64), {
        contentType: asset.mimeType ?? 'image/jpeg',
        upsert: false,
      });
      if (uploadError) throw uploadError;
      uploadedPath = path;

      const { error: insertError } = await supabase.from('profile_photos').insert({
        profile_id: profileId,
        url: path,
        storage_path: path,
        kind,
        position: kindPhotos.length,
      });
      if (insertError) throw insertError;

      await onChanged();
    } catch (err) {
      if (uploadedPath) {
        await supabase.storage.from('profile-photos').remove([uploadedPath]);
      }
      Alert.alert('העלאת התמונה נכשלה', err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }

  function confirmRemove(photo: ProfilePhoto) {
    Alert.alert('מחיקת תמונה', 'למחוק את התמונה?', [
      { text: 'ביטול', style: 'cancel' },
      { text: 'מחיקה', style: 'destructive', onPress: () => void removePhoto(photo) },
    ]);
  }

  async function removePhoto(photo: ProfilePhoto) {
    const { error } = await supabase.from('profile_photos').delete().eq('id', photo.id);
    if (error) {
      Alert.alert('מחיקת התמונה נכשלה', error.message);
      return;
    }

    const storagePath = getStoragePath(photo);
    if (storagePath) {
      const { error: storageError } = await supabase.storage.from('profile-photos').remove([storagePath]);
      if (storageError) {
        Alert.alert('התמונה הוסרה מהפרופיל', 'נשאר קובץ ישן ב-Storage; מומלץ לנקות אותו בדשבורד.');
      }
    }

    await onChanged();
  }

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label} {kindPhotos.length === 0 ? '(חובה)' : `(${kindPhotos.length}/${MAX_PHOTOS_PER_KIND})`}</Text>
      <View style={styles.row}>
        {kindPhotos.map((photo) => (
          <Pressable key={photo.id} onLongPress={() => confirmRemove(photo)} accessibilityHint="לחיצה ארוכה למחיקה">
            <Image source={{ uri: photo.display_url ?? photo.url }} style={styles.thumb} />
          </Pressable>
        ))}
        {!atLimit && (
          <Pressable style={styles.addButton} onPress={pickAndUpload} disabled={uploading}>
            <Text style={styles.addButtonText}>{uploading ? '...' : '+'}</Text>
            <Text style={styles.addButtonHint}>הוספה</Text>
          </Pressable>
        )}
      </View>
      {kindPhotos.length > 0 ? <Text style={styles.hint}>לחיצה ארוכה על תמונה למחיקה</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginBottom: 6 },
  label: { fontSize: 14, fontWeight: '700', marginBottom: 8, color: colors.text },
  row: { flexDirection: 'row-reverse', gap: 10, flexWrap: 'wrap' },
  thumb: { width: 84, height: 84, borderRadius: radii.md, borderWidth: 1, borderColor: colors.border },
  addButton: {
    width: 84,
    height: 84,
    borderRadius: radii.md,
    borderWidth: 1.5,
    borderColor: colors.secondary,
    borderStyle: 'dashed',
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: colors.secondarySoft,
    gap: 2,
  },
  addButtonText: { fontSize: 26, color: colors.secondary, fontWeight: '700' },
  addButtonHint: { fontSize: 12, color: colors.secondary, fontWeight: '700' },
  hint: { marginTop: 6, fontSize: 12, color: colors.textMuted },
});
