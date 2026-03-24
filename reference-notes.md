# Reference Notes for DAWO26 Paper

Digested summaries of key references. For full texts see URLs in CLAUDE.md.

---

## Ford 2020 — "Identity and Personhood in Digital Democracy"

**Core distinction**: Identity (attributes that divide people) vs. personhood (inalienable right to participate equally). Digital democracy needs personhood, not identity.

**Four evaluation criteria**: Inclusive, Equal, Secure, Private. Pseudonym parties are the only approach scoring well on all four. Government ID fails privacy/inclusion. Biometrics fail privacy (centralized DB of "passwords you can't change"). Social trust networks cannot verify *absence* of alter egos. Proof-of-investment (PoW/PoS) fails equality.

**Critique of Encointer** (Section 4.7, pp. 22-24): Small-group assignment enables progressive Sybil accumulation. An attacker hires gig workers as "elastic minions." Ford assumes 4-member groups and calculates ~0.01% of groups fully attacker-controlled per cycle at 10% initial control.

**IMPORTANT: Ford misrepresents Encointer's design.** He assumes group size 4 (pairs/small groups). Encointer's actual target gathering size is **~15 participants** (spec allows 3-12, current implementation targets ~15). The Hoffmann 2021 security study (supervised by Ford himself, see below) corrects this with proper quantitative analysis. At group size 12-15, the control threshold is 7-10 sybil reputables per meetup — vastly harder than Ford's 4-member scenario suggests.

**Key for our paper**: Cite Hoffmann (not Ford) for quantitative security analysis. Acknowledge Ford's conceptual framework (identity vs. personhood, four criteria) but note the misrepresentation of group size. Present empirical evidence from deployments.

---

## Ohlhaver et al. 2024 — "The Silent Strings of Proof of Personhood"

**NOT a survey paper** — a deep empirical case study of **Idena** (Aug 2019 – May 2022).

**Key finding**: Idena achieved *de jure* Sybil resistance (filtering bots from humans) but failed at *de facto* Sybil resistance (filtering humans acting as bots for others). By May 2022, **23 entities (<0.6%) controlled ~40% of accounts and ~48% of rewards**. Operators paid $2-$14/session for participants' keys.

**Puppeteering taxonomy**: Strong puppets (unaware of keys), semi-strong puppets (know keys but not significance), cooperation (voluntary delegation with accountability). Spectrum, not binary. On-chain patterns identical — difference is off-chain social reality.

**Crucial governance lesson**: One-pool-one-vote (discounted influence for pooled accounts) saved Idena. Solo accounts were ~27% of accounts but controlled ~89% of voting power, enabling protocol pivot. Directly relevant to Encointer's participation-weighted voting.

**Theoretical contribution**: De facto Sybil resistance and collusion resistance are "mirror challenges" — neither solvable independently. Remedy: plural attention mechanisms (bridging bonuses, anti-correlation), social identity with subsidiarity. A single global identity game has inevitable economies of scale toward oligopoly; a *plurality* of games enables normal distribution of power.

**Key for our paper**: Community-level identity has a natural advantage (subsidiarity, local social ties) — aligns with Ohlhaver's prescription. Encointer's per-community structure is inherently plural. The puppeteering risk at $2/session is real — must be discussed honestly.

---

## Buterin 2023 — "What do I think about biometric proof of personhood?"

**Taxonomy**: Social-graph-based (Proof of Humanity, BrightID, Idena, Circles) vs. biometric (general-hardware like video, specialized-hardware like Worldcoin Orb). Best path is hybrid.

**Key tradeoffs**: Privacy vs. security, decentralization vs. security, accessibility vs. security. "Cypherpunks stuck in a bind."

**On Worldcoin**: Praises ZK-SNARK privacy layer, iris hashing. Criticizes hardware centralization (one malicious Orb manufacturer = unlimited fake IDs), accessibility (few hundred Orbs globally), government coercion risk, ID selling already happening.

**On ceremony-based**: Sees social-graph/ceremony systems as long-term robust but currently bootstrap-limited. Recommends biometric bootstrapping short-term, social-graph taking over long-term.

**Conclusion**: No ideal PoP exists. Three paradigms are complementary. "A world without proof-of-personhood seems more likely to be dominated by centralized identity solutions, money, small closed communities, or some combination."

**Key for our paper**: Buterin's endorsement of ceremony-based approaches as long-term robust supports our architecture. His "hybrid" recommendation contextualizes Encointer's position. Cite his observation that low-wage labor attacks are currently the dominant real-world attack vector.

