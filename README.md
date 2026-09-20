# excalidraw-region
## TL;DR

1. **In Excalidraw**, draw a rectangle around the area you want and
   color it **`#c1a4de`** (the default).
2. **Give Claude either** a local `.excalidraw` export of the board, or
   the `excalidraw.com/#room=...` link, and ask about the selected section of that board —
   e.g. "summarize this board"
3. **Claude runs the skill**, looking at the area within the rectangle, and replies.
4. If anything's unclear, Claude asks you before
   answering.

## Required order

1. Run the script (fetch first if starting from a link).
2. State what was inferred.
3. Ask about whatever the script couldn't resolve before summarizing.
4. Give the final summary.

## Use

Place this directory under a Claude Code skills path (e.g.
`~/.claude/skills/excalidraw-region` for personal use, or a project's
`.claude/skills/excalidraw-region`). Claude Code picks it up automatically.

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
