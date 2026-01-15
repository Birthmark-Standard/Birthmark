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

---

## ✅ ADDITIONAL DECISIONS (January 10, 2026)

### 4. Blockchain Implementation: Substrate

**Decision:** Use Substrate for Phase 2 blockchain
- Leverage Substrate's built-in GRANDPA finality for consensus
- Rust-based, production-grade blockchain framework
- Custom pallets for Birthmark-specific logic
- P2P networking built-in

**Migration from Phase 1:**
- Phase 1 used Python + PostgreSQL (custom implementation)
- Phase 2 migrates to Substrate (no backward compatibility needed)
- Phase 1 Raspberry Pi camera being returned - no legacy support required

**Technical Stack:**
- Runtime: Substrate FRAME
- Consensus: GRANDPA + BABE (or Aura for simpler PoA)
- Database: RocksDB (Substrate default) per node
- Network: libp2p (Substrate built-in)

---

### 5. Database Strategy: Local DB per Node (Option C)

**Decision:** Each institution runs their own database
- No centralized/managed database service
- Blockchain consensus ensures data consistency across nodes
- Substrate's RocksDB handles blockchain state per node
- No single point of failure

**Benefits:**
- Aligns with decentralized trust model
- Each institution owns their data
- No vendor lock-in
- Reduced operational costs (no managed DB fees)

---

### 6. Deployment Infrastructure: Docker Compose

**Decision:** Start with Docker Compose for Phase 2
- Simple deployment for institutions
- User wants to learn and build expertise (hands-on approach)
- Can evolve to Kubernetes in Phase 3 if needed

**Deployment Package:**
```yaml
# docker-compose.yml for Birthmark Node
services:
  substrate-node:
    image: birthmark/substrate-node:latest
    ports:
      - "443:9933"   # RPC (HTTPS)
      - "30333:30333"  # P2P networking
    volumes:
      - ./chain-data:/chain-data
    environment:
      - NODE_NAME=institution_node_01
      - VALIDATOR=true
```

**Institution Setup:**
1. Receive Docker Compose file from Foundation
2. Configure environment variables (node name, keys)
3. Run `docker-compose up -d`
4. Monitor via Prometheus/Grafana dashboard

---

### 7. Monitoring: Self-Hosted Prometheus + Grafana (Option A)

**Decision:** Avoid managed services, build internal expertise
- Prometheus for metrics collection
- Grafana for visualization dashboards
- Self-hosted on each validator node or centralized Foundation monitoring

**Rationale:**
- Hands-on learning builds expertise
- No vendor lock-in or recurring service fees
- Full control over metrics and alerting
- Open-source, battle-tested stack

**Metrics to Track:**
- Substrate-specific: Block height, finalized blocks, peer count
- API: Request rate, error rate, latency
- System: CPU, memory, disk I/O, network
- MA validation: PASS/FAIL rates, response times

---

### 8. Node Discovery: Passive Table at submission.birthmarkstandard.org

**Decision:** Static table serving node registry
- Foundation-hosted service at `submission.birthmarkstandard.org`
- Returns list of validator nodes with metadata
- Cameras/phones query this table to find submission endpoints
- Nodes query to discover peers for P2P networking

**Table Schema:**
```json
{
  "updated_at": "2026-01-10T12:00:00Z",
  "validator_nodes": [
    {
      "id": "node_1",
      "url": "https://birthmark.nppa.org",
      "location": "US-East",
      "capacity": "high",
      "status": "active",
      "p2p_address": "/ip4/1.2.3.4/tcp/30333/p2p/12D3..."
    }
  ]
}
```

**Usage:**
- Cameras: Query for nearest node based on location
- Nodes: Query for peer list during startup
- Foundation: Manual updates when nodes added/removed

---

### 9. Geographic Distribution: Not Required for Phase 2

**Decision:** Focus on multi-node consensus, not geographic diversity
- Goal: Prove 3 nodes can reach consensus
- All nodes can be in same cloud region for Phase 2
- Geographic distribution deferred to Phase 3 (when selling nodes to institutions)

