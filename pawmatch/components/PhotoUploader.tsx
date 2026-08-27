import { useState } from "react";
import * as ImagePicker from "expo-image-picker";
import { decode } from "base64-arraybuffer";
import { Alert, Image, Pressable, StyleSheet, Text, View } from "react-native";
import { supabase } from "@/lib/supabase";
import type { PhotoKind, ProfilePhoto } from "@/lib/types";

interface PhotoUploaderProps {
  kind: PhotoKind;
  label: string;
  profileId: string;
  photos: ProfilePhoto[];
  onChanged: () => void;
}

export function PhotoUploader({ kind, label, profileId, photos, onChanged }: PhotoUploaderProps) {
  const [uploading, setUploading] = useState(false);
  const kindPhotos = photos.filter((photo) => photo.kind === kind);

  async function pickAndUpload() {
    const permission = await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      Alert.alert("צריך הרשאה לגלריה כדי להעלות תמונה");
      return;
    }

    const result = await ImagePicker.launchImageLibraryAsync({
      mediaTypes: ImagePicker.MediaTypeOptions.Images,
      quality: 0.8,
      base64: true,
    });

    if (result.canceled || !result.assets[0]?.base64) {
      return;
    }

    setUploading(true);
    try {
      const asset = result.assets[0];
      const extension = asset.uri.split(".").pop()?.toLowerCase() ?? "jpg";
      const path = `${kind}/${profileId}/${Date.now()}.${extension}`;

      const { error: uploadError } = await supabase.storage
        .from("profile-photos")
        .upload(path, decode(asset.base64!), { contentType: `image/${extension}` });
      if (uploadError) throw uploadError;

      const { data: publicUrl } = supabase.storage.from("profile-photos").getPublicUrl(path);

      const { error: insertError } = await supabase.from("profile_photos").insert({
        profile_id: profileId,
        url: publicUrl.publicUrl,
        kind,
        position: kindPhotos.length,
      });
      if (insertError) throw insertError;

      onChanged();
    } catch (err) {
      Alert.alert("העלאת התמונה נכשלה", err instanceof Error ? err.message : String(err));
    } finally {
      setUploading(false);
    }
  }

  async function removePhoto(photo: ProfilePhoto) {
    const { error } = await supabase.from("profile_photos").delete().eq("id", photo.id);
    if (error) {
      Alert.alert("מחיקת התמונה נכשלה", error.message);
      return;
    }
    onChanged();
  }

  return (
    <View style={styles.container}>
      <Text style={styles.label}>{label} {kindPhotos.length === 0 ? "(חובה)" : ""}</Text>
      <View style={styles.row}>
        {kindPhotos.map((photo) => (
          <Pressable key={photo.id} onLongPress={() => removePhoto(photo)}>
            <Image source={{ uri: photo.url }} style={styles.thumb} />
          </Pressable>
        ))}
        <Pressable style={styles.addButton} onPress={pickAndUpload} disabled={uploading}>
          <Text style={styles.addButtonText}>{uploading ? "..." : "+"}</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: { marginBottom: 16 },
  label: { fontSize: 14, fontWeight: "600", marginBottom: 8 },
  row: { flexDirection: "row", gap: 8, flexWrap: "wrap" },
  thumb: { width: 72, height: 72, borderRadius: 8 },
  addButton: {
    width: 72,
    height: 72,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: "#ccc",
    borderStyle: "dashed",
    alignItems: "center",
    justifyContent: "center",
  },
  addButtonText: { fontSize: 24, color: "#999" },
});
