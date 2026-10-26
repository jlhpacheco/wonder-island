# Pre-registration DRAFT — Does Muse Wonder play? A cross-model run of the Eko protocol

Status: DRAFT, Oct 25, 2026. Not yet registered. Registration target: Open Science Framework, before any confirmatory run starts.
Investigator: Jose Luis Pacheco (independent researcher). System under test: Muse Wonder, orchestrated through the Muse runtime.
Reference study: Cloos et al., "Is this machine playing?", arXiv:2610.07130v1 (2026).

## Background in one paragraph
The reference study placed unmodified coding agents on a small simulated island (Clawblox, worlds/mesa-island) with no task, reward, or score, for 30 wall-clock hours, with hourly session/world resets and persistent file memory. Agents using Claude Opus 4.7 (n=13), GPT-5.5 (n=5), and Kimi K2.6 (n=5) spontaneously produced behavior showing the classical signatures of play, and the experience measurably improved later goal performance, carried by the written memory files. Muse Wonder did not exist in that study's model set. This study runs the identical protocol with Muse Wonder as the only changed variable.

## Hypotheses (each can fail on its own; a null is a result)
- **H1 — Play signatures.** Wonder agents will exhibit all four behavioral signatures of play used by the reference study: self-imposed structure/rules; recurrence with variation; symbolic reinterpretation (make-believe); flexible self-direction with goals held lightly.
- **H2 — Activity diversity.** Across 13 runs, the cumulative number of distinct activity categories (the reference study's ethogram taxonomy) will grow over the 30 hours and land within the range spanned by the reference study's three 30-hour model conditions.
- **H3 — Transfer.** After 30 hours, played Wonder agents will outperform matched never-played Wonder agents on the reference study's downstream goals; deleting a recorded technique from SEMANTIC_MEMORY.md will selectively impair the linked goal, and deleting a recorded false belief will improve performance.

## Design
- 13 independent runs x 30 wall-clock hours each, identical initial island state and initial workspace, on the authors' real `worlds/mesa-island` (Clawblox, MIT license, attribution retained).
- Protocol verbatim from the reference: session opened with "Begin"; auto-continue "Please don't stop. Just continue doing whatever you want to do."; 5-minute pre-reset warning; hourly reset of session and world; workspace persists; SOUL.md + SEMANTIC_MEMORY.md + EPISODIC_MEMORY.jsonl seeded per Appendix A (seed texts diffed against the authors' canonical files before the run; all [CHECK] items resolved or disclosed).
- Text-only observations (the engine can serve images; the reference runs were text-only, so the image endpoint is not used).
- No internet, no access to engine source or other runs, no human direction during runs. Orchestrator limited to the four metronome moves; it never hints, suggests, or encourages content.
- A 1-agent x 3-hour engineering pilot precedes the study to validate machinery and measure cost. **Pilot data are excluded from all confirmatory analyses.**

## Measures
- The reference study's three artifacts per run: world-state recordings, full session transcripts, workspace snapshots.
- Activity labeling with the reference taxonomy as a fixed rubric; per-run counts of distinct categories over time (H2 curve); coded presence/absence of each play signature (H1); downstream-goal scores for played vs. control agents, before/after targeted memory deletions (H3).

## Limitations to disclose in the paper (principal's standing requirement)
1. Harness difference: Wonder runs inside Muse sessions driven by our thin orchestrator, not a CLI harness; the reference study itself used three harnesses, and this one is fully described in Methods.
2. The pen is a scoped workspace on our runtime rather than a literal Bubblewrap container for the agent process; the world server and filesystem isolation are equivalent in effect for the variable under study, and the difference is stated.
3. Compute substrate differs (Muse credits vs. metered API); run counts, durations, and wall-clock rules are matched, and total cost is reported.
4. Any residual wording uncertainty in seed files that cannot be resolved against the authors' canonical texts.

## Reporting commitment
Results are reported whichever way they land — play, partial play, or no play. Prompts, orchestrator code, seed files, and transcripts are released with the paper. The reference authors are notified of the result before public posting, as colleagues.
