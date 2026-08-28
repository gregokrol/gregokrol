import { supabase } from "./supabase";
import type { ProfilePhoto } from "./types";

const SIGNED_URL_TTL_SECONDS = 60 * 60;
const PUBLIC_PATH_MARKER = "/storage/v1/object/public/profile-photos/";

/** Best-effort compatibility for rows created before storage_path was added. */
export function getStoragePath(photo: Pick<ProfilePhoto, "storage_path" | "url">): string | null {
  if (photo.storage_path) return photo.storage_path;

  const markerIndex = photo.url.indexOf(PUBLIC_PATH_MARKER);
  if (markerIndex >= 0) {
    try {
      return decodeURIComponent(photo.url.slice(markerIndex + PUBLIC_PATH_MARKER.length));
    } catch {
      return null;
    }
  }

  return null;
}

/**
 * Profile photos live in a private bucket. Resolve short-lived URLs only when the
 * authenticated client needs to display them.
 */
export async function withSignedPhotoUrls(photos: ProfilePhoto[]): Promise<ProfilePhoto[]> {
  return Promise.all(
    photos.map(async (photo) => {
      const path = getStoragePath(photo);
      if (!path) return photo;

      const { data, error } = await supabase.storage
        .from("profile-photos")
        .createSignedUrl(path, SIGNED_URL_TTL_SECONDS);

      if (error || !data?.signedUrl) return photo;
      return { ...photo, display_url: data.signedUrl };
    })
  );
}
