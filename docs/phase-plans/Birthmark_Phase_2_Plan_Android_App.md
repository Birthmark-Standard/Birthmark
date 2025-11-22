# Birthmark Phase 2 Plan - Android App

**Version:** 2.0
**Date:** November 2025
**Phase:** Phase 2 (Android Mobile Validation)
**Timeline:** 3-4 months

---

## Purpose

Phase 2 develops an Android camera application to validate the Birthmark Standard architecture on consumer mobile hardware. This phase proves that authentication works on consumer devices, measures mobile performance constraints, and validates user demand through closed beta testing.

**This is a proof-of-concept, not a production app.** The goal is to generate evidence for Phase 3 manufacturer partnerships.

---

## Strategic Approach

### What Phase 2 IS

- Technical validation that architecture works on Android
- Performance benchmarking (battery, speed, reliability)
- User research with 50-100 photographers/photojournalists
- Evidence generation for manufacturer conversations

### What Phase 2 IS NOT

- Google Play Store public release
- Long-term product maintenance
- Consumer brand building
- Production-grade security implementation

### Why Android

**Aligns with Fairphone Partnership Strategy:**
- Primary manufacturer target (Fairphone) uses Android platform
- Android provides better hardware access for authentication prototypes
- Broader manufacturer ecosystem opportunities
- Android Camera2 API enables camera integration testing

**Platform Advantages:**
- Direct hardware access via Camera2 API
- More flexible app distribution (APK sideloading, Internal Testing)
- Better debugging and testing capabilities
- Kotlin is a modern, safe language for cryptographic operations

**Note:** iOS development remains possible in Phase 3 if manufacturer partners require it. The authentication architecture is platform-agnostic.

### Why Android Testing Matters

**Validates architecture is hardware-agnostic:**
- Same aggregation server handles both Raspberry Pi and Android submissions
- Proves backend infrastructure scales to mobile
- No changes needed to Phase 1 infrastructure

**Provides manufacturer conversation data:**
- "We have X photographers actively using authentication daily"
- "Mobile performance: <20ms overhead, <2% battery impact"
- "Users want camera-level integration (not just apps)"

**De-risks technical questions:**
- Can mobile handle cryptographic operations? (Yes)
- Will users tolerate workflow changes? (Data-driven answer)
- Does batching work with intermittent connectivity? (Validated)

---

## Technical Approach

### Simplified Architecture

**Processed Image Hash Only (Not RAW):**
- Hash the JPEG output from Android camera
- Works on all Android devices (not just flagship models)
- Fast: <10ms hashing time
- Minimal battery impact

**Rationale:** RAW capture requires hardware access only manufacturers have. Phase 2 validates the concept; Phase 3 manufacturers provide proper sensor-level integration.

### Device Identity (Android Equivalent of NUC Maps)

Since Android doesn't expose camera sensor calibration data, we use device-specific fingerprinting:

```kotlin
val deviceFingerprint = MessageDigest.getInstance("SHA-256").digest(
    (Settings.Secure.ANDROID_ID +
     cryptographicRandomSeed +
     "Birthmark-Standard-Android-v1").toByteArray()
).toHexString()
```

**Properties:**
- Unique per device installation
- Stored in Android Keystore (tamper-resistant)
- Good enough for proof-of-concept
- Documents need for hardware integration in Phase 3

### Authentication Flow

```
1. User takes photo
   |
2. Android captures processed image (JPEG)
   |
3. Calculate SHA-256 hash (~10ms)
   |
4. Retrieve device fingerprint from Android Keystore
   |
5. Select random key from assigned tables
   |
6. Encrypt device fingerprint with selected key
   |
7. Create authentication bundle
   |
8. Queue for upload to aggregation server
   |
9. Photo saves to device gallery
```

**Total overhead: <20ms (imperceptible to user)**

### Backend Integration

**Critical validation point:** Uses same aggregation server and blockchain from Phase 1 without modification.

**Data formats:**
- Raspberry Pi sends: `{raw_hash, encrypted_NUC_hash, table, key}`
- Android sends: `{processed_hash, encrypted_device_fingerprint, table, key}`
- Server processes both identically

This proves the architecture is hardware-agnostic.

---

## Development Timeline

### Month 1: Core Development

**Weeks 1-2: Environment Setup + Learning**
- Set up Android Studio development environment
- Learn Kotlin/Jetpack Compose basics
- Build basic camera interface (no authentication)
- Validate camera capture works

**Weeks 3-4: Cryptographic Integration**
- Device fingerprint generation
- Android Keystore key storage
- Key derivation (HKDF from master keys)
- Provisioning with Simulated Manufacturer Authority

**Milestone:** Internal testing validates each component works independently

### Month 2: Integration + Initial Beta

