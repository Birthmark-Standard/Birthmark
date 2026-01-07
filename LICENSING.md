# Birthmark Standard Licensing Guide

This document explains the licensing structure of the Birthmark Standard, why we chose this approach, and how to comply with the licenses when using or contributing to this project.

## Table of Contents

1. [Overview](#overview)
2. [Why Dual Licensing?](#why-dual-licensing)
3. [What Each License Means](#what-each-license-means)
4. [Component-by-Component Breakdown](#component-by-component-breakdown)
5. [Compliance Guide](#compliance-guide)
6. [Use Case Examples](#use-case-examples)
7. [Contributing](#contributing)
8. [FAQ](#faq)

---

## Overview

The Birthmark Standard uses **two different open source licenses** for different parts of the codebase:

- **AGPL-3.0-or-later** for the core trust infrastructure (blockchain/registry)
- **Apache-2.0** for reference implementations, tools, and utilities

This dual-license structure protects the integrity of the verification infrastructure while enabling commercial adoption of the authentication protocol.

---

## Why Dual Licensing?

### The Challenge

The Birthmark Standard must balance two critical objectives:

1. **Protect public trust infrastructure** - The verification system must remain transparent and cannot be captured for proprietary use
2. **Enable commercial adoption** - Camera manufacturers and software developers need licensing freedom to integrate authentication

A single license cannot achieve both goals effectively.

### The Solution

**AGPL-3.0 for Infrastructure**

The submission server and blockchain registry are the trust anchors of the entire system. If these components became proprietary:

- Trust would be centralized in private companies
- Users couldn't verify the integrity of authentication
- The system could be manipulated or controlled
- Network effects would favor monopolistic control

AGPL's network copyleft ensures that anyone operating modified registry nodes must publish their source code, maintaining transparency and preventing capture.

**Apache-2.0 for Implementations**

Camera reference implementations, verification clients, and developer tools need broad adoption. Apache-2.0:

- Allows camera manufacturers to integrate without licensing friction
- Enables companies to build commercial products and services
- Provides patent protection for contributors and users
- Compatible with most other open source licenses
- Encourages ecosystem development

### Precedent

This approach follows successful infrastructure projects:

- **MongoDB**: SSPL for database server, Apache for drivers
- **Elastic**: SSPL for search engine, Apache for clients
- **HashiCorp**: BSL for core products, MPL for libraries
- **MariaDB**: GPL for server, LGPL for connectors

These projects protect core infrastructure while enabling ecosystem growth.

---

## What Each License Means

### AGPL-3.0-or-later

The **GNU Affero General Public License v3.0** is a strong copyleft license specifically designed for network services.

**Key Characteristics:**

- **Copyleft**: Derivative works must also be open source under AGPL
- **Network provision**: Running modified code as a service requires publishing source
- **Patent grant**: Contributors grant patent licenses to users
- **Compatibility**: Compatible with GPL v3, but not with Apache, MIT, or BSD

**What it means for you:**

- ✅ You can use, modify, and distribute the code freely
- ✅ You can run the code as a service (including commercially)
- ❌ If you modify and run it as a service, you must publish your modifications
- ❌ You cannot integrate AGPL code into proprietary applications without open-sourcing them

**Official license text**: https://www.gnu.org/licenses/agpl-3.0.txt

### Apache-2.0

The **Apache License v2.0** is a permissive license that allows broad commercial use.

**Key Characteristics:**

- **Permissive**: Can be incorporated into proprietary software
- **Patent grant**: Contributors explicitly grant patent licenses
- **Trademark protection**: Does not grant trademark rights
- **Attribution**: Requires license and copyright notice preservation

**What it means for you:**

- ✅ You can use, modify, and distribute the code freely
- ✅ You can incorporate it into proprietary products
- ✅ You can modify without publishing changes
- ✅ You receive explicit patent protection
- ⚠️ You must include copyright notices and license text
- ⚠️ You must document modifications in NOTICE files

**Official license text**: http://www.apache.org/licenses/LICENSE-2.0

---

## Component-by-Component Breakdown

### AGPL-3.0-or-later Components

#### `packages/blockchain/`

**Contains**: Submission server, validation logic, blockchain client

**Why AGPL**: This is the entry point where photographers submit authentication requests. It must remain transparent to prevent:
- Selective censorship of submissions
- Manipulation of validation results
- Proprietary modifications that undermine trust
- Centralized control of authentication

**Who runs this**: Journalism organizations, universities, archives - institutions with reputational stakes in credibility.

#### `packages/registry/`

**Contains**: Birthmark Media Registry blockchain implementation

**Why AGPL**: The registry stores the permanent authentication records. It must remain transparent to prevent:
- Hidden modifications to authentication records
- Proprietary registry nodes that could fork consensus
- Manipulation of verification queries
- Creation of "premium" registry access tiers

**Who runs this**: Coalition of journalism organizations operating distributed nodes.

---

### Apache-2.0 Components

#### `packages/camera-pi/`

**Contains**: Raspberry Pi camera reference implementation

**Why Apache**: Camera manufacturers need freedom to:
- Study the reference implementation
- Integrate authentication into proprietary firmware
- Modify for different hardware platforms
- Build commercial features around core authentication
- Protect their proprietary camera IP

**Example use**: Canon studies this code and implements Birthmark authentication in their mirrorless cameras with proprietary image processing.

#### `packages/sma/`

**Contains**: Simulated Manufacturer Authority validation server

**Why Apache**: Manufacturers need freedom to:
- Run their own authority servers privately
- Integrate with proprietary manufacturing systems
- Customize validation logic for their hardware
- Protect camera provisioning infrastructure

**Example use**: Sony operates their own manufacturer authority server integrated with their secure element provisioning system.

#### `packages/verifier/`

**Contains**: Verification client and web interface

**Why Apache**: Developers should be able to:
- Build verification into journalism platforms
- Create browser extensions
- Develop mobile verification apps
- Integrate into photo management software
- Build commercial verification services

**Example use**: The New York Times builds Birthmark verification into their CMS without open-sourcing their entire platform.

#### `shared/`

**Contains**: Common cryptographic utilities, data structures, protocols

**Why Apache**: These utilities need maximum reusability:
- Camera manufacturers can use them in proprietary firmware
- Software developers can integrate into any application
- Compatible with most open source projects
- No licensing friction for ecosystem tools

**Example use**: Third-party developer builds a Photoshop plugin that uses `shared/crypto/` to verify images.

#### `docs/`

**Contains**: Documentation, specifications, architecture materials

**Why Apache**: Knowledge should be freely accessible:
- Anyone can learn from the specifications
- Documentation can be adapted for training materials
- Specifications can be incorporated into standards documents
- Educational use without restriction

**Example use**: University includes Birthmark architecture in digital forensics curriculum.

---

## Compliance Guide

### Using AGPL Components (blockchain/registry)

#### Scenario 1: Running Unmodified Code

**What you're doing**: Operating a Birthmark registry node using the published codebase without modifications.

**Compliance requirements**:
- ✅ Include the LICENSE file
- ✅ Preserve copyright notices
- ✅ No source code publication required (code is already public)

**Example**: A journalism organization runs the registry using docker-compose from the official repository.

#### Scenario 2: Running Modified Code as a Service

**What you're doing**: Modifying the registry code (e.g., adding analytics, custom validation, different database) and running it as a public or private service.

**Compliance requirements**:
- ✅ Include the LICENSE file
- ✅ Preserve copyright notices
- ✅ Document your modifications
- ✅ **Publish your complete modified source code**
- ✅ Provide users access to the source (e.g., GitHub link in service interface)

**Example**: A university modifies the registry to add academic research metrics and must publish their modifications on GitHub.

#### Scenario 3: Embedding in a Larger Application

**What you're doing**: Incorporating registry code into a proprietary application.

**Compliance requirements**:
- ⚠️ **This is very difficult** - the AGPL requires that the entire combined work be licensed under AGPL
- ✅ Better approach: Run registry as a separate service and communicate via API
- ✅ Alternative: Keep registry components strictly separated and isolate via network boundaries

**Example**: A company wants to build a proprietary photo management platform. They run the registry as a separate service and query it via API rather than embedding the code.

### Using Apache Components (everything else)

#### Scenario 1: Using in Open Source Project

**What you're doing**: Incorporating camera-pi, verifier, or shared utilities into your own open source project.

**Compliance requirements**:
- ✅ Include a copy of the Apache-2.0 LICENSE
- ✅ Preserve copyright notices
- ✅ If a NOTICE file exists, include it and document your modifications

**Example**: A photographer builds an open source photo gallery that uses `shared/crypto/` for verification.

#### Scenario 2: Using in Commercial Product

**What you're doing**: Incorporating Apache-licensed components into a proprietary commercial product.

**Compliance requirements**:
- ✅ Include a copy of the Apache-2.0 LICENSE (can be in a "licenses" folder or about dialog)
- ✅ Preserve copyright notices
- ✅ If you modify the code, document changes in your NOTICE file
- ❌ You do NOT need to publish your source code
- ❌ You do NOT need to open source your modifications

**Example**: Adobe builds Birthmark verification into Lightroom and includes the Apache license in their legal notices.

#### Scenario 3: Building a Derivative Work

**What you're doing**: Taking the camera-pi reference implementation and heavily modifying it for your own camera hardware.

**Compliance requirements**:
- ✅ Include a copy of the Apache-2.0 LICENSE
- ✅ Preserve original copyright notices
- ✅ Add your own copyright notice for your modifications
- ✅ Document modifications in a NOTICE file
- ❌ You do NOT need to publish your source code

**Example**: Fujifilm adapts camera-pi for their X-series cameras and keeps their implementation proprietary.

---

## Use Case Examples

### Example 1: Camera Manufacturer Integration

**Scenario**: Canon wants to integrate Birthmark authentication into their EOS R series cameras.

**What they do**:
1. Study `packages/camera-pi/` (Apache-2.0) to understand the reference implementation
2. Study `packages/sma/` (Apache-2.0) to understand manufacturer authority requirements
3. Use `shared/crypto/` (Apache-2.0) cryptographic utilities
4. Implement their own secure element integration (proprietary)
5. Operate their own manufacturer authority server (proprietary)
6. Submit authenticated photos to public AGPL-licensed registry nodes

**Compliance**:
- ✅ Include Apache license in firmware legal notices
- ✅ Preserve copyright notices from borrowed code
- ❌ Do NOT need to open-source their camera firmware
- ❌ Do NOT need to publish their authority server code
- ✅ Must submit to public registry nodes (cannot create proprietary registry)

**Result**: Canon ships Birthmark-compatible cameras with full patent protection and licensing freedom.

---

### Example 2: Journalism Organization Operating Registry

**Scenario**: The Organized Crime and Corruption Reporting Project (OCCRP) wants to operate a Birthmark registry node.

**What they do**:
1. Deploy `packages/blockchain/` and `packages/registry/` (both AGPL-3.0)
2. Run nodes as public services for authentication and verification
3. Decide to add custom analytics to track authentication patterns
4. Modify registry code to add analytics database

**Compliance**:
- ✅ Include AGPL license
- ✅ Preserve copyright notices
- ✅ **Publish their modified source code** (including analytics additions)
- ✅ Provide users a link to their source repository in the service interface

**Result**: OCCRP operates a registry node with custom features while maintaining transparency.

---

### Example 3: Third-Party Verification Tool

**Scenario**: A developer wants to build a browser extension that verifies images on social media.

**What they do**:
1. Use `packages/verifier/` (Apache-2.0) as the basis for their extension
2. Use `shared/crypto/` (Apache-2.0) for hashing
3. Query public AGPL-licensed registry nodes via API
4. Add proprietary features like batch verification and reputation scores
5. Sell the extension as a commercial product

**Compliance**:
- ✅ Include Apache license for verifier and shared components
- ✅ Preserve copyright notices
- ❌ Do NOT need to open-source the extension
- ❌ Do NOT need to publish custom features

**Result**: Developer builds a commercial product with licensing freedom while relying on public infrastructure.

---

### Example 4: University Research Project

**Scenario**: MIT researchers want to study authentication patterns and modify the registry for research purposes.

**What they do**:
1. Fork `packages/registry/` (AGPL-3.0)
2. Add research instrumentation to collect metadata
3. Modify consensus rules for experimental analysis
4. Run modified registry as a research service (not part of production network)

**Compliance**:
- ✅ Include AGPL license
- ✅ Preserve copyright notices
- ✅ **Publish their research modifications** (satisfies open science requirements too)
- ✅ Document research changes

**Result**: Researchers can experiment while maintaining transparency and sharing knowledge.

---

### Example 5: News Organization Internal Tool

**Scenario**: The Washington Post wants to build an internal CMS plugin that verifies uploaded photos.

**What they do**:
1. Use `packages/verifier/` (Apache-2.0) for verification client
2. Use `shared/` (Apache-2.0) utilities
3. Build proprietary CMS integration
4. Query public AGPL registry nodes via API
5. Keep the tool internal (not published)

**Compliance**:
- ✅ Include Apache license in internal documentation
- ✅ Preserve copyright notices
- ❌ Do NOT need to publish internal tool code

**Result**: News organization builds proprietary tools while using public verification infrastructure.

---

## Contributing

### Contribution License

By contributing to the Birthmark Standard, you agree that:

1. **Your contributions will be licensed** under the same license as the component you're modifying:
   - Contributions to `blockchain/` or `registry/` → AGPL-3.0-or-later
   - Contributions to all other components → Apache-2.0

2. **You have the right** to license your contributions under these terms

3. **You grant** The Birthmark Standard Foundation a perpetual, worldwide, non-exclusive, royalty-free license to use your contributions

4. **You waive** any moral rights that might interfere with the project's licensing

### What This Means

- If you submit a PR to `packages/blockchain/`, you're licensing it under AGPL-3.0
- If you submit a PR to `packages/camera-pi/`, you're licensing it under Apache-2.0
- You cannot submit code you don't have the right to license
- The Foundation can relicense if needed for compatibility (rare)

### Contributor Certificate of Origin

We may ask you to sign a Contributor License Agreement (CLA) for significant contributions. This protects both you and the project.

---

## FAQ

### General Questions

**Q: Why not use a single license for everything?**

A: A single license can't achieve both goals. AGPL would prevent commercial adoption by manufacturers. Apache would allow proprietary registries, destroying trust. Dual licensing protects infrastructure while enabling adoption.

**Q: Can I use Birthmark in my commercial product?**

A: Yes! Most components (camera, verifier, shared utilities) are Apache-2.0 and explicitly allow commercial use. Only the registry infrastructure is AGPL.

**Q: Is this "open core" or "open source theater"?**

A: No. This is 100% open source - every line of code is published under OSI-approved licenses. There are no proprietary components or "enterprise" features behind paywalls. The license choice differs based on role in trust infrastructure.

**Q: Why AGPL instead of GPL?**

A: AGPL's network provision is critical. GPL's copyleft only triggers on distribution. Since registries are network services (not distributed software), GPL wouldn't protect against proprietary modifications. AGPL ensures transparency even when code runs as a service.

### AGPL Questions

**Q: Can I run a private registry node for my organization?**

A: Yes, but if you modify the code, you must publish your modifications and provide users access to the source. If you run unmodified code, you just need to preserve license notices.

**Q: What if I want to add proprietary features to the registry?**

A: AGPL prevents this by design. The registry must remain transparent. If you need custom features, you have two options:
1. Contribute them upstream as open source
2. Build them as a separate service that queries the registry via API

**Q: Can I query the registry from my proprietary application?**

A: Yes! Querying a service via API doesn't create a derivative work. Your application remains independent and can use any license.

**Q: Does AGPL mean I can't charge for running a registry node?**

A: No, you can charge for services. AGPL doesn't restrict commercial use, only requires that modifications be published. Many companies successfully build businesses around AGPL software.

### Apache Questions

**Q: Can I build a proprietary camera that uses Birthmark?**

A: Yes! The camera implementation (`packages/camera-pi/`) is Apache-2.0 specifically to enable this. You can study the reference implementation, adapt it for your hardware, and keep your modifications proprietary.

**Q: Do I need to publish my camera firmware?**

A: No. Apache-2.0 doesn't require publication of modifications or derivative works. You just need to include the Apache license and preserve copyright notices.

**Q: What's the "NOTICE file" requirement?**

A: If you modify Apache-licensed code, you should document your changes in a NOTICE file. This doesn't mean publishing source code - just noting "Modified by Company X" so your changes aren't attributed to the original authors.

**Q: Can I remove the copyright notices?**

A: No. You must preserve original copyright notices and license attributions. This is a requirement of both AGPL and Apache licenses.

### Integration Questions

**Q: Can I mix AGPL and Apache code in my application?**

A: It depends on how you integrate:
- ✅ **Safe**: Query AGPL registry via API from Apache-licensed client (separate processes)
- ✅ **Safe**: Use Apache-licensed utilities independently of AGPL components
- ⚠️ **Complex**: Link AGPL and Apache code in same process (triggers AGPL copyleft)
- ❌ **Incompatible**: Embed AGPL components in proprietary application

**Q: What if I want to fork the entire project with a different license?**

A: You can't relicense code you didn't write. However:
- You can fork AGPL components under AGPL (but must keep that license)
- You can fork Apache components under Apache (or compatible license)
- You cannot change AGPL → Apache or vice versa without permission

**Q: Can the Birthmark Foundation change the license later?**

A: For existing code, no - it remains under its current license. For future versions:
- The Foundation could release new versions under different licenses
- Contributors retain rights to their contributions under the original license
- This is why clear contribution agreements matter

---

## Getting Help

### Licensing Questions

If you have specific licensing questions:

1. Read this document carefully
2. Check the LICENSE file in the specific package you're using
3. Review the use case examples above
4. If still unclear, email: contact@birthmarkstandard.org

### Legal Review

We are not providing legal advice. For compliance questions specific to your situation:

- Consult with your legal team
- Seek advice from open source licensing attorneys
- Review the official license texts (not just this guide)

### Commercial Licensing

If you need licensing terms different from AGPL/Apache:

- Email: contact@birthmarkstandard.org
- We may be able to discuss alternative arrangements
- The Foundation's mission is public infrastructure, so alternatives will be evaluated against that goal

---

## Summary

The Birthmark Standard's dual licensing structure is designed to:

✅ **Protect public trust infrastructure** via AGPL for registry components
✅ **Enable commercial adoption** via Apache for implementations and tools
✅ **Maximize transparency** where it matters most (verification layer)
✅ **Minimize friction** for manufacturers and developers
✅ **Follow precedent** from successful infrastructure projects

When in doubt:
- **Building on the infrastructure?** → Query it via API, stay independent
- **Modifying registry components?** → AGPL requires publishing modifications
- **Building cameras or verification tools?** → Apache gives you freedom
- **Commercial use?** → Totally fine for all components, with AGPL source requirements

We believe this approach will help Birthmark become the standard for hardware-backed photo authentication while keeping the trust layer genuinely public infrastructure.

---

**Questions?** Contact us at contact@birthmarkstandard.org
**License texts**: See LICENSE files in each package directory
**Website**: https://birthmarkstandard.org
