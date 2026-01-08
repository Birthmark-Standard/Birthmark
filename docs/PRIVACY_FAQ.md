# Birthmark Standard Privacy FAQ

**Last Updated:** January 8, 2026

This document addresses common privacy questions about the Birthmark Standard's design and explains how the system protects photographer privacy while enabling public verification.

---

## Table of Contents

1. [Core Privacy Principles](#core-privacy-principles)
2. [What Information is Collected?](#what-information-is-collected)
3. [Who Can See What?](#who-can-see-what)
4. [Tracking and Surveillance](#tracking-and-surveillance)
5. [Location and Timestamp Privacy](#location-and-timestamp-privacy)
6. [Conflict Zone Photography](#conflict-zone-photography)
7. [Technical Implementation](#technical-implementation)
8. [Network Privacy](#network-privacy)

---

## Core Privacy Principles

### Does Birthmark track photographers?

**No.** The system is designed to prove image authenticity without identifying or tracking individual photographers.

**How this works:**
- No user accounts or registration required
- Camera selection from rotating key tables prevents individual device tracking
- No personal information is ever collected or stored
- Submission servers never see image content
- Blockchain stores only irreversible hashes

### What is the privacy design philosophy?

**Privacy-by-architecture, not policy.**

Every component is designed to see only the minimum information necessary for its function:
- **Cameras** see: Images (obviously, they capture them)
- **Manufacturers** see: That a validation request occurred (no context about what, where, when, or why)
- **Submission servers** see: Image hashes only (not images)
- **Blockchain** sees: Hashes only (irreversible, reveal nothing about content)
- **Verifiers** see: Authentication status for images they already have

---

## What Information is Collected?

### What data does the camera send?

When authenticating an image, the camera sends:

1. **Image hash** (SHA-256) - Cryptographic fingerprint of the image
2. **Encrypted device fingerprint** - NUC hash encrypted with rotating keys
3. **Manufacturer certificate** - Proves camera authenticity without revealing serial number

**Not sent:**
- ❌ The actual image
- ❌ Camera serial number
- ❌ Photographer identity
- ❌ Precise capture timestamp (only server processing time is recorded)
- ❌ Location data (unless in metadata, which is separately hashed)

### What is stored on the blockchain?

The blockchain stores:
- **Image hash** (SHA-256, 32 bytes) - Irreversible cryptographic fingerprint
- **Modification level** - Whether image is raw, validated, or modified
- **Authority ID** - Which manufacturer validated the camera
- **Server processing timestamp** - When the submission server processed it (not when photo was taken)

**The blockchain never stores:**
- ❌ Image content
- ❌ Image metadata
- ❌ Photographer identity
- ❌ Camera serial number
- ❌ Location information
- ❌ Precise capture time

---

## Who Can See What?

### What does the camera manufacturer see?

**What they see:**
- "A validation request occurred for a camera from one of my key tables"

**What they DON'T see:**
- ❌ Which specific camera (table shared by thousands of devices)
- ❌ Image hash or content
- ❌ Location where photo was taken
- ❌ Precise timestamp
- ❌ Photographer timezone
- ❌ What the photo is of

**Can they track usage patterns?**

No. The manufacturer only knows "some camera from table 847 authenticated something" but has zero context. They cannot correlate:
- Individual cameras
- Specific photographers
- Geographic locations
- Temporal patterns by photographer
- Photo content or subject matter

### What does the submission server see?

**What they see:**
- Image hashes (SHA-256)
- Manufacturer validation result (PASS/FAIL)
- Key table reference (shared by thousands of cameras)

**What they DON'T see:**
- ❌ Image content
- ❌ Which specific camera
- ❌ Photographer identity
- ❌ Location data

**Important:** Even verifiers only send hashes to submission servers, never images.

### What is publicly visible on the blockchain?

**Public information:**
- Image hash (SHA-256)
- Manufacturer that validated the camera
- Server processing timestamp
- Modification level (raw/validated/modified)

**Not public:**
- ❌ Image content
- ❌ Image metadata
- ❌ Photographer identity
- ❌ Camera serial number
- ❌ Capture location
- ❌ Actual capture time

### Can someone see all photos I've authenticated?

**No.** Even if you authenticate 1,000 photos:
- Each uses a different key table selection (3 random tables per camera)
- No user account links your submissions
- No camera serial number is revealed
- Blockchain cannot distinguish your photos from thousands of other photographers using cameras from the same manufacturer

---

## Tracking and Surveillance

### Can my camera be tracked?

**No.** The privacy architecture prevents camera tracking through several mechanisms:

1. **Key Table Anonymity**
   - Each camera is assigned 3 random key tables from 2,500 total
   - Each table is shared by thousands of devices
   - Camera randomly selects which of its 3 tables to use per authentication
   - Manufacturer sees table ID, not camera serial number

2. **No Serial Number Transmission**
   - Camera serial number never leaves the device
   - Only encrypted device fingerprint is transmitted
   - Encryption uses rotating keys only manufacturer can decrypt

3. **Table Anonymity Set**
   - Thousands of cameras share each table
   - Knowing "table 847 was used" doesn't identify the specific camera
   - No way to build per-camera usage profiles

### Can someone build a database of my authenticated images?

**Only if they already have your images.**

The blockchain stores hashes, not images. To know if a hash belongs to you:
1. They must already possess the image file
2. Hash it locally
3. Query the blockchain

If someone doesn't have your image, they cannot:
- Discover what you photographed
- Find images you authenticated
- Link multiple authentications to you
- Track your photography activity

### Can authorities retroactively identify when/where a photo was taken?

**No, unless you publish the image with identifying metadata.**

**Scenario:** You photograph a protest, authenticate it, and later publish it.

**What blockchain reveals:** "This hash was authenticated by [manufacturer] on [server processing date]"

**What blockchain does NOT reveal:**
- Actual capture time (only server processing time, which can be delayed)
- Capture location (location metadata is hashed, not stored)
- Photographer identity
- Camera serial number

**Important:** If the published image contains EXIF location data, that's visible in the image file itself, not the blockchain. Birthmark hashes location metadata to prove it hasn't been tampered with, but doesn't reveal it.

---

## Location and Timestamp Privacy

### Does Birthmark reveal where photos were taken?

**No.** Location data is handled via **metadata hashing**, not storage.

**How it works:**
1. If image has EXIF location data (GPS coordinates)
2. Camera hashes that location data
3. Hash is included in authentication bundle
4. Blockchain stores the hash, not the coordinates

**Result:**
- If you publish image with GPS coordinates, Birthmark proves those coordinates haven't been tampered with
- If you strip GPS data before publishing, there's nothing to reveal
- Blockchain never reveals location - it only verifies integrity of location metadata if present

### What about timestamps?

**Blockchain timestamp is server processing time, not capture time.**

**Privacy protection:**
- You can delay submission after capture (hours, days, weeks)
- Timestamp on blockchain reflects when server received it, not when you took the photo
- Actual capture timestamp (from camera EXIF) is hashed, not stored
- If you publish image with EXIF timestamp, Birthmark proves it's authentic but doesn't create it

**Example:**
- You take photo at 3:00 PM
- Authenticate it at 11:00 PM
- Blockchain shows 11:00 PM (server processing time)
- Your actual 3:00 PM capture time is private unless you publish EXIF data

---

## Conflict Zone Photography

### Is Birthmark safe for journalists in dangerous situations?

**Yes, with proper operational security.**

**Built-in protections:**
- No photographer identification
- No location tracking
- Delayed submission supported (authenticate later when safe)
- Works offline (authentication when connected)
- No accounts or login required

**Best practices for high-risk environments:**
1. **Delay authentication:** Capture photos, authenticate after leaving danger zone
2. **Strip metadata:** Remove EXIF location/timestamp before publication if needed
3. **Use VPN:** Obscure submission source (see Network Privacy section)
4. **Batch submissions:** Mix protest photos with unrelated images
5. **Time obfuscation:** Submit hours or days after capture

**What adversaries can learn:** Only that "some camera authenticated some image on [date]" - no connection to you, your location, or specific events.

### Can retroactive identification occur?

**No, unless you publish identifying information.**

**Scenario:** You photograph a sensitive event, authenticate it securely, then someone publishes the image months later.

**What can be determined:**
- Image was authenticated by a legitimate camera from [manufacturer]
- Server processing happened on [date]

**What CANNOT be determined:**
- Who took the photo
- Where it was taken
- When it was actually captured (vs. when submitted for authentication)
- What camera took it (table anonymity)

**Critical:** The published image itself may contain identifying information (EXIF metadata, visual content). Birthmark doesn't add identifying information - it only proves the image came from a real camera.

---

## Technical Implementation

### How does metadata hashing work?

**Metadata is hashed, not stored.**

When an image contains metadata (EXIF):
1. Camera extracts metadata (timestamp, GPS, camera settings)
2. Computes SHA-256 hash of metadata
3. Includes metadata hash in authentication bundle
4. Blockchain stores the hash

**Result:**
- Metadata content is never stored or transmitted
- If you publish image with metadata, hash proves it hasn't been tampered with
- If you strip metadata before publication, there's nothing to reveal
- Hashing is irreversible - cannot recover metadata from hash

### Why not use zero-knowledge proofs?

**Computational infeasibility on mobile devices.**

Zero-knowledge proofs (ZKPs) would allow proving "I have an authenticated image" without revealing which image. However:

**Technical limitations:**
- ZK proof generation takes minutes on high-performance hardware
- Mobile camera taking 10 photos/minute would need 30+ minutes of continuous computation
- Battery drain would be unacceptable
- Creates massive backlog of un-authenticated images

**Practical limitations:**
- No clear use case: Authentication verification requires having the specific image
- Human verifiers need to see the image to assess it
- Adding computational complexity without privacy benefit

**Conclusion:** Hash-based privacy is sufficient and practical for this use case.

### Can hashes be reversed to recover images?

**No. Cryptographic hash functions are one-way.**

SHA-256 properties:
- **Irreversible:** Cannot reconstruct image from hash
- **Deterministic:** Same image always produces same hash
- **Collision-resistant:** Virtually impossible for two different images to produce same hash

**What this means:**
- Blockchain sees hash, has zero information about image content
- Only someone with the actual image can verify authentication
- No way to "browse" authenticated images - must have image first

---

## Network Privacy

### Does Birthmark support VPN/Tor?

**VPN support is prioritized in the roadmap.**

Current status:
- Standard internet connection for submissions
- Future versions will prioritize existing VPN connections
- Tor support under consideration for high-risk users

**Best practice now:** Use your own VPN if privacy is a concern.

### Can my ISP see what I'm authenticating?

**ISP sees encrypted network traffic to submission server.**

What ISP sees:
- Connection to submission server IP address
- Encrypted data transmission (HTTPS)
- Cannot see image content or hashes

What ISP cannot see:
- Image content
- Image hashes
- Authentication results
- Purpose of connection

**For additional privacy:** Use VPN to hide submission server connections from ISP.

### Are submissions anonymous?

**Pseudonymous, not anonymous.**

Submission server sees:
- Source IP address (standard internet protocol)
- Image hashes being authenticated

Submission server does NOT see:
- Your identity (no accounts)
- Images themselves
- Your other submissions (no linking mechanism)

**For IP anonymity:** Use VPN or wait for Tor support.

---

## Summary

### Key Privacy Properties

✅ **No photographer tracking** - Table anonymity prevents camera identification
✅ **No location storage** - GPS coordinates are hashed, not stored
✅ **No capture time storage** - Only server processing time recorded
✅ **No image content exposure** - Only hashes transmitted and stored
✅ **No identity requirement** - No accounts, registration, or login
✅ **Metadata integrity** - Proves metadata authentic without revealing it
✅ **Reversible hashing** - Hashes cannot be reversed to recover data

### Privacy Tradeoffs

The Birthmark Standard prioritizes:
- **Verification capability** over **complete anonymity**
- **Practical usability** over **theoretical maximum privacy**
- **Transparency** over **obscurity**

If you publish an authenticated image with identifying metadata (EXIF location, visible landmarks, etc.), that information becomes public via the image itself, not via Birthmark.

Birthmark's role is to prove the image came from a real camera and the metadata hasn't been tampered with - it doesn't hide information you choose to publish.

---

## Questions?

For additional privacy questions:
- **Technical details:** See [CLAUDE.md](../CLAUDE.md) Privacy Architecture section
- **Security concerns:** Email [contact@birthmarkstandard.org](mailto:contact@birthmarkstandard.org)
- **Community discussion:** [Discord community](https://discord.gg/9Ts7dM9pb5)

---

**The Birthmark Standard Foundation**
*Building public good infrastructure for trust in digital media.*
