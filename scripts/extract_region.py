#!/usr/bin/env python3
"""Extract the contents of colored rectangle region(s) from an .excalidraw file.

Usage:
    extract_region.py <file.excalidraw> [--color #c1a4de]

Finds every rectangle whose strokeColor or backgroundColor matches the given
color, then pulls every element whose center point falls inside that
rectangle's bounding box. Arrows with only one endpoint inside a region are
kept but their outside endpoint is marked external/truncated instead of
being resolved to a node name. Nothing outside the matched rectangle(s) is
included in the output.

Also applies two purely-geometric inference heuristics so the caller does
not have to guess (or render a screenshot) for things the JSON already
answers:
  - floating (unbound) text is associated with the nearest arrow, when
    that arrow is close enough to be a confident match (labels like
    "RO"/"RW"/"rpc" sitting next to a connection);
  - unlabeled rectangles are classified as likely grouping/annotation
    frames (they enclose other labeled shapes) vs. likely leftover/debris
    (disconnected, reusing another semantic color) vs. genuinely unclear,
    in which case the script says so explicitly instead of asserting a
    meaning -- ask the user in that case.
"""
import argparse
import json
import math
import sys

LABEL_MAX_DIST = 60  # px; below this, a floating text is confidently "about" an arrow


def norm_color(c):
    if not c:
        return None
    c = c.strip().lower()
    return c if c.startswith("#") else "#" + c


def bbox(e):
    x, y = e["x"], e["y"]
    w, h = e.get("width", 0), e.get("height", 0)
    return x, y, x + w, y + h


def center(e):
    x0, y0, x1, y1 = bbox(e)
    return (x0 + x1) / 2, (y0 + y1) / 2


def point_in_bbox(pt, box):
    px, py = pt
    x0, y0, x1, y1 = box
    return x0 <= px <= x1 and y0 <= py <= y1


def bound_text(elements, container_id):
    for e in elements:
        if e["type"] == "text" and e.get("containerId") == container_id:
            return e.get("text", "").strip()
    return None


def label_for(elements, by_id, elem_id):
    if elem_id is None:
        return None
    e = by_id.get(elem_id)
    if not e:
        return f"<unknown:{elem_id[:8]}>"
    txt = bound_text(elements, elem_id)
    if txt:
        return txt.replace("\n", " ")
    if e["type"] == "text":
        return e.get("text", "").strip().replace("\n", " ")
    return f"{e['type']}:{elem_id[:6]}"


def arrow_endpoint_world(e, which):
    points = e.get("points") or [[0, 0], [e.get("width", 0), e.get("height", 0)]]
    px, py = points[0] if which == "start" else points[-1]
    return e["x"] + px, e["y"] + py


def arrow_world_points(e):
    points = e.get("points") or [[0, 0], [e.get("width", 0), e.get("height", 0)]]
    return [(e["x"] + px, e["y"] + py) for px, py in points]


def point_seg_dist(p, a, b):
    px, py = p
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    cx, cy = ax + t * dx, ay + t * dy
    return math.hypot(px - cx, py - cy)


def dist_to_arrow(pt, arrow):
    wp = arrow_world_points(arrow)
    return min(point_seg_dist(pt, wp[i], wp[i + 1]) for i in range(len(wp) - 1))


def arrow_desc(elements, by_id, arrow):
    s_bind = (arrow.get("startBinding") or {}).get("elementId")
    t_bind = (arrow.get("endBinding") or {}).get("elementId")
    s = label_for(elements, by_id, s_bind) or "(unbound)"
    t = label_for(elements, by_id, t_bind) or "(unbound)"
    return f"{s} -> {t}"


