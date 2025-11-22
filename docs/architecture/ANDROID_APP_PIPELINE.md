# Android App Pipeline - Plain English Guide

**Last Updated:** November 2025
**Phase:** Phase 2 (Certificate-Based Authentication)
**Audience:** Non-technical stakeholders, testers, and documentation readers

---

## Overview

The Birthmark Android app authenticates photos taken on Android devices to prove they came from a real camera and weren't AI-generated. This document explains exactly how the app works, from installation to photo verification, in plain English without technical jargon.

---

## Part 1: Installing the App (First Launch)

### What Happens When You First Open the App

**Step 1: The Welcome Screen**
- You see a "Get Started" button and some information about what the app does
- The app explains that it will authenticate your photos, but never uploads them
- Only photo "fingerprints" (hashes) are sent to the blockchain, not actual images

**Step 2: You Tap "Get Started"**
Behind the scenes, the app begins provisioning (setting up your device):

1. **Generate Device Identity**
   - The app creates a unique "device secret" that will never change
   - Think of this like a permanent fingerprint for your phone
   - Formula: Random Number + Your Device ID = Device Secret
   - This secret is "frozen" - even if you reset your phone later, the secret stays the same

2. **Contact the Manufacturing Authority (SMA)**
   - The app sends your device secret to the SMA server
   - The SMA is like a certificate authority - it verifies your device is legitimate
   - This happens automatically in the background

3. **Receive Your Credentials**
   The SMA sends back a package of credentials:
   - **Device Certificate**: Like an ID card that proves your device is real
   - **Private Key**: A secret key used to "sign" your photos (like a signature)
   - **Certificate Chain**: Proof that your certificate is valid
   - **Encryption Keys**: 3,000 random encryption keys (3 sets of 1,000 keys each)
   - **Key Table Assignments**: Which 3 tables (out of 2,500 global tables) your device uses

4. **Save Everything Securely**
   - All credentials are stored in your Android device's secure Keystore
   - The Keystore is Android's built-in secure storage - it's hardware-backed on most devices
   - Your private key never leaves your device

5. **You're Ready!**
   - Provisioning takes about 2-3 seconds
   - You only do this once - the app remembers you're set up
   - You're taken to the camera screen

---

## Part 2: Taking a Photo (Every Time You Use the App)

### What Happens When You Capture a Photo

**Step 1: You Take a Photo**
- You see the camera viewfinder, just like the normal Camera app
- Tap the shutter button to take a photo
- The photo is saved to your device's gallery (like any camera app)

**Step 2: The App Computes the Photo Hash (Instant)**
This happens in the background while you're looking at the photo:

- The app reads the photo data (the actual image file)
- It runs a "hash function" (SHA-256) on the photo
- The hash is a 64-character "fingerprint" of the image
- Think of it like a barcode that uniquely identifies this exact photo
- **Example hash:** `a3f2d8c9b1e4f7a2c8d3e9f1b2c4d5e8f9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5`
- This takes about 10 milliseconds (instant)

**Important:** Only the hash is sent to the blockchain, never the actual photo. Your photos stay on your device.

**Step 3: The App Retrieves Your Certificate (Instant)**
- The app gets your device certificate from the Keystore
- This is the "ID card" you received during provisioning
- It contains your device identity (encrypted) and proves you're a real device

**Step 4: The App Creates a "Certificate Bundle" (Instant)**
The bundle contains:
- **Image Hash**: The 64-character fingerprint of your photo
- **Device Certificate**: Your device's ID card
- **Timestamp**: When the photo was taken (Unix timestamp)
- **GPS Hash (Optional)**: If location services are on, a hash of your GPS coordinates
- **Software Certificate (Future)**: Will include app version info in Phase 3

**Step 5: The App Signs the Bundle (Instant)**
- The app uses your private key (from Keystore) to "sign" the bundle
- Signing is like putting your signature on a document - it proves you created it
- The signature is created using ECDSA P-256 (an industry-standard algorithm)
- This takes about 1-2 milliseconds

The signature process:
1. Combine all bundle fields in a specific order (canonical format)
2. Use your private key to sign this combined data
3. Produce a signature (a string of characters)
4. Anyone with your certificate can verify this signature came from you