**Phase 2 Testing Goal:**
- Validate Substrate multi-node consensus works
- Test node communication and sync
- Prove fault tolerance (1 node can go down, 2 continue)

---

### 10. Phase 1 Compatibility: None Required

**Decision:** No backward compatibility with Phase 1
- Phase 1 Raspberry Pi camera being returned after testing
- No need to support Phase 1 API endpoints
- Clean migration: Phase 2 is fresh start
- Substrate blockchain replaces Python + PostgreSQL

**Impact:**
- Can redesign APIs without legacy constraints
- Simplifies codebase (no v1/v2 dual support)
- Documentation focuses only on Phase 2 architecture

---

### 11. Cloud Hosting: All Nodes Cloud-Hosted

**Decision:** Minimize load on node owners by using cloud infrastructure
- All 3 Phase 2 validator nodes hosted in cloud (AWS, GCP, DigitalOcean, etc.)
- Foundation manages hosting for initial deployment
- Institutions may self-host in Phase 3 if desired

**Benefits:**
- Reliable uptime (cloud SLAs)
- Easy scaling and monitoring
- Foundation maintains control during Phase 2 testing
- Lower barrier to entry for institutions

---

## ✅ ADDITIONAL ANSWERS (January 10, 2026 - Session 2)

### 1. Substrate Pallet Design
**Answer:** Refer to record size reduction conversation
- See `docs/OPTIMIZATION_RESULTS.md` for 69% storage reduction analysis
- Binary encoding reduces record from 450 bytes → 140 bytes
- Pallet design should implement this optimized storage format

**CRITICAL SECURITY IMPROVEMENT:** Remove MA/DA ID from blockchain records
- See `docs/SECURITY_IMPROVEMENT_MA_ID_REMOVAL.md` for complete analysis
- `authority_id` MUST NOT be stored on blockchain (security/privacy risk)
- Keep `authority_id` in certificate for routing, discard after validation
- Store in private node audit logs only (not blockchain state)
- Rationale: Reduces attack surface, improves privacy, maintains auditability

**Next Action:** Design pallet schema based on optimized record format WITHOUT authority_id

---

### 2. API Key Management System
**Answer:** Self-service portal is a Phase 3 goal
- Phase 2: Manual API key issuance by Foundation staff
- Phase 3: Self-service portal for manufacturers to request keys
- Keeps Phase 2 scope focused on core blockchain functionality

**Next Action:** Design simple manual key issuance workflow for Phase 2

---

### 3. Stress Testing Criteria
**Answer:** Develop criteria as we develop the node code
- Don't set pass conditions before building
- Set pass conditions before testing (after implementation)
- Iterative approach: build → define metrics → test → adjust

**Next Action:** Define stress testing criteria during Phase 2.0 development

---

