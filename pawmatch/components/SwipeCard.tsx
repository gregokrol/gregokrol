import { Image, StyleSheet, Text, View } from "react-native";
import type { Profile, ProfilePhoto } from "@/lib/types";

interface SwipeCardProps {
  profile: Profile;
  photos: ProfilePhoto[];
}

export function SwipeCard({ profile, photos }: SwipeCardProps) {
  const humanPhoto = photos.find((photo) => photo.kind === "human");
  const petPhoto = photos.find((photo) => photo.kind === "pet");

  return (
    <View style={styles.card}>
      {humanPhoto ? (
        <Image source={{ uri: humanPhoto.url }} style={styles.mainPhoto} />
      ) : (
        <View style={[styles.mainPhoto, styles.placeholder]} />
      )}

      {petPhoto ? (
        <Image source={{ uri: petPhoto.url }} style={styles.petBadge} />
      ) : null}

      <View style={styles.info}>
        <Text style={styles.name}>{profile.name}</Text>
        {profile.pet_name || profile.pet_type ? (
          <Text style={styles.pet}>
            🐾 {profile.pet_name} {profile.pet_type ? `(${profile.pet_type})` : ""}
          </Text>
        ) : null}
        {profile.bio ? <Text style={styles.bio}>{profile.bio}</Text> : null}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderRadius: 16,
    overflow: "hidden",
    backgroundColor: "#fff",
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 12,
    elevation: 4,
  },
  mainPhoto: { width: "100%", aspectRatio: 3 / 4, backgroundColor: "#eee" },
  placeholder: { alignItems: "center", justifyContent: "center" },
  petBadge: {
    position: "absolute",
    top: 12,
    right: 12,
    width: 64,
    height: 64,
    borderRadius: 32,
    borderWidth: 2,
    borderColor: "#fff",
  },
  info: { padding: 16, gap: 4 },
  name: { fontSize: 22, fontWeight: "700" },
  pet: { fontSize: 15, color: "#555" },
  bio: { fontSize: 14, color: "#333", marginTop: 4 },
});