def classify_unlabeled_rect(elements, by_id, rect, kept_shapes):
    """Return a one-line, evidence-based note about an unlabeled rectangle's
    likely purpose, or a note saying to ask the user when there's no
    geometric/color evidence either way."""
    rbox = bbox(rect)

    contained = [
        s for s in kept_shapes
        if s["id"] != rect["id"] and bound_text(elements, s["id"])
        and point_in_bbox(center(s), rbox)
    ]

    own_color = norm_color(rect.get("strokeColor")) or norm_color(rect.get("backgroundColor"))
    color_twins = [
        s for s in elements
        if s["id"] != rect["id"] and s["type"] in ("rectangle", "diamond")
        and bound_text(elements, s["id"])
        and (norm_color(s.get("strokeColor")) == own_color or norm_color(s.get("backgroundColor")) == own_color)
        and own_color not in (None, "transparent")
    ]

    has_arrows = any(b.get("type") == "arrow" for b in (rect.get("boundElements") or []))

    if len(contained) >= 2:
        names = ", ".join(bound_text(elements, s["id"]).replace("\n", " ") for s in contained)
        return (f"likely a GROUPING/ANNOTATION frame (encloses {len(contained)} labeled "
                f"shapes: {names}) -- probably not a functional node itself")

    if color_twins and not has_arrows:
        names = ", ".join(bound_text(elements, s["id"]).replace("\n", " ") for s in color_twins[:3])
        return (f"likely LEFTOVER/DEBRIS -- reuses the same color as labeled node(s) "
                f"({names}) but has no arrows connecting it to anything")

    return "purpose UNCLEAR from color/geometry alone -- ask the user, do not guess"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--color", default="#c1a4de")
    args = ap.parse_args()

    target = norm_color(args.color)

    with open(args.file) as f:
        data = json.load(f)

    elements = [e for e in data.get("elements", []) if not e.get("isDeleted")]
    by_id = {e["id"]: e for e in elements}

    regions = [
        e for e in elements
        if e["type"] == "rectangle"
        and (norm_color(e.get("strokeColor")) == target
             or norm_color(e.get("backgroundColor")) == target)
    ]

    if not regions:
        print(f"No rectangles found with color {target}. Nothing extracted.")
        sys.exit(0)

    if len(regions) > 1:
        print(f"⚠️  WARNING: {len(regions)} rectangles match color {target} — "
              f"pulling nodes from ALL of them, grouped below. If you only "
              f"meant one region, narrow by editing the board or picking a "
              f"more specific color.\n")

    region_boxes = [(r, bbox(r)) for r in regions]

    seen_ids = set()

    for idx, (region, rbox) in enumerate(region_boxes, 1):
        region_ids = {r["id"] for r, _ in region_boxes}
        region_title = bound_text(elements, region["id"])
        title_suffix = f'  title="{region_title}"' if region_title else ""
        print(f"--- Region {idx}/{len(regions)}  "
              f"(rect id={region['id'][:8]}, pos=({rbox[0]:.0f},{rbox[1]:.0f}), "
              f"size=({rbox[2]-rbox[0]:.0f}x{rbox[3]-rbox[1]:.0f}){title_suffix}) ---")

        shapes_out = []
        arrows_out = []
        unlabeled_notes = []
        kept_shapes = []
        loose_texts = []

        for e in elements:
            if e["id"] == region["id"] or e["id"] in region_ids:
                continue
            if e.get("containerId"):
                continue  # bound text handled via its container
            if e["type"] == "arrow":
                continue  # handled separately below
            c = center(e)
            if not point_in_bbox(c, rbox):
                continue
            seen_ids.add(e["id"])
            if e["type"] in ("rectangle", "diamond", "ellipse"):
                kept_shapes.append(e)
                txt = bound_text(elements, e["id"])
                if txt:
                    shapes_out.append(
                        f"  [{e['type']}] {txt}  "
                        f"pos=({e['x']:.0f},{e['y']:.0f}) size=({e['width']:.0f}x{e['height']:.0f})"
                    )
                else:
                    shapes_out.append(
                        f"  [{e['type']}] (no label)  "
                        f"pos=({e['x']:.0f},{e['y']:.0f}) size=({e['width']:.0f}x{e['height']:.0f})"
                    )
            elif e["type"] == "text":
                loose_texts.append(e)
            elif e["type"] in ("image", "freedraw"):
                shapes_out.append(f"  [{e['type']}] id={e['id'][:8]} (visual only, no text -- "
                                   f"cannot be summarized from geometry, view it directly if needed)")

        region_arrows = []
        for e in elements:
            if e["type"] != "arrow":
                continue
            s_bind = (e.get("startBinding") or {}).get("elementId")
            t_bind = (e.get("endBinding") or {}).get("elementId")
            s_pt = arrow_endpoint_world(e, "start")
            t_pt = arrow_endpoint_world(e, "end")
            s_in = point_in_bbox(s_pt, rbox)
            t_in = point_in_bbox(t_pt, rbox)
            if not s_in and not t_in:
                continue
            seen_ids.add(e["id"])
            region_arrows.append(e)

            def resolve(bound_id, pt, is_in):
                if is_in:
                    return label_for(elements, by_id, bound_id) or "(unbound point)"
                return f"EXTERNAL/TRUNCATED (leaves region at ~{pt[0]:.0f},{pt[1]:.0f})"

            s_label = resolve(s_bind, s_pt, s_in)
            t_label = resolve(t_bind, t_pt, t_in)
            arrow_label = bound_text(elements, e["id"])
            suffix = f"  [{arrow_label}]" if arrow_label else ""
            arrows_out.append(f"  {s_label}  ->  {t_label}{suffix}")

        # unlabeled-rectangle classification (evidence-based, ask-don't-guess for the rest)
        for s in kept_shapes:
            if s["type"] != "rectangle":
                continue
            if bound_text(elements, s["id"]):
                continue
            note = classify_unlabeled_rect(elements, by_id, s, kept_shapes)
            unlabeled_notes.append(f"  id={s['id'][:8]} ({s['width']:.0f}x{s['height']:.0f}): {note}")

        # floating text -> nearest-arrow association by proximity
        associated_out = []
        standalone_out = []
        for t in loose_texts:
            tc = center(t)
            best, best_d = None, None
            for a in region_arrows:
                d = dist_to_arrow(tc, a)
                if best_d is None or d < best_d:
                    best, best_d = a, d
            content = t.get("text", "").strip()
            if best is not None and best_d <= LABEL_MAX_DIST:
                associated_out.append(
                    f"  \"{content}\"  -- likely labels arrow: {arrow_desc(elements, by_id, best)} "
                    f"(dist={best_d:.0f}px)"
                )
            else:
                standalone_out.append(f"  [text] {content}  (not confidently tied to any arrow)")

        if shapes_out:
            print(" Shapes:")
            print("\n".join(shapes_out))
        if unlabeled_notes:
            print(" Unlabeled-shape inference:")
            print("\n".join(unlabeled_notes))
        if associated_out:
            print(" Arrow labels (inferred by proximity):")
            print("\n".join(associated_out))
        if standalone_out:
            print(" Other floating text (position ambiguous -- ask if meaning matters):")
            print("\n".join(standalone_out))
        if arrows_out:
            print(" Connections:")
            print("\n".join(arrows_out))
        if not (shapes_out or standalone_out or associated_out or arrows_out):
            print("  (empty region)")
        print()

    print(f"Total distinct elements pulled: {len(seen_ids)}")


if __name__ == "__main__":
    main()
