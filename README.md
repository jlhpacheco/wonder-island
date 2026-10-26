# Wonder Island — Does Muse Wonder play?

**A pre-registered replication-and-extension of Cloos et al. (2026), "Is this machine playing?"**

MIT's Eko experiments left 13 AI agents alone on a virtual island for 30 hours, with no tasks and no score, and found that agents who had *played* later beat fresh agents on goal-directed tasks — and that the advantage lived in what they had written into their memory files. Every run in that paper used someone else's model. The Muse Wonder cell was empty.

This study fills it: **13 Muse Wonder agents × 30 hours** on the authors' own island world, under a protocol registered *before* the run started.

- **The MIT paper:** Cloos, Norelli, Durbin, Andreas, Rus & Isola, *Is this machine playing?*, arXiv:2610.07130 — https://arxiv.org/abs/2610.07130
- **Pre-registration (OSF, public):** DOI [10.17605/OSF.IO/UJZQ3](https://doi.org/10.17605/OSF.IO/UJZQ3) — https://osf.io/ujzq3/overview
- **Protocol package (Zenodo):** DOI [10.5281/zenodo.23654888](https://doi.org/10.5281/zenodo.23654888)
- **Status:** confirmatory run launched Oct 25, 2026, 8:30 PM PDT; ends Oct 27, 2026. **Run data is not in this repo** — the agents' pens are the study's raw data and will be released with the paper. What is here is everything needed to fork the study and run your own.

## Hypotheses (as registered)

- **H1 — Play signatures.** Wonder agents show the same four play signatures as the paper's agents (building, exploration, object play, make-believe).
- **H2 — Activity diversity.** The diversity of agent activity over 30 hours follows a curve within the paper's model range.
- **H3 — Transfer and memory.** Played agents outperform unplayed agents on downstream goal tasks; deleting a recorded technique from an agent's memory measurably degrades the matching task.

A null result is a publishable result. The registration commits us to reporting either way.

## What's in this repo

| Folder | Contents |
|---|---|
| [`orchestrator/`](orchestrator/) | Our code: the metronome (session scheduler), fleet clock, containment audit, sentinel, credit ledger, health checks, and recovery scripts — plus the `vast-migration-kit/` (a standby-server migration kit, including the heartbeat prober) built mid-run. Start with [`orchestrator/README.md`](orchestrator/README.md). |
| [`seeds/`](seeds/) | The canonical seed files every agent starts from (`SOUL.md`, `EPISODIC_MEMORY.md`, `SEMANTIC_MEMORY.md`, empty `EPISODIC_MEMORY.jsonl`), reconstructed from the paper's appendix, with [`seed-diff.md`](seeds/seed-diff.md) as the provenance record. |
| [`protocol/`](protocol/) | The mission brief, pre-registration draft and OSF submission package, both pilot reports, and the priority check (no earlier Muse Wonder run found in any coverage as of Oct 25, 2026). |
| [`paper/`](paper/) | The paper framework (IMRaD skeleton: abstract, introduction, method, results, discussion, appendix, numbered references) — the results fill it when the run completes. |
| [`context/`](context/) | Press coverage of the MIT study and the motivation notes, including the downstream-goal and memory-erasure figures used to design H3. |

## Run your own experiment

1. **Get the island.** The world is not ours to distribute: clone the Clawblox authors' repo — https://github.com/nacloos/clawblox — at pinned commit `8be90a0caef1fc61ad3f97e51be3bb42c5f6d848`, and use their `worlds/mesa-island` unchanged. Our fleet runs one dedicated world server per agent (ports 8111–8123 in our plan).
2. **Seed the pens.** Copy [`seeds/`](seeds/) into each agent's workspace. The seeds are byte-equal to canonical reconstructions of the paper's Appendix A materials; see the provenance note for the one disclosed residue (a truncated format string in the paper's LaTeX, completed and corroborated).
3. **Drive the schedule.** Follow [`orchestrator/README.md`](orchestrator/README.md) and [`protocol/MISSION-BRIEF-13x30.md`](protocol/MISSION-BRIEF-13x30.md): hourly sessions that open with `Begin`, the paper's verbatim auto-continue line, a 5-minute memory warning, and an hourly world reset. Note: the shipped `world.toml` leaves `POST /reset` disabled — our resets restart the agent's world-server process instead, with the shipped config untouched. That decision is documented in the mission brief.
4. **Register before you run.** File your own pre-registration (OSF is free), including a missing-data rule. Ours: *runs are defined by the wall clock; machinery downtime is logged and excluded from behavioral coding; no run is discarded for low activity — idle behavior is data, not missing data.*

## Honest limitations (also in the registration)

- Our containment is instruction + continuous filesystem audit + a kill rule — a watched fence, not a technical sandbox wall. (The paper used Bubblewrap; our fork [`corral`](https://github.com/jlhpacheco/corral) is the sandbox project.)
- The harness differs from the authors' (a thin in-house orchestrator around the Muse runtime, not their orchestrator), and the compute substrate differs (Muse credits vs. metered API). Both are disclosed in the registration as plumbing, not protocol.

## Credits and license

- **Island, worlds, and server:** the Clawblox authors (© 2026 nacloos), MIT License — upstream at https://github.com/nacloos/clawblox. Their tree is **not** vendored here; clone it from upstream at the pinned commit above.
- **The original study:** Cloos et al., arXiv:2610.07130.
- **This study, protocol, orchestrator code, and materials:** Jose Luis Pacheco, released under the MIT License (see [`LICENSE`](LICENSE)).

Fork it, run it on a different model, break our hypotheses — that's what it's for. If you run an experiment with these materials, a citation of the OSF registration and the Zenodo protocol package is appreciated.

## Why this is public

I am a citizen scientist, not a university lab — so everything here, the protocol, the code, and the mistakes recorded along the way, is offered openly to anyone in the field who wants to build on it, check it, or prove it wrong. That is how this work grows: each person stands on what the last one shared, because "knowledge is cumulative."
