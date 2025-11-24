# The Birthmark Standard

**Hardware-backed photo authentication for the AI generation era**

---

## The Problem

Professional photographers face an unprecedented credibility crisis. As AI-generated images become indistinguishable from photographs, legitimate photographic work is increasingly dismissed as fake. Photojournalists, competition photographers, and documentary creators need a way to prove their images came from real cameras—not AI generators.

Current solutions like C2PA embed authentication in image metadata, but this metadata gets stripped when images are shared on social media, converted between formats, or edited. By some estimates, 95% of real-world image distribution loses this metadata.

## Our Solution

The Birthmark Standard authenticates images at the hardware level using each camera's unique sensor fingerprint. When a photo is taken, the camera's secure element cryptographically signs the image hash using rotating keys that only the manufacturer can validate. These hashes are stored on a custom Birthmark blockchain operated by like-minded institutions (universities, archives, journalism organizations).

**The result:** Anyone can verify that an image originated from a legitimate camera at a specific time, even after the image has been copied, compressed, cropped, or had its metadata stripped. No accounts required. No gas fees. No centralized gatekeepers. Just cryptographic proof.

### Key Properties

- **Hardware root of trust** - Camera sensor NUC maps provide unforgeable device identity
- **Privacy preserving** - Rotating keys prevent tracking individual cameras
- **Metadata independent** - Verification survives social media sharing
- **Open source** - All code publicly auditable
- **Decentralized** - No single point of control or failure
- **Complementary to C2PA** - Works alongside existing standards

---

## How It Works

```
1. CAPTURE
   Camera sensor captures image
   Secure element hashes raw sensor data
   NUC fingerprint encrypted with rotating key

2. SUBMIT
   Authentication bundle sent to aggregation server
   Manufacturer validates camera authenticity (PASS/FAIL)
   Image hash submitted to blockchain

3. STORE
   Full SHA-256 hash stored directly on-chain
   Birthmark blockchain nodes (operated by institutions)
   Immutable timestamp with zero gas fees

4. VERIFY
   Anyone can hash an image and query the blockchain
   Direct hash lookup confirms authentication
   No account needed, no API keys, no fees, just math
```

---

## Current Status

**Phase 1: Hardware Prototype** (In Progress)

We're building a Raspberry Pi-based camera prototype that demonstrates the complete authentication pipeline. This proves the architecture works before seeking manufacturer partnerships.

- Raspberry Pi 4 + HQ Camera + TPM secure element
- Aggregation server with SMA validation
- Custom blockchain nodes operated by institutions
- Photography club user validation

**Target:** 2028 Presidential Election deployment

---

## Why This Matters

### For Photojournalists
Prove your images are authentic when covering conflict zones, protests, or breaking news. Your credibility travels with the image, not with your employer's reputation.

### For Competition Photographers  
Enforce "no AI" rules with cryptographic certainty. Judges can verify entries came from real cameras.

### For Fact-Checkers
Quickly determine if an image could have been captured by a legitimate camera at the claimed time.

### For the Public
Evaluate media trustworthiness without relying on platform judgments or institutional gatekeepers.

---

## Technical Architecture

The system consists of five main components:

**Camera Device** - Captures raw sensor data, computes SHA-256 hash, encrypts device fingerprint with rotating keys from assigned key tables, submits authentication bundle.

**Aggregation Server** - Receives submissions, validates camera authenticity via manufacturer, submits validated hashes to blockchain.

**Simulated Manufacturer Authority (SMA)** - Maintains key tables and NUC records, validates encrypted tokens without seeing image content, returns PASS/FAIL.

**Birthmark Blockchain** - Custom blockchain operated by trusted institutions, stores full SHA-256 hashes directly on-chain, provides direct hash lookup queries, zero gas fees.

**Verification Client** - Hashes image, queries blockchain for direct hash match, displays authentication result.

For detailed technical specifications, see [CLAUDE.md](./CLAUDE.md) and the documentation in `/docs`.

---

## Repository Structure

```
birthmark/
├── packages/
│   ├── camera-pi/        # Raspberry Pi prototype
│   ├── aggregator/       # Aggregation server
│   ├── sma/              # Simulated Manufacturer Authority
│   ├── blockchain/       # Custom Birthmark blockchain
│   ├── mobile-app/       # Android app (Phase 2)
│   └── verifier/         # Verification client
├── shared/
│   ├── types/            # Common data structures
│   ├── crypto/           # Cryptographic utilities
│   └── protocols/        # API specifications
└── docs/
    ├── architecture/     # System diagrams
    └── phase-plans/      # Development roadmaps
```

---

## Relationship to C2PA

The Birthmark Standard is **complementary** to C2PA, not competitive. 

C2PA provides rich provenance metadata (camera settings, edit history, creator identity) when that metadata is preserved. Birthmark provides verification when metadata is stripped.

Together, they offer comprehensive authentication:
- C2PA for detailed provenance when available
- Birthmark for existence proof when metadata is lost

Camera manufacturers can implement both standards.

---

## The Birthmark Standard Foundation

This project is developed by The Birthmark Standard Foundation, a 501(c)(3) nonprofit organization (pending). Our mission:

> To develop and maintain open-source, privacy-preserving media authentication infrastructure as a public good, enabling individuals and institutions to verify the origin and authenticity of digital media independently of corporate or governmental gatekeepers.

**Core Principles:**
- Transparent operations and open governance
- All code publicly auditable
- Infrastructure for everyone, not commercial product
- Privacy protection and surveillance resistance built-in
- No tokens, no speculation, pure infrastructure

---

## Get Involved

### For Developers
- Review the architecture and provide feedback
- Contribute to open-source implementation
- Help with security audits and code review

### For Photographers
- Join our Phase 1 photography club testing
- Provide feedback on workflow integration
- Share your authentication use cases

### For Journalists
- Discuss authentication needs for your work
- Help validate the problem statement
- Consider pilot participation

### For Manufacturers
- Explore hardware integration opportunities
- Review technical specifications
- Discuss partnership possibilities

---

## Roadmap

**Phase 1** (Current) - Hardware prototype with Raspberry Pi, photography club validation, initial blockchain deployment

**Phase 2** - Android mobile app, broader user testing (50-100 photographers), performance benchmarking

**Phase 3** - Manufacturer partnerships, production blockchain network with institutional nodes, public verification tools

**Target** - Deployed infrastructure for 2028 Presidential Election

---

## Documentation

- [Technical Architecture](./docs/architecture/) - System diagrams and component specifications
- [Phase Plans](./docs/phase-plans/) - Detailed implementation roadmaps
- [CLAUDE.md](./CLAUDE.md) - Development context for use with Claude Code
- [C2PA Comparison](./docs/birthmark-vs-c2pa-comparison.md) - How standards complement each other

---

## Contact

**The Birthmark Standard Foundation**
Website: [birthmarkstandard.org](https://birthmarkstandard.org)
Email: [contact@birthmarkstandard.org](mailto:contact@birthmarkstandard.org)
Discord: [Join our community](https://discord.gg/btUU6qZK)

**Samuel C. Ryan**
Founder & Executive Director
LinkedIn: [linkedin.com/in/samuelcryan](https://www.linkedin.com/in/samuelcryan)

---

## License

Apache 2.0

---

*Building public good infrastructure for trust in digital media.*