### 4. Cloud Provider Selection
**Answer:** Insufficient knowledge to choose yet
- May resort to local hosting if funding isn't sufficient
- Decision deferred pending cost analysis (see question #5 below)

**Next Action:** Evaluate specs/costs, then decide provider OR local hosting

---

### 6. Phase 2 Timeline & Milestones
**Answer:** Depends on funding availability
- Timeline blocked until funding secured
- Cannot commit to specific dates without budget clarity

**Next Action:** Secure funding, then create timeline

---

### 7. Foundation MA Scope
**Answer:** Android MA will be distinct entity
- Separate from any other app MAs developed by Foundation
- May cohost on same server, but architecturally separate
- User suspects mixing different app MAs won't be simple
- Each app has its own MA instance

**Implementation:** One MA instance per app, even if same server

---

### 8. Android App Development Status
**Answer:** Not started
- No design, no development
- Fresh start for Phase 2

**Next Action:** Begin Android app design and development planning

---

### 9. MA Provisioning Workflow
**Answer:** Provision during install (first launch)
- User needs to determine method for generating sufficiently random hash for validation
- Likely: Device-specific entropy + server-side randomness

**Technical Challenge:** Ensure sufficient randomness for secure device provisioning

---

### 10. Rate Limiting - Time Scale
**Answer:** Rate limits should be on performance-useful time scales
- Use per-minute or per-hour (not just per-day)
- Total per-day should be higher to account for usage spikes
- Example: 100/hour (allows spikes) vs 2400/day (too rigid)

**Implementation:**
```python
# Better rate limiting approach
RATE_LIMITS = {
    "camera": "50/minute, 1000/day",      # Spike-friendly
    "mobile_app": "20/minute, 500/day",
    "verification": "500/minute, 10000/hour"
}
```

---

## Open Questions / To Be Determined

### 5. Cloud Provider Selection - Specs & Cost Analysis

**Question:** What specs will we need? What are the real tradeoffs?

**Substrate Node Resource Requirements:**

Based on Substrate's typical resource needs for a validator node:

**Minimum Specs (Development/Testing):**
- CPU: 2 cores
- RAM: 4GB
- Storage: 50GB SSD
- Bandwidth: 100GB/month
- **Estimated Cost:** $12-24/month

**Recommended Specs (Production):**
- CPU: 4 cores
- RAM: 8GB
- Storage: 100GB SSD (room for blockchain growth)
- Bandwidth: 1TB/month
- **Estimated Cost:** $40-80/month

**High-Performance Specs (Future Scale):**
- CPU: 8 cores
- RAM: 16GB
- Storage: 200GB SSD
- Bandwidth: 5TB/month
- **Estimated Cost:** $160-240/month

**Provider Comparison (Production Specs: 4 CPU, 8GB RAM, 100GB SSD):**

| Provider | Monthly Cost | Pros | Cons |
|----------|-------------|------|------|
| **DigitalOcean** | $48/month | Simple UI, good docs, startup-friendly | Limited geographic regions |
| **Hetzner** | $35/month | Cheapest, EU-friendly, great price/performance | Limited to EU + US, less "enterprise" |
| **Vultr** | $48/month | Good global coverage, competitive pricing | Less popular than AWS/DO |
| **AWS (Lightsail)** | $40/month | AWS ecosystem, easy upgrade path | More complex, can get expensive |
| **AWS (EC2)** | $60-80/month | Most features, global, enterprise-grade | Most expensive, complex pricing |
| **GCP** | $55/month | Google infrastructure, global | Complex pricing, overkill for Phase 2 |
| **Self-Hosted** | $50-70/month | Full control, no vendor lock-in | Requires maintenance, no SLA, uptime risk |

**Key Tradeoffs:**

1. **Cost vs Features:**
   - Cheapest: Hetzner ($35/mo) - Great if EU OK
   - Best value: DigitalOcean ($48/mo) - Simplicity + reliability
   - Most features: AWS EC2 ($60-80/mo) - Future-proof, complex

2. **Simplicity vs Control:**
   - Simplest: DigitalOcean (straightforward pricing/UI)
   - Most control: AWS (every feature imaginable, but complexity)
   - Middle ground: Hetzner or Vultr

3. **Phase 2 vs Phase 3:**
   - Phase 2: Can use cheaper options (single region, 3 nodes)
   - Phase 3: May need global providers (AWS, GCP) for geographic distribution

**Recommendation for Phase 2:**
- **If budget constrained:** Hetzner ($35/mo × 3 nodes = $105/mo total)
- **If learning focus:** DigitalOcean ($48/mo × 3 nodes = $144/mo total)
- **If planning Phase 3 scale:** AWS Lightsail ($40/mo × 3 nodes = $120/mo total)

**Local Hosting Alternative:**
- Buy 3× used servers (~$300-600 upfront)
- Internet: $50/mo, Power: $20/mo → ~$70/mo ongoing
- **Total first year:** $600 hardware + $840 hosting = $1,440
- **Cloud equivalent (DO):** $144/mo × 12 = $1,728
- **Breakeven:** ~10 months

**Next Decision:** What's your budget constraint? <$100/mo? <$200/mo? Or self-host?

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
