# The Birthmark Standard

**Hardware-backed photo authentication for the AI generation era**

---

## The Problem

Trust in online media is collapsing. As AI-generated images become indistinguishable from photographs, the public can no longer confidently determine what's real. This erodes our shared sense of reality and undermines the credibility of legitimate journalism, documentary work, and photographic evidence.

Professional photographers face an unprecedented credibility crisis. Photojournalists, competition photographers, and documentary creators need a way to prove their images came from real cameras—not AI generators.

Current solutions like C2PA embed authentication in image metadata, but this metadata gets stripped when images are shared on social media, converted between formats, or edited. By some estimates, 95% of real-world image distribution loses this metadata.

## Our Solution

The Birthmark Standard authenticates images at the hardware level using each camera's unique sensor fingerprint. When a photo is taken, the camera's secure element cryptographically signs the image hash using rotating keys that only the manufacturer can validate. These hashes are stored on an independent Birthmark blockchain operated by trusted institutions (universities, archives, journalism organizations).

**The result:** Anyone can verify that an image originated from a legitimate camera at a specific time. The blockchain stores authentication independently of image metadata, so verification works even if the image is converted to different formats or has metadata stripped. Editing operations that want to maintain authentication must declare their transformations and pass deviation validation. No accounts required. No gas fees. No centralized gatekeepers. Just cryptographic proof.

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
   Authentication bundle sent to submission server
   Manufacturer validates camera authenticity (PASS/FAIL)
   Image hash submitted to blockchain

3. STORE
   SHA-256 hash stored on independent blockchain
   Byzantine fault tolerant network (20 nodes, 3 minimum)
   Immutable timestamp with zero gas fees

4. VERIFY
   Anyone can hash an image and query the blockchain
   Direct hash lookup confirms authentication
   No account needed, no API keys, no fees, just math
```

### Visual Pipeline

![Birthmark Authentication Pipeline](./docs/Full_Visual_Pipeline.png)

The complete system architecture showing how all components interact: from camera capture through manufacturer validation, submission server processing, blockchain storage, and finally public verification.

---

## Current Status

**Phase 1: Hardware Prototype** (Complete)

We've built and deployed a working Raspberry Pi-based camera prototype that demonstrates the complete authentication pipeline from capture through blockchain verification.

**Completed:**
- ✅ Raspberry Pi 4 HQ Camera with hardware authentication
- ✅ Submission server with manufacturer validation
- ✅ Substrate blockchain (Birthmark Media Registry)
- ✅ End-to-end authentication pipeline validated
- ✅ **Storage optimization: 69% reduction** (450 → 140 bytes/record)

**Current Work:**
- 🎥 Producing demonstration video showing complete workflow

---

## Why This Matters

### For Photojournalists
Prove your images are authentic when covering conflict zones, protests, or breaking news. Your credibility travels with the image, not with your employer's reputation.

### For Fact-Checkers
Quickly determine if viral images could have been captured by legitimate cameras at the claimed time, or were AI-generated.

### For E-Commerce
Prevent product listing fraud with verified photos. Buyers can trust that product images came from real cameras, not generative AI.

### For the Public
Evaluate media trustworthiness without relying on platform judgments or institutional gatekeepers. Anyone can verify any image.

---

## Technical Architecture

The system consists of five main components:

**Camera Device** - Captures raw sensor data, computes SHA-256 hash, encrypts device fingerprint with rotating keys from assigned key tables, submits authentication bundle.

**Submission Server** - Receives submissions, validates camera authenticity via manufacturer, submits validated hashes to blockchain.

**Simulated Manufacturer Authority (SMA)** - Maintains key tables and NUC records, validates encrypted tokens without seeing image content, returns PASS/FAIL.

**Birthmark Media Registry** - Independent Substrate blockchain (selected for forkless runtime upgrade capability) operated by trusted institutions (target: 20 nodes, 3 minimum for operation), Byzantine fault tolerant consensus, stores SHA-256 hashes on-chain (<1KB per record, 1 billion records per terabyte), direct hash lookup queries, zero gas fees, rate-limited submissions (500 per 10 minutes per IP) to prevent spam. Verification is non-time-sensitive; images become verifiable within minutes of capture with no user-facing delay.

**Verification Client** - Hashes image, queries blockchain for direct hash match, displays authentication result.

### Blockchain Storage Optimization

We've optimized the Substrate blockchain to achieve **69% storage reduction** (from ~450 bytes to ~140 bytes per record). This makes operating a registry node sustainable at **$200-350/year** for journalism institutions, even at millions of images per day.

**Key optimizations:**
- Binary hash storage (32 bytes vs 64 bytes hex)
- Authority lookup tables (2 bytes vs 20-100 bytes strings)
- Compact encoding for timestamps and block numbers
- Removed 8 unnecessary pallets while preserving forkless upgrades

**Economics at 1M images/day:**
- Storage: 47 GB/year (vs 151 GB unoptimized)
- Node cost: $200-350/year (vs $500-800 unoptimized)
- Scales to 10M images/day at $500-800/year

For detailed analysis, see [docs/OPTIMIZATION_RESULTS.md](./docs/OPTIMIZATION_RESULTS.md).

For detailed technical specifications, see [CLAUDE.md](./CLAUDE.md) and the documentation in `/docs`.

---

## Repository Structure

```
birthmark/
├── packages/
│   ├── blockchain/       # Merged submission server + blockchain node
│   ├── camera-pi/        # Raspberry Pi camera prototype
│   ├── registry/         # Substrate blockchain (Birthmark Media Registry)
│   ├── sma/              # Simulated Manufacturer Authority
│   └── verifier/         # Verification client
├── shared/
│   ├── certificates/     # Certificate handling utilities
│   ├── crypto/           # Cryptographic utilities
│   ├── protocols/        # API specifications
│   └── types/            # Common data structures
└── docs/
    ├── architecture/     # Architecture documents and design updates
    ├── phase-plans/      # Phase implementation plans
    └── testing/          # Testing guides and reports
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