**Step 6: The App Submits to the Aggregation Server**
- The complete certificate bundle is sent over the internet to the aggregator
- The aggregator is like a postal service - it collects bundles and forwards them
- Endpoint: `POST /api/v1/submit-cert`
- If you're offline, the app uses WorkManager to retry when you're back online

**Step 7: You See "Submitted Successfully!"**
- The app shows a green checkmark
- The photo is now authenticated and registered on the blockchain
- You can take another photo or close the app

**Total Time:** Under 100 milliseconds from shutter press to submission (imperceptible to user)

---

## Part 3: Behind the Scenes (After You Submit)

### What Happens at the Aggregation Server

**Step 1: Server Receives Your Bundle**
- The aggregation server gets your certificate bundle
- It checks the bundle format is valid (correct fields, valid hash format, etc.)
- Status: "Pending Validation"

**Step 2: Server Contacts the SMA for Validation**
- The aggregator sends your certificate to the SMA: "Is this device legitimate?"
- The SMA decrypts your certificate and checks:
  - Is this a real device we provisioned?
  - Is the device blacklisted (abusing the system)?
  - Does the signature match the device's public key?
- The SMA responds: **PASS** or **FAIL**
- **Important:** The SMA never sees your image hash - only validates your device

**Step 3: Abuse Detection (Automatic)**
- The SMA tracks how many photos each device submits
- If you submit more than 10,000 photos in 24 hours: Automatic blacklist
- If you submit 8,000-10,000 photos in 24 hours: Warning flag
- This prevents spammers from flooding the system
- Normal users won't hit these limits (that's ~1 photo every 10 seconds for 24 hours!)

**Step 4: Server Batches Your Hash**
- If validation passes, your image hash is added to a batch
- The aggregator collects 100-1,000 hashes before submitting to the blockchain
- Batching happens every few minutes or when the batch is full
- This reduces blockchain costs (each batch is one transaction)

**Step 5: Batch Submitted to Blockchain**
- The aggregator sends the batch to the Birthmark blockchain
- The blockchain stores your image hash permanently in a block
- Endpoint: `POST /blockchain/submit-batch`
- Your hash is now immutably recorded with a timestamp

**Step 6: Confirmation**
- The blockchain assigns your hash a block number and transaction ID
- The aggregator marks your submission as "Confirmed"
- You can now verify your photo anytime by checking the blockchain

**Total Time:** Usually 1-5 minutes from submission to blockchain confirmation

---

## Part 4: Verifying a Photo Later

### How Anyone Can Check If a Photo is Authentic

**Scenario:** Someone sees your photo on social media and wants to verify it's real.

**Step 1: Get the Photo**
- Download the photo from wherever it's posted
- It can be a copy, screenshot, or re-upload - metadata doesn't matter

**Step 2: Compute the Hash**
- Use a verification tool (web app, mobile app, or command line)
- The tool computes the SHA-256 hash of the photo
- This produces the same 64-character fingerprint

**Step 3: Query the Blockchain**
- Send the hash to the Birthmark blockchain: "Is this hash registered?"
- Endpoint: `GET /api/v1/verify/{hash}`
- The blockchain searches its records

**Step 4: Get the Result**
Two possible outcomes:

**Verified:**
```json
{
  "verified": true,
  "timestamp": 1732050000,
  "block_height": 123456,
  "aggregator": "university_of_oregon"
}
```
Translation:
- "Yes, this photo was captured by a legitimate camera"
- "It was taken on [date/time from timestamp]"
- "It's recorded in block #123456 of the blockchain"
- "The University of Oregon aggregator validated it"

**NOT VERIFIED:**
```json
{
  "verified": false,
  "image_hash": "a3f2d8...",
  "timestamp": null
}
```
Translation:
- "This photo hash is not in our blockchain"
- "It might be AI-generated, heavily edited, or just not registered"
- "We can't confirm it came from a real camera"

**Step 5: Interpretation**
- **Verified = Real Camera:** High confidence the photo came from a legitimate device
- **Not Verified != Fake:** Could be a real photo that wasn't registered
- Verification proves authenticity; lack of verification doesn't prove fakeness

---

## Part 5: Privacy and Security

