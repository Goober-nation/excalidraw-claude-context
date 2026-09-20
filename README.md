# excalidraw-region

A Claude Code skill that extracts the contents of one colored-rectangle
region from a large `.excalidraw` board, without loading the rest of the
board into the model's context.

**TL;DR:** highlight the section you want with a rectangle colored
**`#c1a4de`** (the default the script looks for — pass `--color <hex>` to
use a different one), export the board to a local `.excalidraw` file, and
run `scripts/extract_region.py` on it.

## Workflow

1. **Run the analysis script** (`scripts/extract_region.py`) against a
   local `.excalidraw` export. It finds every rectangle matching a given
   color, then pulls every element whose center falls inside that
   rectangle — shapes, their labels, arrows (including ones that cross
   the boundary, marked as external), and floating text.
2. **State understanding decisions before any summary.** The script
   applies two geometric heuristics and reports them as evidence, not
   fact: an unlabeled rectangle is classified as a likely
   grouping/annotation frame (it encloses other labeled shapes) or likely
   leftover/debris (it reuses a color from real nodes but has no arrows
   attached); floating text within 60px of an arrow's path is reported as
   a likely label for that arrow.
3. **Ask about ambiguities before summarizing.** Anything the script
   can't resolve — an unlabeled shape with no supporting evidence either
   way, floating text too far from any arrow, or the contents of an
   embedded image/freehand drawing — is surfaced as a question rather
   than guessed.
4. **Give the final summary only after those questions are answered.**

There is no rendering or screenshot capability. If something requires
looking at the board, the workflow asks the user to describe it or send a
screenshot themselves.

## Current state

- Single script, Python standard library only (`json`, `math`, `argparse`,
  `sys`) — no installs required.
- Handles multiple rectangles matching the same color: all are processed,
  grouped separately, with an explicit warning rather than silently
  picking one.
- Does not read live Excalidraw collaboration links — those are
  end-to-end encrypted and only decryptable client-side in a browser.
  Requires a local `.excalidraw` JSON export.
- Verified against a real multi-region board, including the multi-match
  warning path and both unlabeled-shape classifications.

## Use

Place this directory under a Claude Code skills path (e.g.
`~/.claude/skills/excalidraw-region` for personal use, or a project's
`.claude/skills/excalidraw-region`). Claude Code picks it up automatically
based on `SKILL.md`'s description.

Manual invocation:

```bash
python3 scripts/extract_region.py <path-to-file.excalidraw> --color <hex>
```

`--color` defaults to `#c1a4de` if omitted.

## Expected behavior

- Only elements geometrically inside the matched rectangle(s) are ever
  printed — nothing else from the board enters the output.
- Unlabeled-shape classifications and arrow-label associations are always
  presented as inferences with their supporting evidence, never asserted
  as plain fact.
- The skill will ask questions rather than answer confidently when the
  JSON doesn't give it enough evidence — this is intentional, not a
  limitation to work around.
