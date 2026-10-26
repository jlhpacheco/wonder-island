# Wonder Island — Press & Explainer Coverage

Background/related-work coverage of Cloos et al., "Is this machine playing?" (arXiv:2610.07130v1), collected for the paper's background section. Our study: "Does Muse Wonder play?" — OSF registration DOI 10.17605/OSF.IO/UJZQ3.

---

## 1. explainx.ai — "AI Agents Play: MIT Left 13 Claude Agents on an Island"

- **Source:** explainx.ai blog; details current as of **Oct 23, 2026**
- **URL:** https://explainx.ai/blog/mit-eko-claude-opus-4-7-agents-virtual-island-play-is-this-machine-playing-2026
- **Filed:** Oct 25, 2026 (approved by Jose Luis)

**What the explainer covers:**

- A plain-language walkthrough of the MIT Eko setup: unmodified Claude Code (Opus 4.7) + orchestrator ("Begin" / auto-continue) + text-only embodiment on the Clawblox mesa island, hourly session/world resets, persistent episodic/semantic memory files, and the curious SOUL.md seed persona (with the no-SOUL ablation noted).
- The observed play taxonomy: building/towers, climbing (8 agents recorded reaching the Spire), pattern-making, simplified sports, hypothesis-testing experiments, and rest — plus the four play signatures the paper scores (self-created rules, recurrence with variation, make-believe, goals held lightly) via a blinded LLM judge.
- The downstream transfer results: agents with 30 h of play generally beat identical 0-hour agents on later goal tasks (3 of 4 goals).
- Memory-erasure evidence that the learning is real, carried by the written files rather than narration.
- Secondary coverage it cites: TechCrunch (Oct 22, 2026, "Left alone with nothing to do, AI agents started playing") and MIT Technology Review (Oct 19, 2026); total MIT run cost ~$8,000 in API calls noted.

**Useful for our paper:**

- **(a) Reproduction is explicitly invited.** The article's "How to check the claims yourself" section tells readers to clone Clawblox, replay recorded runs, and reproduce runs with other models, comparing against the paper's Haiku/Sonnet numbers. As of Oct 23, 2026, no Muse Wonder run exists in any coverage found — Wonder remains the unrun cell, and our 13×30 confirmatory run is the first attempt at it.
- **(b) Downstream-goal table (30 h played vs 0 h unplayed), for H3 comparison:**
  - Build many towers (>2): **62%** of played agents (8/13, max 16 towers) vs **15%** unplayed (2/13, max 6)
  - Objects placed on the Spire: average **10.3** vs **3.5**
  - Throw a block onto the Spire: only **3 of 13** played agents failed vs **more than half** of unplayed
  - Tallest tower: **no advantage** (similar scores; two played agents built only 4-high towers, below the unplayed minimum)
- **(c) Memory-erasure specifics, for mirroring in our H3 deletion tests:**
  - Rock-shattering technique erased → tower count dropped ~**6 → ~2** (other goals unchanged)
  - Jump-before-throw technique erased → time to land a block on the Spire rose **60 s → 19 min**
  - A false belief erased (towers must be thrown, not placed) → tallest-tower score significantly **improved**
- **(d) Limitations overlap.** The article's limits list — preprint, not peer-reviewed; small n and single environment; curiosity-persona (SOUL.md) nudge; LLM-judge ratings — overlaps the limitations already disclosed in our OSF pre-registration, so our disclosure posture matches the public critical framing.