### What Data Leaves Your Device?

**Sent to the Blockchain:**
- SHA-256 hash of your photo (64 characters)
- Timestamp when photo was taken
- GPS hash (optional, only if you enable location)
- Your device certificate (encrypted device identity)

**Never Sent:**
- The actual photo or image data
- Your personal information (name, email, phone number)
- Your exact GPS coordinates (only a hash, if enabled)
- Metadata (EXIF data stays in the photo file)

### How Your Identity is Protected

**Device Certificate:**
- Your certificate contains an encrypted version of your device secret
- Only the SMA can decrypt it (using their master keys)
- The aggregator and blockchain never learn your device's identity
- The certificate proves "this is a legitimate device" without revealing which device

**Rotating Encryption:**
- Each photo uses a different encryption key (randomly selected from 3,000 keys)
- The SMA can't track which photos came from the same device
- This prevents profiling or tracking of individual users

**Blockchain Privacy:**
- Only image hashes are stored on-chain (not photos)
- Hashes are one-way: You can't reverse a hash to get the original photo
- No personal data is ever recorded on the blockchain

### Security Against Attacks

**Preventing Forgery:**
- Your device certificate is signed by the SMA's private key
- Only devices that went through provisioning have valid certificates
- Attackers can't create fake certificates without the SMA's private key
- ECDSA signatures ensure bundles can't be modified in transit

**Preventing Replay Attacks:**
- Each bundle includes a timestamp
- Old bundles can't be resubmitted (server checks timestamps)
- Certificates include random nonces to prevent duplication

**Preventing Abuse:**
- Automatic blacklisting at 10,000 photos/day per device
- The SMA tracks submission rates and flags suspicious devices
- Blacklisted devices can't submit new photos
- Rate limits prevent spam and DoS attacks

---

## Part 6: What Makes This Different?

### Comparison with Other Systems

**vs. C2PA (Content Authenticity Initiative):**
- **C2PA:** Embeds metadata in the photo file
  - Problem: Social media strips metadata when you upload
  - Solution: Works great for professional publishers, not for sharing
- **Birthmark:** Uses independent hash verification
  - Advantage: Works even after metadata is stripped
  - Limitation: Requires blockchain lookup, not self-contained

**vs. Watermarking:**
- **Watermarking:** Embeds invisible pattern in the image
  - Problem: Can be removed with editing, compression destroys it
  - Solution: Good for copyright, not for authenticity
- **Birthmark:** Hash-based verification
  - Advantage: Any pixel change invalidates the hash (tamper-evident)
  - Limitation: Can't track minor edits (that's by design)

**vs. Blockchain Photo Storage:**
- **Other Systems:** Upload entire photos to blockchain or IPFS
  - Problem: Expensive, slow, privacy concerns
  - Solution: Good for archival, not for everyday use
- **Birthmark:** Only stores hashes on-chain
  - Advantage: Fast, cheap, private
  - Limitation: Need the original photo to verify

---

## Part 7: Common Questions

### General Questions

**Q: Does this work if I edit the photo?**
A: No. Any change to the photo (crop, filter, brightness adjustment) changes the hash. This is by design - we're proving this exact photo came from a camera, not a modified version.

**Q: What if I take a screenshot of the photo?**
A: The screenshot is a different image (even if it looks identical), so it has a different hash. Only the original captured photo can be verified.

**Q: Can I verify someone else's photo?**
A: Yes! That's the whole point. Anyone can compute a hash and query the blockchain. Verification is public.

