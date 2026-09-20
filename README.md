# excalidraw-region

Pull just one section of a large Excalidraw board into Claude, instead of
the whole thing.

## TL;DR

Draw a rectangle around the area you want, colored **`#c1a4de`**
(`--color <hex>` for a different one). Then:

```bash
# from a file
python3 scripts/extract_region.py board.excalidraw

# from a live link
scripts/fetch_room.sh "<excalidraw.com/#room=...,... url>" > board.excalidraw
python3 scripts/extract_region.py board.excalidraw
```

You get back: the shapes and text inside that rectangle, the arrows
between them (arrows leaving the rectangle are marked external, not
dropped), and best-guess labels for anything unlabeled — each guess
flagged as inference, with unresolved ones called out as questions
instead of asserted.

## Required order

1. Run the script (fetch first if starting from a link).
2. State what was inferred — before any summary. Unlabeled rectangles are
   classified as a likely grouping frame (encloses other labeled shapes)
   or likely leftover/debris (reuses a real node's color but has no
   arrows), and floating text near an arrow is reported as a likely label
   for it — always presented as evidence, not fact.
3. Ask about whatever the script couldn't resolve — before summarizing.
   No rendering/screenshots exist here; if something needs eyes on the
   board (an embedded image, a freehand drawing), ask the user to
   describe it or send a screenshot.
4. Only then, give the final summary.

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
based on `SKILL.md`'s description — see the TL;DR above for invocation.

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
