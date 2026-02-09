---
title: "Governance"
url: "/governance.html"
---

    <section class="hero" style="padding: 3rem 0;">
        <div class="container">
            <h2>Media Registry Governance</h2>
            <p style="max-width: 800px; margin: 0 auto;">The Birthmark Media Registry is governed by a coalition of independent journalism, fact-checking, and press freedom organizations—not by a single company or government.</p>
        </div>
    </section>

    <section class="technical-section">
        <div class="container">
            <h2>Purpose and Core Principles</h2>

            <div class="content-block">
                <p>The Birthmark Media Registry provides a decentralized, tamper-evident ledger for recording image authentication data. The Registry stores cryptographic hashes of authenticated photographs along with associated metadata, enabling anyone to verify whether a photograph has been authenticated by a legitimate camera and when that authentication occurred.</p>

                <p style="margin-top: 1rem;"><strong>Core Principles:</strong> Independence (no single entity controls the Registry), Transparency (all operations and governance publicly documented), Neutrality (verifies technical authenticity, not editorial content), Permanence (immutable data accessible indefinitely), and Public Good (serves the public interest, not operated for profit).</p>
            </div>
        </div>
    </section>

    <section class="technical-section" style="background: var(--light-blue);">
        <div class="container">
            <h2>Coalition Membership</h2>

            <div class="content-block">
                <h3>Who Can Join</h3>
                <p>Coalition Membership is open to organizations that demonstrate commitment to information integrity: established nonprofits, educational institutions, news organizations, or professional associations with missions aligned with journalism, fact-checking, press freedom, archival preservation, or information integrity. Members must have technical capability to operate a validator node (or contract for managed services) and commit to maintaining 95% uptime.</p>

                <p style="margin-top: 1rem;"><strong>Conflict of Interest:</strong> Organizations whose primary mission is media production (news outlets, content creators, photography agencies) are ineligible due to inherent conflict of interest. Organizations that consume, analyze, or validate media (fact-checkers, press freedom advocates, academic institutions, archival organizations) are eligible.</p>

                <p style="margin-top: 1rem;"><strong>Target Members:</strong> National Press Photographers Association (NPPA), International Fact-Checking Network (IFCN/Poynter), Committee to Protect Journalists (CPJ), Bellingcat, academic journalism schools, and regional press freedom organizations.</p>
            </div>

            <div class="content-block">
                <h3>Node Ownership and Rights</h3>
                <p>Each Coalition Member purchases ownership of one or more validator node slots. Ownership includes validator authority (right to operate a node participating in consensus), governance rights (one vote per node), pre-configured node software with documentation and setup support, and Coalition representation.</p>

                <p style="margin-top: 1rem;"><strong>Ownership Limits:</strong> No single organization may own more than 2 nodes or 10% of total nodes (whichever is higher). Related organizations count as a single entity.</p>

                <p style="margin-top: 1rem;"><strong>Editorial Neutrality:</strong> Node ownership confers no editorial authority over authenticated content. The Registry verifies technical provenance, not content accuracy. Coalition Members shall not represent node operation as endorsement of specific authenticated images.</p>
            </div>

            <div class="content-block">
                <h3>Costs</h3>
                <p>The initial node ownership fee (set by the Foundation) is a one-time purchase funding Registry development and deployment. Ongoing operational costs (server hosting, bandwidth, maintenance) are each member's responsibility, estimated at $15-30/month for VPS hosting.</p>
            </div>
        </div>
    </section>

    <section class="technical-section">
        <div class="container">
            <h2>Governance Structure</h2>

            <div class="content-block">
                <h3>Development and Transition</h3>
                <p><strong>Phase 1 (Current):</strong> The Foundation builds and validates Registry infrastructure. Organizations may participate as Founding Advisors (providing input on technical specifications and governance) with no voting rights or purchase obligation. The Foundation Board retains full authority during this phase.</p>

                <p style="margin-top: 1rem;"><strong>Phase 2 (Production):</strong> Begins when Registry technology completes validation and 10 validator nodes are functionally operational. Node ownership becomes available for purchase by eligible organizations.</p>

                <p style="margin-top: 1rem;"><strong>Governance Transition:</strong> The Foundation retains voting authority until one year after the first node sale, then governance transitions to the full Coalition model.</p>
            </div>

            <div class="content-block">
                <h3>Coalition Voting and Decisions</h3>
                <p>Under full Coalition governance, each owned node receives one vote. A quorum (majority of purchased nodes, >50%) must participate for valid votes.</p>

                <p style="margin-top: 1rem;"><strong>Standard Decisions (Simple Majority >50%):</strong> Operational procedures, documentation updates, technical support policies, communication activities, and minor parameter adjustments.</p>

                <p style="margin-top: 1rem;"><strong>Major Decisions (Supermajority ≥67%):</strong> Charter amendments, protocol upgrades affecting consensus or data structure, admission or removal of Coalition Members, changes to ownership limits or voting structure, and integration with external systems.</p>

                <p style="margin-top: 1rem;"><strong>Emergency Decisions:</strong> The Foundation retains authority for time-critical security issues, subject to Coalition ratification within 30 days.</p>
            </div>
        </div>
    </section>

    <section class="technical-section" style="background: var(--light-blue);">
        <div class="container">
            <h2>Member Responsibilities</h2>

            <div class="content-block">
                <p><strong>Technical:</strong> Maintain minimum 95% uptime, install Coalition-approved software updates within specified timeframes, implement reasonable security measures, monitor node health and respond to issues promptly, and report technical problems or security concerns to the Coalition.</p>

                <p style="margin-top: 1rem;"><strong>Governance:</strong> Participate in votes (quorum requirement), designate a primary contact for Coalition communications, attend or send representative to quarterly Coalition meetings, and provide technical feedback on proposed protocol changes.</p>

                <p style="margin-top: 1rem;"><strong>Financial:</strong> Members are responsible for all operational costs (server hosting, bandwidth, electricity, technical staff time). The Registry charges no ongoing fees. Optional technical support and managed services are available from the Foundation under separate service agreements.</p>
            </div>
        </div>
    </section>

    <section class="technical-section">
        <div class="container">
            <h2>Node Failure and Member Removal</h2>

            <div class="content-block">
                <h3>Node Downtime</h3>
                <p>If a member's node experiences temporary downtime, the Network continues operating with remaining nodes. For extended absence (30+ consecutive days without communication), the Foundation may spin up a temporary replacement node. The member retains ownership but loses voting rights until node is restored, and the Coalition will work to recruit a replacement member to purchase the node slot.</p>
            </div>

            <div class="content-block">
                <h3>Grounds for Removal</h3>
                <p>Members may be removed for: sustained failure to maintain 95% uptime (90+ consecutive days), security breach from negligence or willful misconduct, actions compromising Registry integrity or neutrality, material charter breach uncured after 30-day notice, organizational mission change conflicting with Registry principles, or criminal conduct related to Registry operations.</p>
            </div>

            <div class="content-block">
                <h3>Removal Process</h3>
                <p>Written notice with 30-day cure period (if curable) → Formal removal proposal by any Coalition Member or Foundation → Accused member submits written response within 14 days → Supermajority vote (≥67%) required → Immediate loss of voting rights → 90-day transition to transfer node ownership or revert to Foundation → No refund of initial purchase fee.</p>

                <p style="margin-top: 1rem;"><strong>Independent Review:</strong> Removed members may request third-party review within 30 days at their expense. Voting rights are not restored during review. If review finds the removal process violated the charter, removal may be reversed by simple majority Coalition vote.</p>
            </div>

            <div class="content-block">
                <h3>Emergency Suspension</h3>
                <p>In cases of active security threats or ongoing malicious conduct, the Foundation may immediately suspend a member's voting rights and node participation. Emergency suspensions must be ratified by Coalition supermajority vote within 30 days or the suspension is automatically lifted.</p>
            </div>

            <div class="content-block">
                <h3>Legal Compulsion</h3>
                <div class="diagram-box" style="background: white;">
                    <p><strong>Critical Protection:</strong> If a Coalition Member is compelled by legal authority to take actions that violate this charter, that member shall be removed from the Network. This ensures governments cannot subvert the network through captured nodes—they can only remove individual nodes from a network designed to continue operating with remaining members.</p>
                </div>
            </div>
        </div>
    </section>

    <section class="technical-section" style="background: var(--light-blue);">
        <div class="container">
            <h2>Role of the Foundation</h2>

            <div class="content-block">
                <p>The Foundation serves as the <strong>administrative coordinator</strong> for the Registry, not its owner or controller. Responsibilities include initial node setup (one-time provisioning and transfer of configured node software), maintaining technical documentation, facilitating Coalition meetings and communications, maintaining the open source code repository, acting as first responder for critical security issues (subject to Coalition ratification), and offering technical training to member IT staff.</p>

                <p style="margin-top: 1rem;"><strong>Technical Support:</strong> The Foundation does not provide indefinite support as part of node ownership. Members may choose optional paid service contracts for ongoing maintenance or receive training for self-managed operation.</p>

                <p style="margin-top: 1rem;">The Foundation does not control the Registry's data, cannot unilaterally modify the blockchain, and cannot override Coalition governance except in documented emergency procedures.</p>
            </div>

            <div class="content-block">
                <h3>Foundation Node Reserve</h3>
                <p>The Foundation may operate up to 10 validator nodes for Network resilience. These nodes carry no voting rights, serve primarily as backup capacity, may be transitioned to new Coalition Members as they join, and incur operational costs borne by the Foundation. The Foundation's goal is zero ownership, with member-operated nodes preferred.</p>
            </div>

            <div class="content-block">
                <h3>Sustainability</h3>
                <p>The Foundation sustains operations through node sales, optional service contracts, technical training services, and grant funding. The Foundation maintains minimum 12-month operating reserves. If unable to sustain operations, the Foundation shall execute orderly transition: transferring administrative functions to the Coalition, ensuring documentation and code repositories remain accessible, and providing 6-month advance notice. The Registry is designed to operate independently of the Foundation's continued existence.</p>
            </div>
        </div>
    </section>

    <section class="technical-section">
        <div class="container">
            <h2>Registry Continuity</h2>

            <div class="content-block">
                <p>The Registry is designed to operate independently of any single organization, including the Foundation. If the Foundation ceases operations, all node software and documentation remains open source and publicly available, Coalition Members retain full ownership and operational control of their nodes, the blockchain continues operating with minimum node count (3), Coalition governance structure remains in effect, and the Coalition may transfer administrative functions to another organization.</p>
            </div>
        </div>
    </section>

    <section class="technical-section" style="background: var(--light-blue);">
        <div class="container">
            <h2>Additional Governance Provisions</h2>

            <div class="content-block">
                <h3>Dispute Resolution</h3>
                <p>Disputes between Coalition Members, or between Members and the Foundation, follow this process: Direct negotiation (30 days from written notice) → Mediation with mutually agreed neutral mediator (within 60 days) → Binding arbitration under American Arbitration Association rules. Mediation and arbitration costs are shared equally unless the arbitrator determines otherwise. This process does not apply to emergency security decisions, which are subject to Coalition ratification as specified.</p>
            </div>

            <div class="content-block">
                <h3>Charter Amendments</h3>
                <p>Any Coalition Member may propose charter amendments in writing. Amendments require a minimum 30-day review period for Coalition discussion, supermajority (≥67%) approval, 30-day notice before taking effect, and documentation with version history.</p>
            </div>

            <div class="content-block">
                <h3>Whistleblower Protection</h3>
                <p>The Foundation Board shall establish whistleblower protection procedures within 12 months of Phase 2 commencement, ensuring Coalition Members and Foundation staff have protected channels for reporting charter violations or misconduct.</p>
            </div>

            <div class="content-block">
                <h3>Open Source Licensing</h3>
                <p>All Registry software (node operation code, documentation, and supporting tools) is released under Apache License 2.0, permitting free use, modification, and distribution while providing patent protection. Coalition Members and external developers may fork the codebase, though the Foundation maintains control of the official repository and project direction.</p>
            </div>
        </div>
    </section>
