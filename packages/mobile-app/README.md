# Mobile App Package

**Phase:** Phase 2
**Status:** Planned (Not Yet Implemented)
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

## Technology Stack (Proposed)

### Option 1: Swift/SwiftUI (Native)
- Best performance and iOS integration
- Direct Secure Enclave access
- Smaller app size
- Steeper learning curve

### Option 2: React Native
- Cross-platform potential (future Android)
- Faster development iteration
- Larger community
- Limited Secure Enclave access

**Decision:** TBD based on Phase 1 learnings

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

**Note:** Not yet implemented. This directory is a placeholder for Phase 2.

When development begins:
```bash
cd packages/mobile-app
npm install  # or pod install for native
# Follow iOS/React Native setup guides
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

*This package is currently in planning phase. Implementation begins after Phase 1 validation.*
