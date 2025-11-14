# Birthmark Phase 2 Plan - iOS App

**Version:** 1.0  
**Date:** November 2025  
**Phase:** Phase 2 (iOS Mobile Validation)  
**Timeline:** 3-4 months

---

## Purpose

Phase 2 develops an iOS camera application to validate the Birthmark Standard architecture on consumer mobile hardware. This phase proves that authentication works on consumer devices, measures mobile performance constraints, and validates user demand through closed beta testing.

**This is a proof-of-concept, not a production app.** The goal is to generate evidence for Phase 3 manufacturer partnerships.

---

## Strategic Approach

### What Phase 2 IS

- Technical validation that architecture works on iOS
- Performance benchmarking (battery, speed, reliability)
- User research with 50-100 photographers/photojournalists
- Evidence generation for manufacturer conversations

### What Phase 2 IS NOT

- App Store submission or public release
- Long-term product maintenance
- Consumer brand building
- Production-grade security implementation

### Why iOS Testing Matters

**Validates architecture is hardware-agnostic:**
- Same aggregation server handles both Raspberry Pi and iOS submissions
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
- Hash the JPEG/HEIC output from iOS camera
- Works on all iPhones (not just Pro models)
- Fast: <10ms hashing time
- Minimal battery impact

**Rationale:** RAW capture requires hardware access only manufacturers have. Phase 2 validates the concept; Phase 3 manufacturers provide proper sensor-level integration.

### Device Identity (iOS Equivalent of NUC Maps)

Since iOS doesn't expose camera sensor calibration data, we use device-specific fingerprinting:

```
device_fingerprint = SHA256(
    UIDevice.identifierForVendor +
    cryptographic_random_seed +
    "Birthmark-Standard-iOS-v1"
)
```

**Properties:**
- Unique per device installation
- Stored in Secure Enclave (tamper-resistant)
- Good enough for proof-of-concept
- Documents need for hardware integration in Phase 3

### Authentication Flow

```
1. User takes photo
   ↓
2. iOS captures processed image (JPEG/HEIC)
   ↓
3. Calculate SHA-256 hash (~10ms)
   ↓
4. Retrieve device fingerprint from Secure Enclave
   ↓
5. Select random key from assigned tables
   ↓
6. Encrypt device fingerprint with selected key
   ↓
7. Create authentication bundle
   ↓
8. Queue for upload to aggregation server
   ↓
9. Photo saves to Camera Roll
```

**Total overhead: <20ms (imperceptible to user)**

### Backend Integration

**Critical validation point:** Uses same aggregation server and smart contract from Phase 1 without modification.

**Data formats:**
- Raspberry Pi sends: `{raw_hash, encrypted_NUC_hash, table, key}`
- iPhone sends: `{processed_hash, encrypted_device_fingerprint, table, key}`
- Server processes both identically

This proves the architecture is hardware-agnostic.

---

## Development Timeline

### Month 1: Core Development

**Weeks 1-2: Environment Setup + Learning**
- Set up Xcode development environment
- Learn Swift/SwiftUI basics
- Build basic camera interface (no authentication)
- Validate camera capture works

**Weeks 3-4: Cryptographic Integration**
- Device fingerprint generation
- Secure Enclave key storage
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
- TestFlight setup
- Apple review (24-48 hours)
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

### Distribution: TestFlight Closed Beta

**What is TestFlight:**
- Apple's official beta distribution platform
- Included with $99/year Apple Developer account
- Up to 10,000 external testers (using 50-100)
- 90-day testing period per build
- Free for testers

**How it works:**
1. Upload build to App Store Connect
2. Apple reviews (24-48 hours)
3. Send invitation links to testers
4. Testers install via TestFlight app
5. Updates push automatically

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
- AVFoundation: Camera capture
- CryptoKit: SHA-256, AES-GCM, HKDF
- Security: Secure Enclave key storage
- Foundation: Networking (URLSession)
- SwiftUI: User interface

**Development:**
- Xcode (latest stable)
- Swift 5.9+
- iOS 16.0+ target

### Key Components

**1. Camera Manager**
- Capture photos using AVFoundation
- Hash image data (SHA-256)
- Trigger authentication pipeline

