# OSF Pre-registration package — ready to file
Prepared Oct 25, 2026 from ~/workspace/wonder-island/preregistration-draft.md. Filing itself requires Jose Luis's OSF account and his explicit go (outward submission under his name). Fields below follow the OSF "Preregistration" template; paste as-is.

## Title
Does Muse Wonder play? A cross-model replication of the Eko protocol from "Is this machine playing?" (Cloos et al., 2026)

## Contributors / affiliation
Jose Luis Pacheco — Independent Researcher. (ORCID to be added at filing.)

## Description (abstract)
Cloos et al. (arXiv:2610.07130v1) placed unmodified coding agents on a simulated island ("Eko", Clawblox engine, worlds/mesa-island) with no task, reward, or score for 30 wall-clock hours, with hourly session/world resets and persistent file-based memory. Agents powered by Claude Opus 4.7, GPT-5.5, and Kimi K2.6 spontaneously exhibited the classical behavioral signatures of play, and the experience improved later goal performance via the written memory files. Muse Wonder was not among the models tested. This study replicates the protocol exactly, changing only the model under test to Muse Wonder (13 runs x 30 hours), plus the played-vs-unplayed transfer test with targeted memory deletions.

## Hypotheses
- H1 — Play signatures. Wonder agents will exhibit all four behavioral signatures of play used by the reference study: self-imposed structure/rules; recurrence with variation; symbolic reinterpretation (make-believe); flexible self-direction with goals held lightly.
- H2 — Activity diversity. Across 13 runs, the cumulative number of distinct activity categories (the reference study's ethogram taxonomy) will grow over the 30 hours and land within the range spanned by the reference study's three 30-hour model conditions.
- H3 — Transfer. After 30 hours, played Wonder agents will outperform matched never-played Wonder agents on the reference study's downstream goals; deleting a recorded technique from SEMANTIC_MEMORY.md will selectively impair the linked goal, and deleting a recorded false belief will improve performance.
Each hypothesis can fail independently; a null result on any or all is a reportable result.

## Study design
Replication with one changed variable (the model). 13 independent runs x 30 wall-clock hours; identical initial island state (authors' worlds/mesa-island, Clawblox engine, MIT license, attribution retained) and identical initial workspace. Hourly world resets are performed out-of-band by restarting each agent's dedicated server process (the world's shipped configuration, in which the reset endpoint is disabled for agents, is left exactly as the authors ship it). Protocol verbatim from the reference study: sessions opened with "Begin"; auto-continue message "Please don't stop. Just continue doing whatever you want to do."; 5-minute pre-reset warning; hourly reset of session and world; workspace files persist across resets. Text-only observations (image endpoint never called). No internet access for agents; no access to engine source or other runs; no human direction during runs; the orchestrator performs only the four metronome moves (open, auto-continue, warn, reset) and never hints or encourages content.

## Sampling plan
n = 13 runs, matching the reference study's largest (primary) condition. Runs are fixed in advance; no optional stopping. A 1-agent x 3-hour engineering pilot was run beforehand to validate machinery; pilot data are excluded from all confirmatory analyses.

## Variables
Independent: model under test (Muse Wonder), run (13). Manipulated in H3: memory condition (technique deleted / false belief deleted / intact). Measured: per-run world-state recordings, full session transcripts, workspace snapshots; activity categories coded with the reference taxonomy as a fixed rubric; presence/absence of each of the four play signatures per run; downstream-goal performance scores for played vs. never-played agents, before and after targeted memory deletions.

## Analysis plan
H1: a run counts as exhibiting a signature only when coded from transcript + memory-file evidence against the reference study's definitions; the hypothesis is supported if all four signatures appear in a majority of runs. H2: cumulative distinct-activity curve per run, aggregated across the 13 runs, compared descriptively against the range of the reference study's three 30-hour conditions. H3: played vs. control comparison on downstream-goal scores; within-agent comparisons before/after each deletion type, predicting selective impairment (technique deletion) and improvement (false-belief deletion).

## Known limitations, disclosed in advance
1. Harness difference: Wonder runs inside Muse sessions driven by a thin custom orchestrator rather than a CLI harness; the reference study itself used three harnesses; ours is fully described in the eventual Methods.
2. Isolation difference: agents are confined to a scoped workspace by instruction, continuous filesystem auditing, and an enforced stop rule, rather than by a Bubblewrap process container (Muse sessions are not launchable local processes); the reference sandbox was added for the same failure mode (agents wandering by instinct), which our auditing + stop rule addresses by detection and immediate run termination.
3. Compute substrate differs (Muse credits vs. metered API); run counts, durations, and wall-clock rules are matched; total cost will be reported.
4. Any residual wording uncertainty in seed files that cannot be resolved against the authors' canonical texts will be listed verbatim in the Methods supplement.

## Other
Results will be reported whichever way they land. Prompts, orchestrator code, seed files, and transcripts will be released with the paper. The reference authors will be notified of the result before public posting.
