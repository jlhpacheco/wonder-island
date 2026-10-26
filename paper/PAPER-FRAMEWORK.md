# Does Muse Wonder Play? A Pre-Registered Replication and Extension of Cloos et al. (2026)

**Author:** Jose Luis Pacheco — Independent Researcher
**Pre-registration:** OSF, DOI 10.17605/OSF.IO/UJZQ3 (filed Oct 25, 2026)
**Protocol package:** Zenodo, DOI 10.5281/zenodo.23654888
**Code and materials:** https://github.com/jlhpacheco/wonder-island

*Status: framework approved Oct 25, 2026. Sections fill in as the confirmatory run (Oct 25–27, 2026) completes and the analysis lands. Headings and one-line content notes below are the agreed skeleton — IMRaD structure, numbered references.*

---

## Abstract

*Content note: the question, the setup (13 Muse Wonder agents × 30 hours, mesa-island, text observations), the headline results — whichever way they land — and the one-line significance. Written last, kept to one paragraph.*

## 1. Introduction

*Content note: agents at population scale (Meta Q3 2026: 10M+ Muse agents in ~6 weeks, ~25% daily use, shopping the dominant use case); the question shifts from "can an agent do the task?" to "what does an agent do when nobody gives it a task?"; Cloos et al.'s island study and its empty Muse Wonder cell; this study's hypotheses H1–H3; the stakes — an agent economy forming before its customs.*

## 2. Method

### 2.1 The world
*Content note: Clawblox mesa-island (authors' world, pinned commit, unchanged config); entities (Peak, Spire, 12 cubes, rock, Ring); six commands; text-only JSON observations; the hidden rock-impact mechanic.*

### 2.2 Subjects and seeds
*Content note: 13 Muse Wonder agents; canonical seed files and their provenance (Appendix A reconstruction, one disclosed residue); no cross-agent contact; one dedicated world server per agent.*

### 2.3 Procedure
*Content note: hourly sessions opening with "Begin"; verbatim auto-continue; 5-minute memory warning (delivery limitation disclosed — warnings undeliverable to sessions outside the operator's scope, logged per protocol); hourly world reset by server-process restart (shipped world.toml leaves POST /reset disabled; decision documented); 30 wall-clock hours per agent, staggered starts.*

### 2.4 Containment and audit
*Content note: pen discipline; continuous filesystem boundary audits (390 scheduled); the three kill bars; pilot-001's kill at 5.5 minutes and the brief fix; honest statement — the fence is instruction + audit + kill, not a technical sandbox wall.*

### 2.5 Compute substrate and missing-data rule
*Content note: Muse credits vs. the paper's metered API (baseline rate, watchdog thresholds, no throttling by design); the registered missing-data rule verbatim; machinery downtime accounting.*

### 2.6 Downstream evaluation and memory ablations (H3 design)
*Content note: played vs. unplayed goal tasks mirroring the paper (tower building, objects on Spire, block-onto-Spire, tallest tower); technique-erasure ablations mirroring the paper's (rock-shattering, jump-before-throw, and the false-belief case); judge procedure.*

## 3. Results

### 3.1 Play signatures (H1)
*Content note: taxonomy coding of all 13 agents across 30 hours against the paper's four signatures; per-signature incidence vs. the paper's 13.*

### 3.2 Activity diversity (H2)
*Content note: diversity curves per agent and fleet; comparison against the paper's model range; rest/idle stretches reported as data.*

### 3.3 Thirteen portraits
*Content note: one short narrative per agent — what it invented, repeated, and varied — the Wonder analogue of the paper's comic figure.*

### 3.4 Transfer and memory deletion (H3)
*Content note: played vs. unplayed scores on each goal task (with the paper's honest-null precedent: tallest tower); ablation deltas per erased technique.*

## 4. Discussion

*Content note: what the results mean and what they do not; comparison with Cloos et al. point by point; implications for agent deployment at scale — play as competence formation, memory as the asset, guardrails and oversight as the governance question (worker voice, audit, human-in-command); the agent-economy framing (customs written at the start, not after).*

### 4.1 Limitations
*Content note: sandbox truth (instruction + audit, not a technical wall); harness and substrate differences; n = 13, single world; LLM judging; the 5-minute-warning delivery limitation; seed-reconstruction residue. Stated plainly, as registered.*

## 5. Conclusion

*Content note: one paragraph — the verdict on the title question, either way it lands.*

## Appendix

### A. Protocol strings (verbatim)
*Content note: the seed SOUL text, "Begin", the auto-continue line, the 5-minute warning — exactly as run.*

### B. Seed files
*Content note: the four canonical seed files with SHA-256 hashes and provenance pointer.*

### C. Audit procedure
*Content note: the boundary-audit method, baseline statics, adjudication rule (raw hits are claims; sweep-3 pen sweep is the verdict).*

### D. Incident record
*Content note: pilot-001 kill; three VM replacements during the confirmatory run and the recoveries; the fleet-clock death and the systemd fix; the operator split (clerk/starter) and the cadence diagnosis; the rented standby server and the held migration, with reasons. All machinery time excluded from behavioral data per §2.5.*

### E. Fleet manifest
*Content note: 13 agents, ports 8111–8123, start offsets, session ledger totals.*

## References

*Style: numbered, in order of first citation. Seed entries below; the list completes with the results.*

1. Cloos, N., Norelli, A., Durbin, D., Andreas, J., Rus, D., & Isola, P. (2026). *Is this machine playing?* arXiv:2610.07130.
2. Pacheco, J. L. (2026). *Does Muse Wonder play? Pre-registration.* OSF. DOI 10.17605/OSF.IO/UJZQ3.
3. Pacheco, J. L. (2026). *Wonder Island protocol package.* Zenodo. DOI 10.5281/zenodo.23654888.
4. Clawblox (2026). *Clawblox island server and mesa-island world.* GitHub: nacloos/clawblox, commit 8be90a0.
5. Meta Platforms (2026). *Q3 2026 earnings call*, Oct 21, 2026 (Muse adoption and commerce figures).
6. *Press coverage of Cloos et al.: TechCrunch (Oct 22, 2026); MIT Technology Review (Oct 19, 2026); explainx.ai explainer (Oct 23, 2026). Full citations in `context/press-coverage.md`.*