**Q: What if I lose my phone?**
A: Your photos are still verified (they're on the blockchain). But you'll need to provision a new device if you get a new phone. Each device has its own certificate.

**Q: Does this prove the photo wasn't edited?**
A: Yes, for that exact image. If the hash matches, it's the exact photo that came from the camera. But someone could edit it and submit the edited version elsewhere.

**Q: How much does it cost?**
A: The blockchain is operated by institutions (universities, archives) with zero gas fees. The app is free. There's no cost to users.

### Technical Questions (Simplified)

**Q: How big is the hash?**
A: 64 characters (256 bits). Example: `a3f2d8c9b1e4f7a2c8d3e9f1b2c4d5e8f9a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5`

**Q: How many photos can I take?**
A: Unlimited, but more than 10,000 per day will trigger abuse detection. Normal users won't hit this.

**Q: What happens if I'm offline?**
A: Submissions are queued using Android's WorkManager and will be sent when you're back online.

**Q: Can the SMA see my photos?**
A: No. The SMA only sees your encrypted device certificate. It never receives image hashes or photos.

**Q: What stops someone from copying my certificate?**
A: Your certificate is useless without your private key, which is locked in your Android Keystore. Even you can't extract it. It can only be used for signing, not copied.

**Q: How long does verification last?**
A: Forever (in theory). Blockchains are permanent. As long as the Birthmark blockchain exists, your photo can be verified.

---

## Part 8: The Complete Journey (Timeline)

### Provisioning (One-Time Setup)
```
T+0.0s    You tap "Get Started"
T+0.1s    Device secret generated
T+0.2s    Contacting SMA server...
T+1.5s    SMA provisions device, returns certificate + keys
T+1.6s    Credentials saved to Keystore
T+1.7s    Provisioning complete
T+1.8s    Camera screen appears
```

### Photo Capture and Authentication (Every Photo)
```
T+0.0s    You tap shutter button
T+0.0s    Photo captured, saved to gallery
T+0.01s   Computing SHA-256 hash of photo...
T+0.02s   Hash computed: a3f2d8c9b1e4...
T+0.02s   Retrieving device certificate from Keystore...
T+0.03s   Creating certificate bundle...
T+0.03s   Signing bundle with ECDSA P-256...
T+0.04s   Bundle signed, ready to submit
T+0.05s   Submitting to aggregation server...
T+0.20s   Server received bundle (HTTP 202 Accepted)
T+0.20s   "Submitted Successfully!" shown to user
```

### Server-Side Processing (Background)
```
T+0.0s    Aggregator receives bundle
T+0.1s    Validating bundle format...
T+0.2s    Bundle valid, contacting SMA...
T+0.5s    SMA validates certificate: PASS
T+0.6s    Adding hash to batch queue...
T+120s    Batch full (1000 hashes), submitting to blockchain...
T+125s    Blockchain confirms transaction (block #123456)
T+125s    Submission marked as "Confirmed"
```

### Verification (Later, By Anyone)
```
T+0.0s    Verifier uploads photo to web app
T+0.1s    Computing hash...
T+0.2s    Querying blockchain for hash a3f2d8c9b1e4...
T+0.3s    Blockchain found hash in block #123456
T+0.3s    VERIFIED - Captured Nov 20, 2025 at 5:30 PM
```

---

## Part 9: Future Enhancements

### Coming in Phase 3

**Software Certificates:**
- Apps like Photoshop will also get certificates
- Edited photos will include a "modification record"
- You'll see: "Original authentic, minor edits by Adobe Photoshop 2026"

**GPS Verification:**
- Optionally prove where a photo was taken
- GPS coordinates hashed for privacy
- Useful for journalism and evidence

**Enhanced Abuse Detection:**
- Machine learning to detect suspicious patterns
- Graduated warnings before blacklisting
- Appeal process for false positives

---

## Summary

The Birthmark Android app provides a simple, privacy-preserving way to prove photos came from real cameras:

1. **One-Time Setup:** Provision your device with the SMA (2 seconds)
2. **Every Photo:** App hashes photo, signs bundle, submits to blockchain (instant)
3. **Later Verification:** Anyone can check if a photo is authentic (1 second)

**Key Benefits:**
- Photos stay on your device (only hashes leave)
- Works after social media strips metadata
- Free to use (no blockchain fees)
- Permanent verification (blockchain is immutable)
- Privacy-preserving (rotating encryption, no tracking)

**Key Limitation:**
- Only verifies unedited photos (by design)
- Requires blockchain lookup (not self-contained)

**Target Use Case:**
Proving a photo came from a real camera during the 2028 Presidential Election and beyond, combating AI-generated misinformation while preserving privacy.

---

**For More Information:**
- Technical Architecture: `docs/architecture/PHASE_2_ARCHITECTURE_UPDATES.md`
- Codebase Overview: `CLAUDE.md`
- Phase Plans: `docs/phase_plans/`
