# PawMatch – free iPhone demo with Expo Go

This project targets Expo SDK 54 specifically so it can run in the current Expo Go app from Apple's App Store on a physical iPhone without an Apple Developer membership.

## One-time setup on the computer

1. Install Node.js 20.19+ or Node.js 22 LTS.
2. Extract this project.
3. In the project folder run:

```bash
npm install
npx expo install --check
npx expo-doctor@latest
```

4. Copy `.env.example` to `.env` and fill in the Supabase URL and anon key.

## Run on iPhone for free

1. Install **Expo Go** from the Apple App Store.
2. Make sure the iPhone and computer are on the same Wi-Fi network.
3. In the project folder run:

```bash
npx expo start --go
```

4. Scan the QR code with the iPhone camera or Expo Go.

If the local network blocks LAN connections, try:

```bash
npx expo start --go --tunnel
```

No Apple Developer subscription is required for this Expo Go demo route.

## Important limitation

Expo Go is suitable for demo/testing. A standalone IPA, TestFlight distribution, or App Store release still requires Apple signing / Apple Developer membership.
