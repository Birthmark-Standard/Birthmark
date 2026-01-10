# Phase 2 BMR Production Deployment - Planning Document

**Status:** Planning in Progress
**Date:** January 10, 2026
**Goal:** Transition from local Phase 1 prototype to production multi-node deployment

---

## Key Decisions Made

### 1. Terminology Change: SMA → MA (Manufacturer Authority)

**Phase 1:** SMA (Simulated Manufacturer Authority)
**Phase 2:** MA (Manufacturer Authority)

**Rationale:**
- The Birthmark Standard Foundation is developing the Android App
- We ARE the actual manufacturer/developer
- Documentation should reflect this reality, not simulation

**Impact:**
- Update all documentation: `packages/sma/` → refers to real MA
- Android app provisions with Birthmark Standard MA keys
- Foundation operates MA for our own apps
- Third-party camera manufacturers operate their own MAs

---

## 2. Multi-Node Blockchain Deployment

### Initial Phase 2 Launch: 3 Validator Nodes

**Target after stress testing first node:**
1. Node 1: Primary (stress test, then production)
2. Node 2: Secondary validator
3. Node 3: Tertiary validator

**Node Discovery: Passive DNS Server**
- Host: `submission.birthmarkstandard.org`
- Function: Acts as passive DNS server returning validator node addresses
- Format: Returns list of active validator endpoints

**Example DNS Response:**
```json
{
  "validator_nodes": [
    {
      "id": "node_1",
      "url": "https://birthmark.nppa.org",
      "status": "active"
    },
    {
      "id": "node_2",
      "url": "https://birthmark.bellingcat.com",
      "status": "active"
    },
    {
      "id": "node_3",
      "url": "https://birthmark.cpj.org",
      "status": "active"
    }
  ]
}
```

---

## 3. Authentication Model

### ✅ Selected: Option A - API Keys for Device Manufacturers

**Approach:**
- Camera/app manufacturers receive API keys from Foundation
- Keeps Foundation decoupled from manufacturing process
- Relationship only involves constant communication if we operate their MA server
- Self-service model for third parties

**Implementation:**
```python
# Camera submission includes API key
POST /api/v1/submit
Headers:
  Authorization: Bearer <manufacturer_api_key>
  X-Manufacturer-ID: birthmark_standard_android
  X-Device-Serial: ANDROID_DEVICE_001
```

**API Key Management:**
- Foundation issues keys to verified manufacturers
- Rate limits per API key (not per IP)
- Revocation capability for compromised keys
- Separate keys for development vs production

**Third-Party Manufacturers:**
- Apply for API key from Foundation
- Operate their own MA (or Foundation operates for fee)
- Submit to any validator node in network
- Keys tracked across all nodes via blockchain consensus

---

## 4. Domain & Network Architecture

### ✅ Domain Structure: Institution-Branded Subdomains

**Format:** `https://birthmark.<institution>.org`

**Preferred over:** `https://<institution>.birthmark.org`

**Reasoning:** Cleaner, institution controls their own domain

**Example Validator Nodes:**
- `https://birthmark.nppa.org` (National Press Photographers Association)
- `https://birthmark.bellingcat.com` (Bellingcat)
- `https://birthmark.cpj.org` (Committee to Protect Journalists)
- `https://birthmark.witness.org` (WITNESS)
- `https://birthmark.ifcn.org` (International Fact-Checking Network)

**Central Services (Foundation-operated):**
- `submission.birthmarkstandard.org` - Node discovery DNS
- `docs.birthmarkstandard.org` - Documentation
- `verify.birthmarkstandard.org` - Public verification interface

---

## 5. Security: HTTPS Everywhere

### ✅ Decision: HTTPS Only (No HTTP)

**Implementation:**
- All API endpoints require HTTPS
- No HTTP fallback
- Redirect HTTP → HTTPS at reverse proxy level
- HSTS headers enforced

**Consequences:**

**Positive:**
- End-to-end encryption for all submissions
- Protects image hashes in transit
- Prevents MITM attacks
- Industry standard for APIs

