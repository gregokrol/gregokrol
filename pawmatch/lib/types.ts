export type PhotoKind = "human" | "pet";

export interface ProfilePhoto {
  id: string;
  profile_id: string;
  url: string;
  storage_path: string | null;
  display_url?: string;
  kind: PhotoKind;
  position: number;
}

export interface PublicProfile {
  id: string;
  name: string;
  bio: string;
  pet_name: string;
  pet_type: string;
  is_complete: boolean;
  created_at: string;
}

export interface Profile extends PublicProfile {
  birthdate: string | null;
}

export type SwipeDirection = "like" | "pass";

export interface Swipe {
  id: string;
  swiper_id: string;
  swiped_id: string;
  direction: SwipeDirection;
  created_at: string;
}

export interface Match {
  id: string;
  user_a: string;
  user_b: string;
  created_at: string;
}

export interface Message {
  id: string;
  match_id: string;
  sender_id: string;
  content: string;
  created_at: string;
}
