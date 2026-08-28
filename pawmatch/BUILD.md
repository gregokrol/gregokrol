# PawMatch build and demo options

## Free iPhone demo — recommended now

PawMatch targets Expo SDK 54 so it can run in the App Store version of Expo Go on a physical iPhone.

```bash
npm install
npx expo install --check
npx expo-doctor@latest
npx expo start --go
```

Then scan the QR code using Expo Go on the iPhone.

No Apple Developer subscription is required for this demo route.

## Android APK (direct install)

```bash
eas build --platform android --profile android-apk
```

## Android AAB (Google Play)

```bash
eas build --platform android --profile production
```

## iPhone / iPad internal standalone build

Requires Apple Developer credentials and device provisioning:

```bash
eas build --platform ios --profile ios-device
```

## iOS Simulator

Does not install on a physical iPhone:

```bash
eas build --platform ios --profile ios-simulator
```

## App Store / TestFlight

Requires Apple Developer credentials:

```bash
eas build --platform ios --profile production
```