**Challenges:**
- Certificate management for all nodes
- Initial setup complexity (Let's Encrypt automation)
- Testing environment needs certs (self-signed OK for dev)
- Mobile apps must handle cert pinning (optional security layer)

**Certificate Strategy:**
- Let's Encrypt for automatic renewal
- 90-day cert lifecycle (auto-renewed at 60 days)
- Wildcard certs NOT recommended (per-subdomain certs safer)

**Development Environment:**
```bash
# Local development uses self-signed certs
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout localhost.key -out localhost.crt \
  -days 365 -subj "/CN=localhost"
```

**Production Deployment:**
```bash
# Automated Let's Encrypt with certbot
certbot certonly --webroot -w /var/www/html \
  -d birthmark.nppa.org --email admin@nppa.org
```

---

## 6. Rate Limiting

### ✅ Decision: To Be Determined (TBD)

**Factors to Consider:**
- Camera submissions: Rare (photographers take 10s-100s photos/day)
- Mobile app submissions: Moderate (casual users, few per day)
- Software editor submissions: High (batch processing workflows)
- Verification queries: Very high (public, read-only)

**Initial Proposal (to be validated):**
```python
# Per API key rate limits
RATE_LIMITS = {
    "camera": "1000/day",      # Cameras submit frequently during shoots
    "mobile_app": "500/day",    # Mobile users submit occasionally
    "software": "100/hour",     # Software editors batch process
    "verification": "10000/hour"  # Public verification queries
}
```

**Testing Plan:**
- Phase 2.0: Monitor actual usage patterns
- Phase 2.1: Set limits based on real data
- Phase 2.2: Implement dynamic rate limiting

---

## 7. DDoS Protection

### ✅ Decision: CloudFlare if Necessary, But Not Fully Reliant

**Concerns:**
- Recent CloudFlare outages demonstrate single-point-of-failure risk
- Full reliance creates centralization vulnerability
- Contradicts decentralized trust model

**Hybrid Approach:**

**Primary Protection (Self-Hosted):**
```nginx
# nginx rate limiting
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req zone=api burst=20 nodelay;

# Connection limits
limit_conn_zone $binary_remote_addr zone=addr:10m;
limit_conn addr 10;
```

**Backup Protection (CloudFlare):**
- Enable CloudFlare during active DDoS attacks
- DNS failover to CloudFlare-fronted endpoints
- Maintain ability to serve directly without CloudFlare

**Architecture:**
```
Normal Operation:
  User → Validator Node (direct)

Under Attack:
  User → CloudFlare → Validator Node
```

**Implementation:**
- Dual DNS records: direct + CloudFlare-proxied
- Automatic failover based on traffic patterns
- Manual override capability

---

## Open Questions / To Be Determined

### 1. Blockchain Implementation Clarification
**Question:** Is Phase 1 blockchain Substrate or Python + PostgreSQL?
- `packages/registry/` suggests Substrate
- `packages/blockchain/` uses PostgreSQL
- **Need to confirm actual implementation**

### 2. Consensus Mechanism
**Depends on:** Blockchain implementation answer
- If Substrate: Use built-in GRANDPA finality
- If Python: Build custom PoA consensus protocol

### 3. Node Deployment Timeline
- When to launch first production node?
- Stress testing duration/criteria?
- Onboarding timeline for institutions?

### 4. Foundation MA Scope
**For Birthmark Standard Foundation MA:**
- Android app (definite)
- iOS app (future)
- Reference camera implementation (Raspberry Pi)?
- Third-party app certification service?

### 5. Cost Model
- Free for all (Foundation-funded)?
- Tiered pricing for commercial manufacturers?
- Coalition members contribute infrastructure?

---

## Next Steps

### Immediate (Before Phase 2 Development):
1. ✅ **Clarify blockchain implementation** (Substrate vs Python)
2. [ ] Validate stress testing requirements for first node
3. [ ] Define success criteria for 3-node deployment
4. [ ] Document MA provisioning workflow for Android app

### Phase 2.0 (First Production Node):
1. [ ] SSL/TLS certificate automation (Let's Encrypt)
2. [ ] API key management system
3. [ ] Rate limiting implementation (initial conservative limits)
4. [ ] Monitoring and alerting setup
5. [ ] Single-node production deployment

### Phase 2.1 (Multi-Node Deployment):
1. [ ] Consensus protocol implementation (PoA)
2. [ ] Node discovery service at `submission.birthmarkstandard.org`
3. [ ] P2P networking between validators
4. [ ] Geographic distribution (3 nodes)

### Phase 2.2 (Production Hardening):
1. [ ] CloudFlare integration (backup DDoS protection)
2. [ ] Rate limit tuning based on real usage
3. [ ] Automated failover testing
4. [ ] Third-party MA onboarding process

---

## Documentation Updates Needed

**When Phase 2 Begins:**
1. Rename `packages/sma/` → `packages/ma/` (or update all docs)
2. Update CLAUDE.md with Phase 2 architecture
3. Create PHASE_2_DEPLOYMENT_GUIDE.md
4. Update API documentation with authentication requirements
5. Create MA_OPERATIONS_GUIDE.md for Foundation staff

---

**Next Session:** User will provide notes for first 3 sections (interrupted)

**Awaiting Clarification:**
- Blockchain implementation (Substrate vs Python + PostgreSQL)
- User's notes on sections 1-3
