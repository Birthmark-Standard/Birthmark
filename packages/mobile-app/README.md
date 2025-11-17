# Mobile App Package

**Phase:** Phase 2
**Status:** ✅ Implemented (Ready for Testing)
**Platform:** iOS (TestFlight Beta)

## Overview

The mobile-app package will implement an iOS application for the Birthmark Standard. This app will validate the system architecture on consumer mobile devices before engaging camera manufacturers for Phase 3.

## Key Differences from Phase 1

### Hardware Fingerprinting vs. NUC Maps

**Phase 1 (Raspberry Pi):**
- Uses raw Bayer sensor data
- Extracts NUC (Non-Uniformity Correction) maps
- Direct hardware sensor access

**Phase 2 (iOS):**
- Uses processed camera output (JPEG/HEIF)
- Device fingerprint instead of sensor NUC
- Works within iOS camera framework constraints

### Architecture Validation

The iOS app validates that:
- Aggregation server scales to consumer devices
- Authentication flow works on mobile networks
- User experience is acceptable for general public
- Costs remain under target (<$0.00003/image)

## Planned Features

### Camera Integration
- Native iOS camera capture
- Background image hashing
- Zero user-perceivable latency
- Batch submission on WiFi

### Device Authentication
- iOS Secure Enclave for key storage
- Device fingerprint generation
- Certificate-based device identity
- Encrypted authentication bundles

### User Interface
- Minimal UI (camera app + verification badge)
- Photo library integration
- Verification status indicators
- Settings for aggregator selection

## Technology Stack

**Decision: Swift/SwiftUI (Native)**

Implemented with:
- Swift 5.9+ with SwiftUI
- AVFoundation for camera capture
- CryptoKit for SHA-256, HKDF, AES-GCM
- iOS Keychain for secure storage
- Photos framework for library integration
- Minimum iOS 16.0 target

## Testing Plan

### TestFlight Beta
- 60-100 volunteer testers
- Photography enthusiasts and journalists
- 2-3 month beta period
- Feedback collection via TestFlight

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
- TestFlight deployment
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

- Android version
- Federated aggregator selection
- Local verification cache
- Photo gallery verification viewer
- Social media integration warnings

## Development Setup

The iOS app is implemented and ready for Xcode integration.

### Quick Start

1. Open Xcode 15+
2. Create new iOS App project
3. Copy files from `BirthmarkCamera/` directory
4. Update aggregator URL in `NetworkService.swift`
5. Build and run on device or simulator

See `BirthmarkCamera/README.md` for detailed setup instructions.

```bash
cd packages/mobile-app/BirthmarkCamera
open README.md  # Full documentation
```

## Related Documentation

- iOS app plan: `docs/phase-plans/Birthmark_Phase_2_Plan_iOS_App.md`
- Architecture comparison: `docs/specs/Birthmark_Camera_Security_Architecture.md`

## Notes for Future Developers

1. **Secure Enclave Integration:** Critical for device authentication
2. **Background Processing:** iOS background task limitations
3. **Network Efficiency:** Batch submissions to conserve data/battery
4. **User Education:** Clear messaging about what Birthmark does/doesn't guarantee
5. **App Store Guidelines:** Compliance with privacy and camera usage policies

---

## Implementation Status

✅ **Complete iOS Implementation:**
- Camera capture with AVFoundation
- SHA-256 image hashing (<10ms)
- Device fingerprint generation
- HKDF key derivation + AES-GCM encryption
- Network submission with offline queue
- Photo Library integration
- Provisioning flow
- Settings and device management

📋 **Remaining Work:**
- Real SMA provisioning integration (currently uses mock data)
- TestFlight deployment and beta testing
- Performance benchmarking on real devices
- User feedback collection

*This iOS app is ready for Xcode project creation and TestFlight distribution.*
