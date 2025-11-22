# Mobile App Package

**Phase:** Phase 2
**Status:** 🔄 Transitioning to Android
**Platform:** Android (Google Play Internal Testing)

## Overview

The mobile-app package implements an Android application for the Birthmark Standard. This app validates the system architecture on consumer mobile devices before engaging camera manufacturers for Phase 3.

**Note:** This package is transitioning from iOS to Android development. The existing Swift/iOS code is being replaced with Kotlin/Android implementation.

## Why Android?

- **Fairphone Partnership:** Primary manufacturer target uses Android platform
- **Hardware Access:** Better access for authentication prototypes via Camera2 API
- **Developer Experience:** More Android development expertise available
- **Manufacturer Ecosystem:** Broader opportunities with Android OEMs

## Key Differences from Phase 1

### Hardware Fingerprinting vs. NUC Maps

**Phase 1 (Raspberry Pi):**
- Uses raw Bayer sensor data
- Extracts NUC (Non-Uniformity Correction) maps
- Direct hardware sensor access

**Phase 2 (Android):**
- Uses processed camera output (JPEG)
- Device fingerprint instead of sensor NUC
- Works within Android camera framework constraints

### Architecture Validation

The Android app validates that:
- Aggregation server scales to consumer devices
- Authentication flow works on mobile networks
- User experience is acceptable for general public
- Costs remain under target (<$0.00003/image)

## Planned Features

### Camera Integration
- Native Android camera capture via CameraX
- Background image hashing
- Zero user-perceivable latency
- Batch submission on WiFi

### Device Authentication
- Android Keystore for secure key storage
- Device fingerprint generation
- Certificate-based device identity
- Encrypted authentication bundles

### User Interface
- Minimal UI (camera app + verification badge)
- Photo gallery integration
- Verification status indicators
- Settings for aggregator selection

## Technology Stack

**Decision: Kotlin/Jetpack Compose (Native)**

To be implemented with:
- Kotlin 1.9+ with Jetpack Compose
- CameraX for camera capture
- java.security for SHA-256, AES-GCM
- Android Keystore for secure storage
- MediaStore for gallery integration
- Minimum Android API 26 (Android 8.0+)

## Testing Plan

### Google Play Internal Testing
- 60-100 volunteer testers
- Photography enthusiasts and journalists
- 2-3 month beta period
- Feedback collection via Play Console

### Success Metrics
- <10 second background processing
- >95% successful submissions
- <5% battery impact per day (heavy usage)
- >80% user satisfaction

## Phase 2 Timeline

**Month 1-2:** Core Development
- Camera capture and hashing
- Device fingerprinting
- Aggregator communication

**Month 3:** Beta Testing
- Google Play Internal Testing deployment
- User feedback collection
- Bug fixes and optimization

**Month 4:** Analysis
- Review cost metrics
- Assess scalability
- Prepare Phase 3 proposal

## Privacy Considerations

- No photos stored by app (only hashes computed)
- Device fingerprint rotation
- Optional GPS hashing
- User consent for all data submission

## Future Enhancements (Post-Phase 2)

- iOS version (if manufacturer partners require)
- Federated aggregator selection
- Local verification cache
- Photo gallery verification viewer
- Social media integration warnings

## Development Setup

The Android app is being developed using Android Studio.

### Quick Start

1. Open Android Studio (latest stable)
2. Create new Android project with Kotlin/Jetpack Compose
3. Set minimum SDK to API 26 (Android 8.0)
4. Implement camera capture, hashing, and network services
5. Update aggregator URL in configuration
6. Build and run on device or emulator

### Legacy iOS Code

The `BirthmarkCamera/` directory contains the previous iOS implementation in Swift.
This code serves as a reference for the Android implementation but is no longer
the primary development target.

```bash
cd packages/mobile-app
# Android implementation in progress
```

## Related Documentation

- Android app plan: `docs/phase-plans/Birthmark_Phase_2_Plan_Android_App.md`
- Architecture comparison: `docs/specs/Birthmark_Camera_Security_Architecture.md`

## Notes for Future Developers

1. **Android Keystore Integration:** Critical for device authentication
2. **Background Processing:** Use WorkManager for reliable background uploads
3. **Network Efficiency:** Batch submissions to conserve data/battery
4. **User Education:** Clear messaging about what Birthmark does/doesn't guarantee
5. **Play Store Guidelines:** Compliance with privacy and camera usage policies

---

## Implementation Status

🔄 **Transitioning to Android:**
- Legacy iOS implementation available in `BirthmarkCamera/` for reference
- Android implementation in progress

📋 **Android Development Roadmap:**
- Camera capture with CameraX
- SHA-256 image hashing
- Device fingerprint generation with Android Keystore
- AES-GCM encryption for camera tokens
- Network submission with WorkManager for offline queue
- MediaStore integration for gallery
- Provisioning flow with SMA
- Settings and device management

📋 **Remaining Work:**
- Complete Android app implementation
- Real SMA provisioning integration
- Google Play Internal Testing deployment
- Performance benchmarking on real devices
- User feedback collection

*Android development is the primary focus for Phase 2.*
