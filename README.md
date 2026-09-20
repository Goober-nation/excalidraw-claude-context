# excalidraw-region

A Claude Code skill that extracts the contents of one colored-rectangle
region from a large `.excalidraw` board, without loading the rest of the
board into the model's context.

**TL;DR:** highlight the section you want with a rectangle colored
**`#c1a4de`** (the default the script looks for — pass `--color <hex>` to
use a different one), export the board to a local `.excalidraw` file, and
run `scripts/extract_region.py` on it.

## Workflow

0. **(Only if given a live room link, not a file)** try
   `scripts/fetch_room.sh "<excalidraw.com/#room=...,... url>"` to fetch
   and decrypt the room's current scene into a standard `.excalidraw`
   file, best-effort (see Current state below). **If it fails for any
   reason, stop and ask the user for an exported `.excalidraw` file
   instead** — do not retry, do not attempt another decryption method.
1. **Run the analysis script** (`scripts/extract_region.py`) against a
   local `.excalidraw` file (an export, or `fetch_room.sh`'s output). It
   finds every rectangle matching a given color, then pulls every element
   whose center falls inside that rectangle — shapes, their labels,
   arrows (including ones that cross the boundary, marked as external),
   and floating text.
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

- `extract_region.py`: Python standard library only (`json`, `math`,
  `argparse`, `sys`) — no installs required.
- Handles multiple rectangles matching the same color: all are processed,
  grouped separately, with an explicit warning rather than silently
  picking one.
- Verified against a real multi-region board, including the multi-match
  warning path and both unlabeled-shape classifications.
- `fetch_room.sh`: **best-effort** support for live
  `excalidraw.com/#room=...` links. Excalidraw's room data is end-to-end
  encrypted with a key that lives only in the URL fragment; this script
  fetches the encrypted scene from Excalidraw's own (undocumented,
  unofficial) storage backend and decrypts it locally with that key,
  using Node's built-in `crypto` module (no `npm install`, no packages —
  only requires `node` to be present). Because it depends on an
  unofficial endpoint, it can break at any time and is not guaranteed to
  work — every failure mode falls back to asking the user for an
  exported file, which always works.

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

For a live room link instead of a file:

```bash
scripts/fetch_room.sh "<excalidraw.com/#room=...,... url>" > room.excalidraw
python3 scripts/extract_region.py room.excalidraw --color <hex>
```

If `fetch_room.sh` exits non-zero, it printed why to stderr — the correct
response is to ask the user for an exported `.excalidraw` file, not to
retry or work around it.

## Expected behavior

- Only elements geometrically inside the matched rectangle(s) are ever
  printed — nothing else from the board enters the output.
- Unlabeled-shape classifications and arrow-label associations are always
  presented as inferences with their supporting evidence, never asserted
  as plain fact.
- The skill will ask questions rather than answer confidently when the
  JSON doesn't give it enough evidence — this is intentional, not a
  limitation to work around.
- If `fetch_room.sh` fails, for any reason, the expected behavior is to
  ask the user for an exported `.excalidraw` file and continue with
  that — not to retry, not to attempt another decryption approach.
