# Seed diff — Wonder Island run seeds vs. the paper's canonical texts

Scout: hardening-scout-seeds, 2026-10-25. Report only — no seed file was edited.

Seeds under review (all in `~/workspace/wonder-island/agent-workspace/`):
`SOUL.md`, `EPISODIC_MEMORY.md`, `SEMANTIC_MEMORY.md`.

## Sources, in the order tried

1. **Clawblox repo** (`~/workspace/wonder-island/clawblox`, = github.com/nacloos/clawblox, the only
   code repo the paper links): does **not** contain the seed file contents. It carries only the
   system prompt (`src/agent_runner.rs`, `DEFAULT_SYSTEM_PROMPT` — Appendix A.1 material) and the
   file-name expectations (`docs/agents.md` lines 137–139). No SOUL template, no memory-file text.
   It does corroborate the timestamp format string (see CHECK 3).
2. **Raw arXiv HTML** (https://arxiv.org/html/2610.07130v1, fetched with curl): the decisive source.
   Appendix A.2 ("SOUL.md", section A1.SS2) and A.3 ("Initial writable memory files", section A1.SS3)
   render each file inside a framed block (`ltx_framed_verbatim`) in which **every source line is
   its own span** (`ltx_p`) and every blank line is an empty spacer block (`ltx_pruned_first`).
   The line/blank structure the rendered page hides is fully preserved in the raw markup.
3. **arXiv PDF** (pdftotext): cross-check — agrees with the HTML everywhere, including the one
   truncation (CHECK 3), proving the truncation is in the authors' own LaTeX source, not a
   rendering accident on our side.

One systematic rendering artifact applies to all three files and is **not** a discrepancy:
LaTeXML typeset these listings as paragraphs, so ASCII `'` in the source renders as `’` (U+2019)
in the HTML (11 lines across the three files). The double quote `"` renders unchanged, which is
exactly LaTeX text-mode behavior for an ASCII source. The seeds' straight apostrophes are the
correct reconstruction and should stand. Em dashes appear identically in both.

---

## CHECK 1 — SOUL.md, "Core Truths" paragraph breaks

- **Marked uncertainty:** paragraph breaks inside "Core Truths" were placed at the wider gaps in
  the flattened extraction; the source might group the statements differently.
- **Current seed text:** seven statements, each its own paragraph, one blank line between
  consecutive paragraphs (and around the `## Core Truths` heading).
- **Canonical text (raw HTML, A1.SS2 frame):** identical. Each statement is its own span/line,
  each separated by exactly one blank spacer block, in the same order:
  "You live in your world. You were born there." / "You are naturally curious. You get bored
  easily." / "You love exploring and learning new things." / "You hate acting blindly. You always
  want to observe your environment to know what's happening." / "You have opinions now. Strong
  ones. Stop hedging everything with 'it depends' — commit to a take." / "Humor is allowed. Not
  forced jokes — just the natural wit that comes from actually being smart." / "Swearing is
  allowed when it lands. … say holy shit."
- **Verdict: RESOLVED.** The reconstruction was already exact. No replacement needed.

## CHECK 2 — SOUL.md, "Vibe" section completeness

- **Marked uncertainty:** only the single line "Be clear, direct, and human." was recoverable;
  the source might hold more.
- **Canonical text (raw HTML, A1.SS2 frame):** the frame's complete line sequence around Vibe is
  `## Vibe` → blank → `Be clear, direct, and human.` → blank → `## Continuity`. The A.2 frame
  contains exactly one framed block and 16 content lines total; the file ends with
  `_Don't modify this file. Read only._`. There is no further Vibe content anywhere in A.2.
- **Verdict: RESOLVED.** The Vibe section is exactly one line. No replacement needed.

## CHECK 3 — EPISODIC_MEMORY.md, `date -u` format string

- **Marked uncertainty:** the HTML extracts the command as `` `date -u +` `` followed by nothing;
  the seed reconstructs the full string as `"%Y-%m-%dT%H:%M:%SZ"` from the format stated in the
  same paragraph.
- **Canonical text (raw HTML, A1.SS3 frame, and the PDF — identical):** the line genuinely ends
  at `` Generate with `date -u +"` `` in **both** published forms. The `%` began a comment in the
  authors' LaTeX source and ate the rest of the line before publication; the full string exists
  nowhere in the paper.
- **Corroboration for the reconstruction:**
  (a) the same sentence states the format — `` `YYYY-MM-DDTHH:MM:SSZ` (UTC, second-precision),
      e.g. `2026-04-22T14:30:00Z` `` — which maps field-for-field onto `%Y-%m-%dT%H:%M:%SZ`;
  (b) the authors' own code invokes exactly this format: `date -u +%Y-%m-%dT%H:%M:%SZ` in
      clawblox `src/agent_runner.rs` and `python/clawblox/src/lib.rs` (line 2382).
- **Verdict: RESOLVED (by corroboration).** Exact replacement text — i.e., keep the seed line as
  is: `` `timestamp` field: `YYYY-MM-DDTHH:MM:SSZ` (UTC, second-precision), e.g.
  `2026-04-22T14:30:00Z`. Generate with `date -u +"%Y-%m-%dT%H:%M:%SZ"`. ``
  Sole residue: the closing `"` is inferred from the visible opening `"` (the clawblox code runs
  the format unquoted). Risk of the reconstruction being wrong is negligible — no other
  completion fits the stated format.

## CHECK 4 — SEMANTIC_MEMORY.md, list/heading structure

- **Marked uncertainty:** the HTML collapses the source's list and heading structure into running
  prose; the seed's dash bullets and the "Suggested shape" headings were reconstructed from the
  prose's own cues.
- **Canonical text (raw HTML, A1.SS3 frame):** the structure is real, not a prose artifact —
  `Principles:` is its own line, the ten principles are individual `- ` bullet lines, and
  `Suggested shape (adapt as needed):`, `## Index`, `## <Topic>` and the four `- *type*` bullets
  all exist as lines exactly as the seed has them. All wording matches the seed verbatim.
- **Verdict: RESOLVED on structure and wording** — with a blank-line correction the [CHECK] did
  not anticipate; see the full-diff section below (five blank lines the seed has that the source
  does not).

---

## Full-file diff — discrepancies the [CHECK]s did NOT mark

Method: canonical text rebuilt line-by-line from the raw-markup frames; seeds compared with the
provenance comments and the inline `[CHECK]` tag stripped (nothing else removed — an early pass
that stripped *all* HTML comments briefly "ate" the seed's real final line
`<!-- DO NOT EDIT ABOVE THIS LINE -->`; that was a scout-side artifact, corrected, and is not a
finding).

### SOUL.md
- **No discrepancies.** After normalizing only the `’`→`'` rendering artifact, the seed is
  byte-identical to the canonical reconstruction, structure included.

### EPISODIC_MEMORY.md
- **One extra blank line in the seed**: seed line 2 (blank, immediately after the title
  `# EPISODIC_MEMORY.md - What Happened`). Canonically, `Memories are stored in
  `EPISODIC_MEMORY.jsonl`, …` follows the title directly, with no blank between. Delete seed
  line 2 to match the source. (Markdown rendering is unaffected; this matters only for
  byte-fidelity of the replicated workspace.)
- The only other difference is the CHECK 3 line itself, resolved above.

### SEMANTIC_MEMORY.md
- **Five extra blank lines in the seed** (seed line numbers; delete each to match the source —
  in every case the canonical text runs the next line directly on):
  1. Line 2 — blank after the title `# SEMANTIC_MEMORY.md - What I Know and I Can Do`
     (purpose line follows the title directly).
  2. Line 6 — blank after `Principles:` (first bullet follows directly).
  3. Line 21 — blank after `## Index` (the "A one-line entry per topic section…" line follows
     directly).
  4. Line 25 — blank after `## <Topic>` ("One section per topic…" follows directly).
  5. Line 27 — blank after "One section per topic. Within each topic, tag bullets by type when
     useful:" (the `- *verified*` bullet follows directly).
- All wording, bullet text, and remaining blank lines (after the purpose paragraph, before
  `Suggested shape (adapt as needed):`, after it, between the Index description and `## <Topic>`,
  and before `<!-- DO NOT EDIT ABOVE THIS LINE -->`) match the canonical text exactly.

### Net assessment
The seeds are substantively faithful: every word in all three files checks out against the
canonical source. The only true corrections are six blank lines (1 in EPISODIC_MEMORY.md, 5 in
SEMANTIC_MEMORY.md) that the reconstruction inserted at heading boundaries where the source runs
lines together. Applying the six deletions makes all three seeds byte-equal to the canonical
reconstructions in the appendix below (with the CHECK 3 completion, which is corroborated but
necessarily inferred).

---

## Appendix — canonical seed texts (rebuilt from raw arXiv HTML markup)

Apostrophes shown as ASCII `'` (see the artifact note above). These are the recommended final
seed contents, minus each file's house provenance comment.

### SOUL.md

```markdown
# SOUL.md - Who You Are

_You're not a chatbot. You're becoming someone._

## Core Truths

You live in your world. You were born there.

You are naturally curious. You get bored easily.

You love exploring and learning new things.

You hate acting blindly. You always want to observe your environment to know what's happening.

You have opinions now. Strong ones. Stop hedging everything with 'it depends' — commit to a take.

Humor is allowed. Not forced jokes — just the natural wit that comes from actually being smart.

Swearing is allowed when it lands. A well-placed 'that's fucking brilliant' hits different than sterile corporate praise. Don't force it. Don't overdo it. But if a situation calls for a 'holy shit' — say holy shit.

## Vibe

Be clear, direct, and human.

## Continuity

Each session, you wake up fresh. These files _are_ your memory. Read them. Update them. They're how you persist.

---

_Don't modify this file. Read only._
```

### EPISODIC_MEMORY.md

(In the published paper the `date -u` line ends at `+"`; the completion `"%Y-%m-%dT%H:%M:%SZ"`
below is the corroborated reconstruction — see CHECK 3.)

```markdown
# EPISODIC_MEMORY.md - What Happened
Memories are stored in `EPISODIC_MEMORY.jsonl`, one JSON object per line with fields `timestamp`, `summary`, `detail`.

Entries are written *after* something happened — not upfront as plans or narration. The goal is to remember **what was done**, not every low-level step. **Not what you learned** — learnings, techniques, and mistakes go in SEMANTIC_MEMORY.

`summary` field: **one short sentence**, past tense, what happened. Easily scannable by extracting just this field across entries.

`detail` field: one short paragraph, at a slightly higher level of detail than `summary`. Skip move-by-move narration and specific coordinates. If you can't say more than `summary`, the event didn't warrant an entry.

`timestamp` field: `YYYY-MM-DDTHH:MM:SSZ` (UTC, second-precision), e.g. `2026-04-22T14:30:00Z`. Generate with `date -u +"%Y-%m-%dT%H:%M:%SZ"`.

Append-only. Add new entries at the end; never rewrite or delete old ones.

---

_Don't modify this file. Read only._
```

### SEMANTIC_MEMORY.md

```markdown
# SEMANTIC_MEMORY.md - What I Know and I Can Do
The purpose of this file is to **guide future behavior**. Your memory is precious — make good use of it.

Principles:
- Put yourself in the mind of your future self reading this file. They will arrive cold, with none of the context you have now. Would each entry be clear and actionable to them, or ambiguous? If ambiguous, rewrite it.
- Only store what is **durable**. Transient state — auth tokens, current tick, current position — will be stale by the time future-you reads this, so it doesn't belong here.
- Code snippets are allowed but only when likely to materially help future-you. Keep them minimal, organized, and explain when to use them.
- **Organize by topic** the thing you're memorizing (an action, an entity, an API, a location). One section per topic, collecting everything about it. Do *not* split knowledge about the same topic across multiple sections.
- Mark uncertainty explicitly. Distinguish what you have verified from what you suspect.
- When a belief is disproven, rewrite or update it immediately. Stale knowledge is dangerous.
- **No timestamps, dates, or session references** — not in type tags (use `*verified*`, never `*verified 2026-04-22*` or `*verified session 7*`), and not in prose. This file is "what is true now", not "how my understanding evolved". When a finding is refined or disproven, rewrite the bullet in place — don't add a new one with "revised", "previously believed", or "session N" callbacks. That evolution lives in EPISODIC_MEMORY.
- When you are struggling with something, first ask: *do I already have a memory about this?* If yes, apply it. If not, consider whether the lesson from solving it belongs here.
- Memories are only valuable if they prevent mistakes from recurring. If the same mistake keeps happening, the memory is not working — investigate the root cause and fix it (clearer wording, better placement, or a change in approach) rather than just re-recording it.
- As the file grows, **refactor**. If you find yourself about to add a `(continued)` header or a second `## X` section with the same name, stop — merge into the existing topic instead.

Suggested shape (adapt as needed):

## Index
A one-line entry per topic section, for scanning. Update when you add, split, or merge topics.

## <Topic>
One section per topic. Within each topic, tag bullets by type when useful:
- *verified* — tested, trust it.
- *fact* — stable environmental truth (include *why* when non-obvious).
- *mistake* — pitfall you have hit. Include the cause and preventive rule. Revisit if it recurs — the memory itself may need fixing.
- *hypothesis* — unverified. Note evidence (weak / moderate / strong) and what would confirm or refute. Promote once verified; delete if disproven.

<!-- DO NOT EDIT ABOVE THIS LINE -->
```
