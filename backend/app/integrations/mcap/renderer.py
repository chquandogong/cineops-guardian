"""Renders MCAP telemetry into a frame the model can look at.

The agent otherwise reasons only over numbers. A misalignment between the dolly's
commanded path and the costmap it is avoiding is a *shape*, and shapes are what a
rig operator recognises at a glance in Foxglove. This draws that shape server-side
so Gemini can use vision on the same evidence, rather than being told about it.

Pure Pillow, no plotting stack: the container stays small and the output is
deterministic, which matters because the demo must reproduce offline.
"""

from __future__ import annotations

import io
from typing import Any

from PIL import Image, ImageDraw, ImageFont

BG = (7, 10, 15)
PANEL = (12, 16, 23)
GRID = (30, 41, 59)
INK = (226, 232, 240)
MUTED = (100, 116, 139)
CYAN = (34, 211, 238)
AMBER = (251, 191, 36)
RED = (248, 113, 113)
GREEN = (52, 211, 153)

W, H = 1280, 620
PAD = 56


def _font(size: int) -> ImageFont.ImageFont:
    """Scalable font without a system font dependency (python:slim ships none)."""
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # Pillow < 10.1: bitmap default only
        return ImageFont.load_default()


F_TITLE = _font(24)
F_BODY = _font(18)
F_LABEL = _font(16)
F_SMALL = _font(14)


def _text(d: ImageDraw.ImageDraw, xy, s, fill=INK, font=None, anchor=None) -> None:
    d.text(xy, s, fill=fill, font=font or F_BODY, anchor=anchor)


def _panel(d: ImageDraw.ImageDraw, box, title: str) -> None:
    d.rounded_rectangle(box, radius=10, fill=PANEL, outline=GRID, width=1)
    _text(d, (box[0] + 16, box[1] + 12), title, fill=MUTED, font=F_LABEL)