**2. Cryptographic Service**
- Generate/store device fingerprint
- Derive encryption keys from master keys
- Encrypt device fingerprint

**3. Network Manager**
- Submit bundles to aggregation server
- Queue failed uploads
- Background upload support

**4. Secure Storage**
- Store device fingerprint in Secure Enclave
- Store table assignments
- Retrieve credentials

### Provisioning Flow

**First Launch:**
1. Generate device fingerprint (cryptographic random)
2. Connect to Simulated Manufacturer Authority
3. SMA assigns 3 random tables (from 2,500 global pool)
4. SMA generates 3 master keys (256-bit each)
5. Store certificate + keys in Secure Enclave
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
- Background: iOS URLSession background tasks

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

**1. Working iOS Application**
- Functional camera app with authentication
- TestFlight distribution to beta testers
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
- "Photo Authentication on iOS: Feasibility Study"
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

### iOS-Specific Constraints

**Camera API Limitations:**
- No raw sensor data access (app-level)
- Hashing occurs post-ISP processing
- Device fingerprint is software-based
- Need manufacturer partnership for hardware integration

**Background Limitations:**
- iOS terminates background tasks aggressively
- Limited background networking time (~30 seconds)
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

**iOS API changes**
- Mitigation: Target stable iOS 16.0+
- Impact: Medium (can update quickly)

**Performance targets not met**
- Mitigation: Benchmark early (Week 3-4)
- Impact: Low (crypto is fast on modern iOS)

**Secure Enclave limitations**
- Mitigation: Research thoroughly Week 3
- Impact: Medium (fallback to Keychain)

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

**iOS learning curve**
- Mitigation: Extra time Month 1, contractor option
- Impact: Medium (can extend)

**TestFlight review delays**
- Mitigation: Submit early, buffer time
- Impact: Low (typically 24-48 hours)

**Late bugs**
- Mitigation: Progressive rollout, internal testing
- Impact: Medium (can push updates quickly)

---

## Post-Phase 2 Plan

### App Sunset Strategy

**Decision Point:** End of Month 4

**Option 1: Sunset After Data Collection**
- Close TestFlight access
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
- Complete iOS app source code
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
- iOS performance data
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

### Apple Developer Account
- **Cost:** $99/year
- **Required for:** TestFlight, code signing

### Infrastructure (No Change from Phase 1)
- **Aggregation server:** $50-100/month
- **Ethereum testnet:** Free (Sepolia/Goerli)
- **Domain:** $20/year (existing)

### Testing Devices
- **Development iPhone:** Existing device
- **Testing variety:** Testers' own devices

### Total Incremental Cost
- **Apple Developer:** $99
- **Server hosting (4 months):** $200-400
- **Total:** ~$300-500

**Note:** Primary investment is time (3-4 months), not money.

---

## Next Steps

### Immediate (This Week)
1. Purchase Apple Developer account
2. Install Xcode, set up environment
3. Create new iOS project
4. Build simple camera capture (no auth)

### Short Term (Weeks 1-4)
1. Learn Swift/iOS fundamentals
2. Device fingerprint + Secure Enclave
3. Integrate with SMA for provisioning
4. Internal testing

### Medium Term (Weeks 5-8)
1. Network integration with aggregation server
2. Queue management and offline support
3. TestFlight setup and Apple review
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
- [ ] Secure Enclave vs Keychain approach
- [ ] Table assignment protocol with SMA
- [ ] Authentication bundle format

### Week 5-6
- [ ] Queue management strategy
- [ ] Background upload timing
- [ ] Error handling approach

### Week 6-7
- [ ] TestFlight invitation method
- [ ] Tester communication plan
- [ ] Feedback collection approach

### Month 4
- [ ] Post-Phase 2 app strategy
- [ ] Open source timing and license
- [ ] Phase 3 package format

---

## Document Maintenance

**Version:** 1.0  
**Date:** November 2025  
**Author:** Samuel C. Ryan, Birthmark Standard Foundation  
**Status:** Planning Document

**Revision History:**
- v1.0 (Nov 2025): Initial Phase 2 iOS app plan
