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

## Open Questions / To Be Determined

### 1. Substrate Pallet Design
**Question:** What custom pallets do we need for Birthmark?
- Pallet for image hash storage?
- Pallet for MA validation tracking?
- Pallet for provenance chains?
- Integration with Substrate's existing pallets (balances, timestamp, etc.)

**Action:** Design pallet architecture before development starts

---

### 2. API Key Management System
**Question:** How to implement API key issuance, tracking, and revocation?
- Database for API keys (separate from blockchain)?
- How to sync API keys across all 3 nodes?
- Web dashboard for Foundation to manage keys?
- Self-service portal for manufacturers to request keys?

**Action:** Design API key management workflow

---

### 3. Rate Limiting Values
**Question:** What are the actual rate limits per API key?
**Status:** Marked as TBD - need real usage data

**Proposed Framework:**
- Camera manufacturers: 1000 submissions/day
- Mobile app (Foundation): 500 submissions/day per device
- Verification queries: 10,000/hour (public, read-only)

**Action:** Implement conservative limits, monitor Phase 2 usage, adjust

---

### 4. Stress Testing Criteria
**Question:** What defines "passing" stress test for first node?
- Submissions per second target?
- Concurrent connections?
- Database size limits?
- Uptime requirements?

**Action:** Define stress testing plan with success metrics

---

### 5. Cloud Provider Selection
**Question:** Which cloud provider(s) for Phase 2 nodes?
- AWS (most features, higher cost)
- DigitalOcean (simpler, lower cost, good for startups)
- GCP (middle ground)
- Hetzner (EU-friendly, cost-effective)

**Considerations:**
- Cost per node per month
- Global availability (for Phase 3 geographic distribution)
- Docker/container support
- Monitoring integrations

**Action:** Evaluate cost and features, select provider

---

### 6. Phase 2 Timeline & Milestones
**Question:** When to launch each phase?
- Phase 2.0: Single node stress testing
- Phase 2.1: 3-node deployment
- Phase 2.2: Production hardening

**Depends on:**
- Funding availability
- Android app development timeline
- Substrate development resources

**Action:** Create project timeline with milestones

---

### 7. Foundation MA Scope
**Question:** What devices will Foundation MA provision?
- ✅ Android app (confirmed)
- iOS app (future, Phase 3?)
- Reference implementations for manufacturers?
- Third-party certification service?

**Action:** Define Foundation MA service scope

---

### 8. Android App Development Status
**Question:** What is the current state of Android app development?
- Design complete?
- Development started?
- Integration with MA ready?
- Timeline to beta/production?

**Action:** Sync with Android app development team (if exists) or plan development

---

### 9. MA Provisioning Workflow
**Question:** How does Foundation MA provision Android devices?
- Bulk provisioning during app download?
- Per-device unique credentials?
- How to handle key rotation?
- Backup/recovery for lost devices?

**Action:** Design Android app provisioning workflow

---

### 10. Cost Budget per Node
**Question:** What is acceptable monthly cost per validator node?
- VPS sizing (CPU, RAM, storage)?
- Bandwidth limits?
- Monitoring costs?
- Total budget: $50/month? $100/month? $200/month?

**Action:** Define budget constraints for cloud hosting

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