**Weeks 5-6: Authentication Pipeline**
- Integrate authentication into camera flow
- Hash captured images
- Create authentication bundles
- Local queue for offline operation

**Week 7: Network Integration**
- Submit to aggregation server
- Handle responses and errors
- Retry logic for failures
- Background upload support

**Week 8: First External Beta**
- Google Play Internal Testing setup
- Recruit Wave 1: Photography clubs (20-30 people)
- Collect initial feedback

**Milestone:** External testers can capture and authenticate photos

### Month 3: Refinement + Expansion

**Weeks 9-10: Polish**
- Address Wave 1 feedback
- Performance optimization
- Bug fixes
- Stability improvements

**Week 11: Expanded Testing**
- Wave 2: Photojournalists (20-30 people)
- Wave 3: Fact-checkers (10-20 people)
- Wave 4: Technical community (10-20 people)
- Monitor usage patterns

**Week 12: Data Collection**
- Performance benchmarks
- User satisfaction surveys
- Usage analytics
- Testimonial collection

**Milestone:** 60-100 active testers, statistically significant data

### Month 4: Documentation

**Weeks 13-14: Technical Documentation**
- Code documentation for open-source release
- Architecture docs for manufacturers
- Performance report with benchmarks
- Lessons learned

**Weeks 15-16: User Research Report**
- Analyze feedback and usage data
- Document workflows and pain points
- Compile testimonials
- Prepare Phase 3 evidence package

**Milestone:** Complete evidence package ready for manufacturer conversations

---

## Beta Testing Strategy

### Distribution: Google Play Internal Testing

**What is Google Play Internal Testing:**
- Google's official internal beta distribution platform
- Part of Google Play Console ($25 one-time fee)
- Up to 100 internal testers
- No review process required for internal testing
- Instant updates to testers

**How it works:**
1. Upload APK/AAB to Play Console
2. Add testers via email addresses
3. Testers accept invitation and install via Play Store
4. Updates push automatically

### Tester Recruitment

**Target: 60-100 active testers across 4 waves**

**Wave 1: Photography Clubs (20-30 people)**
- Local Portland-area clubs
- Enthusiast photographers
- Timeline: Month 2, Week 8

**Wave 2: Photojournalists (20-30 people)**
- Professional photographers via NPPA, CPJ
- Experiencing credibility crisis firsthand
- Timeline: Month 3, Week 11

**Wave 3: Fact-Checkers (10-20 people)**
- Verification professionals (First Draft, IFCN)
- Use case: verifying others' photos
- Timeline: Month 3, Week 11

**Wave 4: Technical Community (10-20 people)**
- Blockchain developers, security researchers
- Security-focused feedback
- Timeline: Month 3-4

### Setting Expectations

**Message to testers:**

"This is a technical pilot to validate photo authentication on mobile devices. This is a proof-of-concept, not a consumer product.

The app will be available for approximately 3-6 months while we collect data. If we successfully partner with camera manufacturers, authentication will move to hardware-level integration in future cameras.

By participating, you're helping prove demand for this technology.

We'll see device fingerprints and image hashes for authentication. We do not see your actual photos."

---

## Technical Implementation

### Core Technologies

**Frameworks:**
- CameraX: Camera capture (recommended over Camera2 for simplicity)
- java.security: SHA-256, AES-GCM
- Android Keystore: Secure key storage
- Retrofit/OkHttp: Networking
- Jetpack Compose: User interface

**Development:**
- Android Studio (latest stable)
- Kotlin 1.9+
- Android API 26+ target (Android 8.0+)
- Minimum SDK 26 (covers 95%+ of devices)

### Key Components

**1. Camera Manager**
- Capture photos using CameraX
- Hash image data (SHA-256)
- Trigger authentication pipeline

**2. Cryptographic Service**
- Generate/store device fingerprint
- Derive encryption keys from master keys
- Encrypt device fingerprint

**3. Network Manager**
- Submit bundles to aggregation server
- Queue failed uploads
- WorkManager for background uploads

**4. Secure Storage**
- Store device fingerprint in Android Keystore
- Store table assignments
- Retrieve credentials

### Provisioning Flow

**First Launch:**
1. Generate device fingerprint (cryptographic random)
2. Connect to Simulated Manufacturer Authority
3. SMA assigns 3 random tables (from 2,500 global pool)
4. SMA generates 3 master keys (256-bit each)
5. Store certificate + keys in Android Keystore
6. Ready to authenticate

**Subsequent Launches:**
- Retrieve stored credentials
- No re-provisioning needed
- Keys derived on-demand

---

## Performance Targets

### Capture Pipeline

**Latency:**
- Image capture: ~100ms (system speed)
- SHA-256 hash: <10ms
- Encryption: <1ms
- Bundle creation: <1ms
- **Total overhead: <20ms**