def render_spatial_evidence(channels: dict[str, Any]) -> bytes:
    """Draws a top-down path view plus TF and frame-rate strips. Returns PNG bytes."""
    odom = channels.get("odom") or []
    tf = channels.get("tf") or []
    costmap = channels.get("costmap") or []
    camera = channels.get("camera") or []

    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    _text(d, (PAD, 22), "Stage A · dolly-alpha-01 · MCAP spatial evidence", fill=INK, font=F_TITLE)
    _text(
        d,
        (PAD, 50),
        "Top-down dolly path vs costmap inflation, with TF Z-translation and camera frame rate",
        fill=MUTED,
        font=F_LABEL,
    )

    # ---------------------------------------------------------------- path
    path_box = (PAD, 78, PAD + 700, 78 + 470)
    _panel(d, path_box, "TOP-DOWN PATH  (x/y metres)")
    px0, py0, px1, py1 = path_box[0] + 40, path_box[1] + 44, path_box[2] - 20, path_box[3] - 34

    xs = [p["pose"]["position"]["x"] for p in odom if "pose" in p]
    ys = [p["pose"]["position"]["y"] for p in odom if "pose" in p]
    if not xs:
        xs, ys = [0.0], [0.0]
    xmin, xmax = min(xs) - 0.6, max(xs) + 0.6
    ymin, ymax = min(ys) - 1.2, max(ys) + 1.2
    if xmax - xmin < 1e-6:
        xmax = xmin + 1.0
    if ymax - ymin < 1e-6:
        ymax = ymin + 1.0

    def sx(x: float) -> float:
        return px0 + (x - xmin) / (xmax - xmin) * (px1 - px0)

    def sy(y: float) -> float:
        return py1 - (y - ymin) / (ymax - ymin) * (py1 - py0)

    for i in range(5):
        gx = px0 + i * (px1 - px0) / 4
        gy = py0 + i * (py1 - py0) / 4
        d.line([(gx, py0), (gx, py1)], fill=GRID, width=1)
        d.line([(px0, gy), (px1, gy)], fill=GRID, width=1)

    # phantom obstacle: the inflation the stale transform invents, drawn where the
    # dolly first started refusing to pass
    inflation = next((c for c in costmap if c.get("phantom_inflation_detected")), None)
    if inflation and len(xs) > 12:
        ox, oy = xs[min(14, len(xs) - 1)] + 0.9, ys[0]
        radius_m = float(inflation.get("inflation_radius_m", 0.45))
        rx = radius_m / (xmax - xmin) * (px1 - px0)
        ry = radius_m / (ymax - ymin) * (py1 - py0)
        d.ellipse(
            [sx(ox) - rx * 2.2, sy(oy) - ry * 2.2, sx(ox) + rx * 2.2, sy(oy) + ry * 2.2],
            outline=RED,
            width=2,
        )
        d.ellipse([sx(ox) - 5, sy(oy) - 5, sx(ox) + 5, sy(oy) + 5], fill=RED)
        # keep the callout inside the panel even when the marker sits near the edge
        label_x = sx(ox) + 16
        if label_x + 170 > px1:
            label_x = sx(ox) - 186
        label_y = sy(oy) - ry * 2.2 - 42
        _text(d, (label_x, label_y), "phantom obstacle", fill=RED, font=F_LABEL)
        _text(
            d,
            (label_x, label_y + 20),
            f"inflation r={radius_m:.2f} m",
            fill=MUTED,
            font=F_SMALL,
        )

    # the path itself: cyan while nominal, amber once it starts oscillating
    osc_from = next((i for i, p in enumerate(odom) if p.get("recovery_loop_active")), len(odom))
    pts = [(sx(x), sy(y)) for x, y in zip(xs, ys, strict=False)]
    if len(pts) > 1:
        d.line(pts[: max(osc_from, 1)], fill=CYAN, width=3)
        if osc_from < len(pts):
            d.line(pts[max(osc_from - 1, 0) :], fill=AMBER, width=3)
    for i, (x, y) in enumerate(pts):
        colour = AMBER if i >= osc_from else CYAN
        d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=colour)
    if pts:
        d.ellipse([pts[0][0] - 5, pts[0][1] - 5, pts[0][0] + 5, pts[0][1] + 5], fill=GREEN)
        _text(d, (pts[0][0] - 12, pts[0][1] + 10), "start", fill=MUTED, font=F_SMALL)

    _text(d, (px0, py1 + 10), f"x {xmin:.1f} to {xmax:.1f} m", fill=MUTED, font=F_SMALL)
    _text(d, (px1 - 250, py1 + 10), "cyan nominal · amber recovery loops", fill=MUTED, font=F_SMALL)

    # ------------------------------------------------------------ tf strip
    tf_box = (PAD + 720, 78, W - PAD, 78 + 225)
    _panel(d, tf_box, "TF Z-TRANSLATION  camera_optical_frame -> lidar_link")
    tz = [t["transform"]["translation"]["z"] for t in tf if "transform" in t]
    if tz:
        expected = 0.350
        lo, hi = min(min(tz), expected) - 0.01, max(max(tz), expected) + 0.01
        bx0, by0, bx1, by1 = tf_box[0] + 20, tf_box[1] + 46, tf_box[2] - 20, tf_box[3] - 40

        def ty(v: float) -> float:
            return by1 - (v - lo) / (hi - lo) * (by1 - by0)

        d.line([(bx0, ty(expected)), (bx1, ty(expected))], fill=GREEN, width=2)
        _text(d, (bx0, ty(expected) - 20), f"approved {expected:.3f} m", fill=GREEN, font=F_SMALL)
        step = (bx1 - bx0) / max(len(tz) - 1, 1)
        series = [(bx0 + i * step, ty(v)) for i, v in enumerate(tz)]
        d.line(series, fill=RED, width=3)
        drift = abs(tz[-1] - expected)
        _text(d, (bx0, by1 + 10), f"active {tz[-1]:.3f} m", fill=RED, font=F_LABEL)
        _text(d, (bx1 - 130, by1 + 10), f"drift +{drift * 1000:.0f} mm", fill=RED, font=F_LABEL)

    # -------------------------------------------------------- camera strip
    cam_box = (PAD + 720, 78 + 245, W - PAD, 78 + 470)
    _panel(d, cam_box, "CAMERA FRAME RATE")
    fps = [c.get("fps", 24.0) for c in camera]
    if fps:
        target = float(camera[0].get("target_fps", 24.0))
        lo, hi = min(min(fps), target) - 2, max(max(fps), target) + 2
        bx0, by0, bx1, by1 = cam_box[0] + 20, cam_box[1] + 46, cam_box[2] - 20, cam_box[3] - 40

        def fy(v: float) -> float:
            return by1 - (v - lo) / (hi - lo) * (by1 - by0)

        d.line([(bx0, fy(target)), (bx1, fy(target))], fill=GREEN, width=2)
        _text(d, (bx0, fy(target) - 20), f"target {target:.2f} fps", fill=GREEN, font=F_SMALL)
        step = (bx1 - bx0) / max(len(fps) - 1, 1)
        d.line([(bx0 + i * step, fy(v)) for i, v in enumerate(fps)], fill=AMBER, width=3)
        _text(d, (bx0, by1 + 10), f"min {min(fps):.2f} fps", fill=AMBER, font=F_LABEL)

    # ------------------------------------------------------------- footer
    _text(
        d,
        (PAD, H - 34),
        "Rendered from the ROS2 .mcap by CineOps Guardian · synthetic telemetry",
        fill=MUTED,
        font=F_SMALL,
    )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()


