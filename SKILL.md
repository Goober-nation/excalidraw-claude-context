---
name: excalidraw-region
description: Extract only the contents of a specific colored-rectangle region from an .excalidraw whiteboard file, without pulling the rest of the board into context. Use when the user shares an .excalidraw file (or export) and asks to read/discuss/focus on "just the [color] box", a specific section, or wants to avoid dumping the whole board into context — e.g. "pull the purple rectangle from this whiteboard", "what's in the parked-ideas box". Default region color is #c1a4de unless the user specifies another.
---

# Excalidraw region extraction

This skill isolates one labeled section of a large Excalidraw board so only
that section's nodes and connections enter the conversation — the rest of
the board (parked discussions, unrelated sections) is never read into
context.

**There is no browser/screenshot stage.** Everything is computed from the
`.excalidraw` JSON. When something genuinely can't be determined from the
JSON (an embedded raster image's actual content, a freehand drawing), ask
the **user** to look at the board themselves and describe it or send you a
screenshot — do not open a browser or render anything yourself.

## Prerequisite

You need a local path to an `.excalidraw` file (JSON export). If the user
only has a live collab link, this skill doesn't apply — a collab room's
scene data is end-to-end encrypted and only decryptable client-side in a
real browser session (not fetchable, not readable from a JSON export).
Ask the user to export via the board's menu → "Save to..." → File, and
give you that path.

## Running the analysis

```bash
python3 <this-skill's-directory>/scripts/extract_region.py <path-to-file> --color <hex>
```

`<this-skill's-directory>` is wherever this `SKILL.md` actually lives (e.g.
`~/.claude/skills/excalidraw-region`, or a project's
`.claude/skills/excalidraw-region` if installed there instead) — resolve
it relative to this file's own location, not a hardcoded path, so the
skill keeps working if it's moved, renamed, or cloned somewhere else.

Omit `--color` to use the default `#c1a4de`. Read the script's stdout
directly — do not also read or grep the raw `.excalidraw` file yourself;
the script's output is already the filtered, chat-safe summary.

**What it does, and why nothing here needs a screenshot:**

- Matches rectangles by `strokeColor`/`backgroundColor`.
- Pulls every element whose center point falls inside a matched
  rectangle's bounding box. Deleted elements are always ignored.
- Arrows with only one endpoint inside a region are kept, with the
  outside endpoint marked `EXTERNAL/TRUNCATED (leaves region at ~x,y)`.
  Arrows with both endpoints outside are omitted entirely.
- **Unlabeled-rectangle inference**: a rectangle with no bound text is
  classified as a likely GROUPING/ANNOTATION frame (it geometrically
  encloses 2+ other labeled shapes), likely LEFTOVER/DEBRIS (it reuses a
  color used by real labeled nodes elsewhere, but has no arrows attached
  to it), or explicitly flagged as purpose UNCLEAR when neither test
  gives evidence either way.
- **Floating-text-to-arrow association**: unbound text near an arrow
  (within 60px of the arrow's path) is reported as a likely label for
  that arrow (e.g. "RO", "rpc"). Text farther than that is kept separate
  and flagged as not confidently tied to anything, instead of being
  silently attached to the nearest guess.
- `image`/`freedraw` elements are listed by id only — the script cannot
  and does not try to interpret their visual content.

## Required order of operations

This order is mandatory, not a suggestion — do not collapse or reorder
these steps, and do not print the final summary early.

1. **Run the analysis script.** This is the only step that touches the
   file.
2. **State your understanding decisions to the user, before the
   summary.** This means telling them what you inferred and why, as its
   own step — e.g. "I'm reading the gray box as a grouping frame because
   it encloses 4 labeled shapes (Grade service, Repository service,
   kafka, S3), and the small pink box as leftover/debris because it
   reuses a color used by real nodes but has no arrows attached." Do not
   fold this into the final summary as if it were simply given — say it
   first, as your reasoning, so the user can correct it before it
   becomes "the answer."
3. **Ask about the ambiguities, after your analysis but before any
   summary.** Anything the script flagged as UNCLEAR, or floating text
   not confidently tied to an arrow, or anything visual (image/freedraw)
   whose content matters to the question — raise these with
   AskUserQuestion (or plain questions) now. Do not present a guess and
   wait to be corrected; ask first. If the answer requires seeing the
   actual board, ask the user to describe the area or send you a
   screenshot of it themselves — you do not have a way to render or view
   the board yourself in this skill.
4. **Only after 2 and 3 are resolved, give the final summary.** The
   summary should reflect the user's answers from step 3, not your
   original guesses.

## Notes

- Deleted elements (`isDeleted: true`) are always ignored.
- This only reads a file already on disk — it does not fetch live collab
  rooms (see Prerequisite above).
- There is deliberately no rendering/screenshot capability in this
  skill. If a future need for visual rendering comes up, that is a
  separate decision to make explicitly with the user, not something to
  fall back on automatically.