**Battery:**
- <2% additional consumption
- Typical usage: 100-200 photos/day
- Cryptographic operations highly efficient

**Storage:**
- Authentication bundle: ~200 bytes/photo
- Queue capacity: 10MB (~50,000 bundles)
- Negligible vs photo storage (2-5MB each)

### Network Performance

**Upload:**
- Batch size: 10-50 bundles
- Frequency: Every 5 minutes when online
- Retry: Exponential backoff (1s, 2s, 4s, 8s, max 60s)
- Background: WorkManager for reliable background uploads

**Failure Handling:**
- Queue persists across launches
- Manual sync option
- Status display in settings
- Alert if queue exceeds threshold

---

## Success Metrics

### Technical Metrics

**Performance:**
- [ ] Authentication overhead <20ms (95th percentile)
- [ ] Battery impact <2% for 100 photos/day
- [ ] Upload success rate >98%
- [ ] Crash rate <1%

**Reliability:**
- [ ] Queue handles 1,000+ pending bundles
- [ ] Background uploads work consistently
- [ ] Offline mode degrades gracefully
- [ ] Automatic failure recovery

### Usage Metrics

**Adoption:**
- [ ] 50+ weekly active users
- [ ] 500+ total photos authenticated
- [ ] Average 10+ photos per user per week
- [ ] 60%+ week-over-week retention

**Engagement:**
- [ ] Use continues beyond week 2
- [ ] Meaningful volume (not just testing)
- [ ] Active issue reporting and feedback

### User Research Metrics

**Satisfaction:**
- [ ] 80%+ find authentication valuable
- [ ] 70%+ would use production version
- [ ] 60%+ perceive minimal workflow disruption

**Feedback Quality:**
- [ ] 5+ detailed testimonials from professionals
- [ ] Specific pain points identified
- [ ] Feature requests collected
- [ ] Use cases validated

---

## Deliverables

### Technical Outputs

**1. Working Android Application**
- Functional camera app with authentication
- Google Play Internal Testing distribution to beta testers
- Integration with Phase 1 infrastructure
- Open-source code repository (MIT/Apache 2.0)

**2. Performance Report**
- Authentication latency benchmarks
- Battery consumption analysis
- Network reliability metrics
- Device compatibility results

**3. Technical Documentation**
- Architecture docs for manufacturers
- API integration guide
- Open-source code documentation
- Security analysis and threat model

### User Research Outputs

**1. Usage Data Analysis**
- Active user counts and retention
- Photos per user per week
- Feature usage patterns
- Technical issues encountered

**2. User Feedback Report**
- Satisfaction survey results
- Workflow observations
- Value perception analysis
- Pain points and requests

**3. Testimonial Collection**
- Professional photographer quotes
- Use case validation stories
- Credibility crisis examples
- Authentication value statements

### Phase 3 Evidence Package

**1. Executive Summary**
- "Photo Authentication on Android: Feasibility Study"
- Key findings: performance, demand, validation
- Recommendations for manufacturer integration

**2. Technical Specifications**
- Reference implementation
- Mobile-specific constraints
- Hardware integration requirements

**3. Market Validation**
- User demand quantification
- Professional testimonials
- Target market validation
- Value proposition confirmation

---

## Technical Considerations

### Android-Specific Constraints

**Camera API Limitations:**
- No raw sensor data access (app-level, without Camera2 RAW support)
- Hashing occurs post-ISP processing
- Device fingerprint is software-based
- Need manufacturer partnership for hardware integration

**Background Limitations:**
- Android may kill background processes
- WorkManager provides reliable background execution
- Must queue reliably and retry on next launch

**Battery Optimization:**
- Minimize continuous connections
- Batch uploads when possible
- Defer non-critical operations

**Storage Management:**
- Queue size limits
- Purge old failed uploads
- Alert if queue grows excessively

### Security Model

**App-Level Limitations:**
- Users could manipulate before hashing (modified app)
- Device fingerprint less secure than hardware NUC
- Software-based, not hardware root of trust

**Mitigation:**
- Document limitations clearly
- Position as proof-of-concept
- Show what hardware integration solves

**For Phase 3 Manufacturers:**
- "Here's what app-level can do"
- "Here's why hardware is necessary"
- "Here's the baseline performance you need to meet"

---

## Risk Management

### Technical Risks

**Android fragmentation**
- Mitigation: Target API 26+ (95% coverage), test on multiple devices
- Impact: Medium (wide device support needed)

**Performance targets not met**
- Mitigation: Benchmark early (Week 3-4)
- Impact: Low (crypto is fast on modern Android)

**Android Keystore limitations**
- Mitigation: Research thoroughly Week 3
- Impact: Medium (fallback to encrypted SharedPreferences)