def render_comparison(incident: dict[str, Any], baseline: dict[str, Any]) -> bytes:
    """Draws the failing take beside a known-good take of the same rig.

    A measurement only becomes an anomaly next to a baseline. Stacking the two
    paths and the two TF traces on one canvas lets the model see whether the
    value it is about to blame actually differs from a take that finished
    cleanly — including the case where it does not.
    """
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    _text(d, (PAD, 22), "Failing take vs known-good baseline", fill=INK, font=F_TITLE)
    _text(
        d,
        (PAD, 50),
        "Same rig, same route. Anything identical in both panels is not the anomaly.",
        fill=MUTED,
        font=F_LABEL,
    )

    panel_w = (W - PAD * 2 - 24) // 2
    for column, (channels, title, accent) in enumerate(
        ((baseline, "BASELINE — take completed clean", GREEN), (incident, "FAILING TAKE", RED))
    ):
        bx = PAD + column * (panel_w + 24)
        box = (bx, 78, bx + panel_w, 78 + 330)
        _panel(d, box, title)
        d.line([(box[0] + 16, box[1] + 34), (box[0] + 16 + 190, box[1] + 34)], fill=accent, width=3)

        odom = channels.get("odom") or []
        xs = [o["pose"]["position"]["x"] for o in odom if "pose" in o]
        ys = [o["pose"]["position"]["y"] for o in odom if "pose" in o]
        if not xs:
            continue
        # both panels share one scale, otherwise the shapes are not comparable
        all_x = xs + [
            o["pose"]["position"]["x"] for o in (incident.get("odom") or []) if "pose" in o
        ]
        all_y = ys + [
            o["pose"]["position"]["y"] for o in (incident.get("odom") or []) if "pose" in o
        ]
        xmin, xmax = min(all_x) - 0.5, max(all_x) + 0.5
        ymin, ymax = min(all_y) - 1.0, max(all_y) + 1.0
        px0, py0 = box[0] + 24, box[1] + 56
        px1, py1 = box[2] - 20, box[3] - 24

        def sx(x: float, a=px0, b=px1, lo=xmin, hi=xmax) -> float:
            return a + (x - lo) / (hi - lo) * (b - a)

        def sy(y: float, a=py0, b=py1, lo=ymin, hi=ymax) -> float:
            return b - (y - lo) / (hi - lo) * (b - a)

        for i in range(4):
            gy = py0 + i * (py1 - py0) / 3
            d.line([(px0, gy), (px1, gy)], fill=GRID, width=1)

        osc_from = next((i for i, o in enumerate(odom) if o.get("recovery_loop_active")), len(odom))
        pts = [(sx(x), sy(y)) for x, y in zip(xs, ys, strict=False)]
        if len(pts) > 1:
            d.line(pts[: max(osc_from, 1)], fill=CYAN, width=3)
            if osc_from < len(pts):
                d.line(pts[max(osc_from - 1, 0) :], fill=AMBER, width=3)

        loops = sum(1 for o in odom if o.get("recovery_loop_active"))
        cam = channels.get("camera") or []
        min_fps = min((c.get("fps", 24.0) for c in cam), default=24.0)
        tf = channels.get("tf") or []
        tz = tf[-1]["transform"]["translation"]["z"] if tf else 0.0
        _text(
            d,
            (px0, py1 + 6),
            f"recovery loops {loops} · min {min_fps:.2f} fps · TF Z {tz:.3f} m",
            fill=MUTED,
            font=F_SMALL,
        )

    # ------------------------------------------------------- delta summary
    box = (PAD, 78 + 350, W - PAD, H - 56)
    _panel(d, box, "WHAT ACTUALLY DIFFERS")

    def stats(ch: dict[str, Any]) -> tuple[float, int, float]:
        tf = ch.get("tf") or []
        tz = tf[-1]["transform"]["translation"]["z"] if tf else 0.0
        loops = sum(1 for o in (ch.get("odom") or []) if o.get("recovery_loop_active"))
        cam = ch.get("camera") or []
        return tz, loops, min((c.get("fps", 24.0) for c in cam), default=24.0)

    b_tz, b_loops, b_fps = stats(baseline)
    i_tz, i_loops, i_fps = stats(incident)
    rows = [
        (
            "TF Z-translation",
            f"{b_tz:.3f} m",
            f"{i_tz:.3f} m",
            abs(i_tz - b_tz) > 1e-6,
            f"{(i_tz - b_tz) * 1000:+.0f} mm",
        ),
        (
            "Recovery loops",
            str(b_loops),
            str(i_loops),
            i_loops != b_loops,
            f"{i_loops - b_loops:+d}",
        ),
        (
            "Minimum frame rate",
            f"{b_fps:.2f} fps",
            f"{i_fps:.2f} fps",
            abs(i_fps - b_fps) > 1e-6,
            f"{i_fps - b_fps:+.2f} fps",
        ),
    ]
    y = box[1] + 46
    _text(d, (box[0] + 24, y), "metric", fill=MUTED, font=F_SMALL)
    _text(d, (box[0] + 300, y), "baseline", fill=MUTED, font=F_SMALL)
    _text(d, (box[0] + 470, y), "failing", fill=MUTED, font=F_SMALL)
    _text(d, (box[0] + 640, y), "delta", fill=MUTED, font=F_SMALL)
    y += 26
    for label, base, fail, differs, delta in rows:
        colour = RED if differs else MUTED
        _text(d, (box[0] + 24, y), label, fill=INK if differs else MUTED, font=F_BODY)
        _text(d, (box[0] + 300, y), base, fill=MUTED, font=F_BODY)
        _text(d, (box[0] + 470, y), fail, fill=colour, font=F_BODY)
        _text(d, (box[0] + 640, y), delta if differs else "identical", fill=colour, font=F_BODY)
        y += 30

    buffer = io.BytesIO()
    img.save(buffer, format="PNG", optimize=True)
    return buffer.getvalue()