**Phase 1: Proof of Concept** (Complete)
- Built working Raspberry Pi camera prototype
- Deployed submission server and Substrate blockchain
- Validated complete authentication pipeline

**Phase 2: Mobile Implementation** (Next)
- Android camera app with native authentication
- User testing with journalists and photographers (50-100 users)
- Performance optimization and benchmarking
- Developer tools and SDKs

**Phase 3: Production Network**
- Camera manufacturer partnerships and integrations
- Multi-institution blockchain network (target: 20 nodes across journalism organizations and universities)
- Public verification tools and browser extensions
- Standards body engagement (W3C, IETF)

Our goal is to establish trustworthy media authentication infrastructure that helps restore confidence in online information and supports our shared ability to distinguish reality from fabrication.

---

## Documentation

- [CLAUDE.md](./CLAUDE.md) - Development context and technical specifications for Phase 1
- [Phase Plans](./docs/phase-plans/) - Detailed implementation roadmaps for each phase
- [Architecture Docs](./docs/architecture/) - Architecture updates and design documents
- [Storage Optimization](./docs/OPTIMIZATION_RESULTS.md) - 69% storage reduction analysis and implementation
- [LICENSING.md](./LICENSING.md) - Complete licensing guide with use cases and compliance
- [Phase 1 Deployment Guide](./docs/PHASE_1_DEPLOYMENT_GUIDE.md) - Production deployment instructions

---

## License

The Birthmark Standard uses a dual-licensing structure:

- **AGPL-3.0-or-later** for core trust infrastructure (blockchain/registry)
- **Apache-2.0** for reference implementations and tools (camera, verifier, shared utilities)

This approach protects the verification infrastructure as public goods while enabling commercial adoption by camera manufacturers and developers.

**Quick Summary:**
- Using Birthmark authentication in your camera/app? → Apache-2.0 (permissive, commercial-friendly)
- Operating a registry node? → AGPL-3.0 (modifications must be published)
- Building verification tools? → Apache-2.0 (permissive, commercial-friendly)

For detailed information, see:
- [LICENSE](./LICENSE) - Overview of dual-licensing structure
- [LICENSING.md](./LICENSING.md) - Complete guide with use cases and compliance requirements
- Individual LICENSE files in each package directory

---

## Contact

**The Birthmark Standard Foundation** |
Website: [birthmarkstandard.org](https://birthmarkstandard.org) |
Email: [contact@birthmarkstandard.org](mailto:contact@birthmarkstandard.org) |
Discord: [Join our community](https://discord.gg/9Ts7dM9pb5)

**Samuel C. Ryan** |
Founder & Executive Director |
LinkedIn: [linkedin.com/in/samuelcryan](https://www.linkedin.com/in/samuelcryan)

---

*Building public good infrastructure for trust in digital media.*