**Network reliability**
- Mitigation: Robust queue, offline testing
- Impact: Medium (critical for UX)

### User Adoption Risks

**Insufficient recruitment**
- Mitigation: Start outreach early (Week 6)
- Impact: High (need 50+ users)

**Testers don't continue using**
- Mitigation: Clear value prop, engagement
- Impact: High (need usage data)

**Confusion about temporary nature**
- Mitigation: Clear upfront communication
- Impact: Low (manageable)

### Timeline Risks

**Kotlin learning curve**
- Mitigation: Extra time Month 1, contractor option
- Impact: Medium (can extend)

**Play Console setup delays**
- Mitigation: Set up account early
- Impact: Low (typically quick)

**Late bugs**
- Mitigation: Progressive rollout, internal testing
- Impact: Medium (can push updates quickly)

---

## Post-Phase 2 Plan

### App Sunset Strategy

**Decision Point:** End of Month 4

**Option 1: Sunset After Data Collection**
- Close Internal Testing access
- Thank testers, explain transition
- Archive code and documentation
- Focus on Phase 3

**Option 2: Maintain Through Phase 3**
- Keep running during manufacturer negotiations
- Use continued usage as demand evidence
- Sunset when first manufacturer ships

**Option 3: Open Source for Community**
- Release code publicly
- Foundation supports standard, not app
- Community can continue development

**Decision factors:**
- Phase 3 partnership status
- Tester engagement level
- Resource availability
- Strategic value

### Open Source Release

**What to Release:**
- Complete Android app source code
- Integration examples
- Developer documentation
- Reference implementation

**License:**
- MIT or Apache 2.0 (permissive)
- Manufacturer-friendly
- No copyleft restrictions

**Purpose:**
- Good faith to manufacturers
- Enable academic review
- Show implementation approach
- Build trust in openness

### Manufacturer Conversations

**Evidence Package:**
- Android performance data
- User demand validation
- Professional testimonials
- Open-source reference code
- Hardware integration requirements

**Key Messages:**
- "Mobile validation: <20ms overhead confirmed"
- "X photographers using daily authentication"
- "App-level has security limits only hardware solves"
- "Open-source reference implementation available"
- "Need hardware integration for production"

---

## Budget

### Google Play Console
- **Cost:** $25 one-time registration fee
- **Required for:** Internal Testing, app signing

### Infrastructure (No Change from Phase 1)
- **Aggregation server:** $50-100/month
- **Blockchain testnet:** Free
- **Domain:** $20/year (existing)

### Testing Devices
- **Development device:** Existing Android phone or emulator
- **Testing variety:** Testers' own devices

### Total Incremental Cost
- **Google Play Console:** $25
- **Server hosting (4 months):** $200-400
- **Total:** ~$225-425

**Note:** Primary investment is time (3-4 months), not money.

---

## Next Steps

### Immediate (This Week)
1. Register Google Play Console account
2. Install Android Studio, set up environment
3. Create new Android project
4. Build simple camera capture (no auth)

### Short Term (Weeks 1-4)
1. Learn Kotlin/Android fundamentals
2. Device fingerprint + Android Keystore
3. Integrate with SMA for provisioning
4. Internal testing

### Medium Term (Weeks 5-8)
1. Network integration with aggregation server
2. Queue management and offline support
3. Google Play Internal Testing setup
4. Wave 1 tester recruitment

### Long Term (Weeks 9-16)
1. Expand testing to additional waves
2. Performance benchmarking
3. Feedback collection and analysis
4. Phase 3 evidence package
5. Begin manufacturer outreach

---

## Key Decisions Needed

### Week 2-3
- [ ] Android Keystore vs encrypted SharedPreferences approach
- [ ] Table assignment protocol with SMA
- [ ] Authentication bundle format

### Week 5-6
- [ ] Queue management strategy
- [ ] Background upload timing
- [ ] Error handling approach

### Week 6-7
- [ ] Internal Testing invitation method
- [ ] Tester communication plan
- [ ] Feedback collection approach

### Month 4
- [ ] Post-Phase 2 app strategy
- [ ] Open source timing and license
- [ ] Phase 3 package format

---

## Document Maintenance

**Version:** 2.0
**Date:** November 2025
**Author:** Samuel C. Ryan, Birthmark Standard Foundation
**Status:** Planning Document

**Revision History:**
- v2.0 (Nov 2025): Updated to Android platform (from iOS)
  - Changed platform from iOS to Android
  - Updated TestFlight to Google Play Internal Testing
  - Updated Swift/SwiftUI to Kotlin/Jetpack Compose
  - Added Fairphone partnership strategy context
  - Maintained core architecture (platform-agnostic)
- v1.0 (Nov 2025): Initial Phase 2 iOS app plan