---

## Ruddick 2025 — "Grassroots Economics: Reflection and Practice"

**Evolution**: From community currencies (tokens as money) toward **commitment pools** (curated, valued, limited, exchangeable agreements). Inspired by Mweria (Mijikenda/Kamba rotating labor associations).

**Pool protocol**: Four functions — curation (what's allowed), valuation (relative pricing), limitation (caps per commitment type), exchange (swap rules). Multiple overlapping pools form polycentric network.

**The accumulation problem**: Addressed structurally via hard limits per participant ($400-$500 caps), multiple overlapping pools (route around stagnation), demurrage/expiration, periodic Jubilee rebalancing, and the "cancerous pumpkin" metaphor (no entity should force all nutrients through itself).

**Governance**: Dhome tradition (fireside deliberation), rotating elder councils, community circles for conflict resolution, 75% agreement threshold for changes. Digital: multi-sig wallets, smart contract stewardship, pool transaction fees fund default protection.

**Field experience**: 100+ communities across Kenya. Emma Onyango case study: started with 6 members, grew to 25+, paper-to-digital transition. Sarafu Network on Celo blockchain. Also Uganda refugee camps. 2012 arrest set legal precedent for community currencies in Kenya.

**Key for our paper**: Ruddick documents the *why* behind treasury swap governance — popular businesses accumulating excess tokens is a known problem. His structural solutions (caps, pools, demurrage) parallel Encointer's per-beneficiary limits and exercise fees. Cite for community currency sustainability challenges and governance traditions.

---

## Schneider 2024 — "Governable Spaces: Democratic Design for Online Life"

**Core argument**: "Implicit feudalism" — online spaces default to autocratic admin control, atrophying democratic skills. The internet needs democratic governance by design.

**DAO critique — three problems**:
1. **Personhood problem**: No reliable human ID forces default to token-based voting.
2. **Persistent plutocracy**: One-token-one-vote = wealth determines power. Even Buterin admits "plutocracy is still bad."
3. **Invisible externalities**: On-chain systems ignore non-tokenizable costs.

**Key insight**: "Markets are downstream from politics" (Polanyi). When governance becomes purely economic, politics disappears and plutocratic feedback loops are inevitable. Self-sacrifice, duty, honor are "bedrock features of most political organizations, but difficult to simulate with cryptoeconomic incentive design."

**Alternatives**: Quadratic voting, soulbound tokens, vote delegation, reputation systems, citizen assemblies, cooperative models (one-member-one-vote). Modular politics — governance modules mixed and matched per context. Exit to Community (E2C).

**Buterin exchange**: Buterin largely agrees on plutocracy critique, reframes around collusion prevention. Identity-based governance is cryptographically necessary for stability.

**Key for our paper**: Schneider provides the theoretical framing for *why* plutocratic DAO governance is problematic. His "personhood problem" is exactly what Encointer's PoP solves. Cite for the democratic legitimacy argument and the cooperative governance tradition. His "modular politics" concept maps to Encointer's per-community governance customization.

---

## Brenzikofer 2019 — Encointer Paper (arxiv:1912.12141)

**Ceremony mechanism**: Pseudonym key-signing parties every 10 days at "high sun" worldwide. Registration → Assignment (randomized, NP-hard optimization) → Meetup (vote on attendance count, pairwise attestation) → Witnessing (on-chain submission).

**Assignment rules**: Minimize repeat encounters, maximize group size (3-12), max 1/4 newcomers per meetup, randomize locations.

**Currency model**: UBI reward per ceremony. Demurrage at 7%/month (compound) creates equilibrium money supply. Anti-Cantillon: money created "at the bottom." Many local currencies, not one global token.

**Reputation**: Rolling window (5 ceremonies on mainnet). Statuses: Newbie → Reputable → Bootstrapper. Reputation gates assignment guarantees and voting eligibility.

**Governance (current)**: One-person-one-vote based on ceremony reputation. Adaptive quorum biasing: `threshold = 1/(1 + sqrt(turnout))`. Open proposal submission, parallel competing proposals, participation-weighted voting (capped 4x), one-cycle reputation delay. Global actions need all-community quorum; community actions are local.

**Treasury**: Deterministic accounts (no private key holder). Funded by transfers. Spending requires democratic approval. Swap options with per-beneficiary limits and exercise fees.

**Tanzania deployment**: Nyota currency in Dar es Salaam (Sep 2023). 5 Nyota per ceremony (~2 USD). 100+ participants, 60 entrepreneurs, 7 business groups. Integrated with Mchezo (rotating savings circles). 15 new ventures from first lending round. Also exploring Zaria, Nigeria.

**Architecture**: Kusama common-good parachain. TEE-validated sidechains for privacy. Reputation rings via ring-VRF on Bandersnatch curve for anonymous PoP.

---

## Hoffmann 2021 — "Security Analysis of Proof-of-Personhood: Encointer"

**EPFL Master project, supervised by Bryan Ford. 16 pages.**
URL: https://encointer.org/wp-content/uploads/2022/04/report-2021-1-hoffmann_21_pop_security_encointer.pdf

**Attack model**: Two types — Sybil (validate >1 UPoP token) and Sabotage (prevent honest participants from validating). Adversary hires "minions" to attend ceremonies, then exploits random assignment to land enough sybils in one meetup to control it.

**Control threshold**: Adversary needs **(reputables_in_meetup - 2)** sybil reputables to control a meetup. At meetup size 12: needs 7 of 9 reputables. At target size 15: needs ~10 of ~11-12 reputables. Per-meetup probability modeled via hypergeometric distribution with exponential tail bound.

**Key quantitative findings**:
- Below ~50% sybil fraction: probability of controlling any meetup is negligible, profit is zero or negative.
- The sybil-fraction-to-profit relationship is **exponential, not linear** — crossing 50% triggers rapid profit growth.
- At **0% friction, system is broken**: adversary grows to 90% in ~1 year at zero cost.
- At **~4.5% friction**: no sybil strategy is profitable within 2 years. This is the critical defense threshold.
- At **10% friction**: needs ~1 year and 7000 currency units investment to profit at 80-90% sybils.
- Progressive accumulation rate capped by 1/4 newcomer rule: max ~1/3 of network per ceremony.

**Friction** = cost of hiring minions as fraction of ceremony reward. Primary defense parameter. Even small friction (few %) makes attacks expensive and slow.

**Unmodeled real-world factors that further defend**: currency devaluation from sybil inflation (slows profit from exponential to linear), legitimate network growth (slows sybil fraction growth), limited real-world value of community currency (profit bounded by community market cap).

**Proposed mitigation**: "Absence counting" — honest participants report no-shows; after 2 absences, sybil ID removed. Not simulated.

**Key for our paper**: This is the correct quantitative security reference for Encointer (not Ford's informal analysis which assumes group size 4). The friction threshold of ~4.5% and the 50% sybil fraction breakpoint are the key numbers. Real-world deployments with low UBI value ($2/ceremony) inherently have high effective friction relative to minion recruitment costs in local labor markets — discuss this empirically.

---

## Cross-Reference Themes for the Paper

**Theme 1 — Encointer addresses the "personhood problem"**: Schneider identifies lack of reliable human ID as forcing DAOs into plutocracy. Encointer's PoP via physical ceremonies provides the missing identity primitive. Ford's four criteria (inclusive, equal, secure, private) are the evaluation framework.

**Theme 2 — Security analysis**: Ford's critique assumes group size 4 — misrepresentation. Hoffmann 2021 (Ford's own lab) provides correct quantitative analysis at group size 12+: attacks unprofitable below 50% sybil fraction, and friction threshold of ~4.5% blocks all attacks within 2 years. Real-world friction is inherently high when ceremony reward is ~$2 and minion recruitment has travel/coordination costs. Ohlhaver's Idena puppeteering ($2-$14/session) is a cautionary tale but Idena lacked physical co-presence requirement — Encointer's in-person ceremonies raise friction structurally. Present empirical evidence from deployments on whether sybil accumulation has materialized.

**Theme 3 — Community-level identity as structural advantage**: Ohlhaver's prescription (plurality of identity games, subsidiarity) maps directly to Encointer's per-community design. Schneider's modular politics maps to per-community governance customization.

**Theme 4 — Treasury governance as democratic legitimacy test**: Schneider's plutocracy critique motivates the problem. Ruddick documents the accumulation problem in community currencies. Encointer's adaptive quorum biasing + per-beneficiary limits + exercise fees are the concrete solution.

**Theme 5 — Governance mechanism design**: Ohlhaver's finding that one-pool-one-vote saved Idena validates discounted influence for concentrated power. Encointer's participation-weighted voting (capped 4x) + reputation delay are analogous safeguards. Adaptive quorum biasing balances legitimacy and agility — compare to Ruddick's 75% threshold and Schneider's citizen assemblies.
