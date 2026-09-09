"""Render a reference graph spec (from solver/functions._build_graph) to a PNG
image using Pillow.  No matplotlib needed — just lines, curves, and text."""
import io
import math

from PIL import Image, ImageDraw, ImageFont

# Layout constants
IMG_W, IMG_H = 640, 480
MARGIN = 48
AXIS_COLOR = (120, 120, 120)
CURVE_COLOR = (30, 100, 200)
ASYM_COLOR = (200, 60, 60)
TANGENT_COLOR = (40, 180, 80)
POINT_COLOR = (200, 120, 0)
BG_COLOR = (255, 255, 255)
GRID_COLOR = (235, 235, 230)
LABEL_COLOR = (60, 60, 60)


def _get_font(size: int):
    """Try to load a monospace font; fall back to default."""
    for path in [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "C:\\Windows\\Fonts\\arial.ttf",
    ]:
        try:
            return ImageFont.truetype(path, size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def render_reference_graph(graph: dict, function_expr: str = "") -> bytes:
    """Render the reference graph to PNG bytes.

    Parameters
    ----------
    graph : dict
        The graph spec from ``_build_graph``:
        ``{x_min, x_max, y_min, y_max, curve, vertical_asymptotes, tangent, points}``
    function_expr : str
        The function expression string (for the title).

    Returns
    -------
    bytes
        PNG image data.
    """
    img = Image.new("RGB", (IMG_W, IMG_H), BG_COLOR)
    draw = ImageDraw.Draw(img)
    font = _get_font(13)
    font_sm = _get_font(11)
    font_title = _get_font(15)

    x_min = graph.get("x_min", -6)
    x_max = graph.get("x_max", 6)
    y_min = graph.get("y_min", -6)
    y_max = graph.get("y_max", 6)

    plot_w = IMG_W - 2 * MARGIN
    plot_h = IMG_H - 2 * MARGIN

    def to_px(xv, yv):
        px = MARGIN + (xv - x_min) / (x_max - x_min) * plot_w
        py = MARGIN + (y_max - yv) / (y_max - y_min) * plot_h
        return px, py

    # Light grid
    for gx in range(int(math.ceil(x_min)), int(math.floor(x_max)) + 1):
        if gx == 0:
            continue
        px, _ = to_px(gx, 0)
        draw.line([(px, MARGIN), (px, IMG_H - MARGIN)], fill=GRID_COLOR, width=1)
    for gy in range(int(math.ceil(y_min)), int(math.floor(y_max)) + 1):
        if gy == 0:
            continue
        _, py = to_px(0, gy)
        draw.line([(MARGIN, py), (IMG_W - MARGIN, py)], fill=GRID_COLOR, width=1)

    # Axes
    ox, oy = to_px(0, 0)
    # x-axis
    draw.line([(MARGIN, oy), (IMG_W - MARGIN, oy)], fill=AXIS_COLOR, width=2)
    # y-axis
    draw.line([(ox, MARGIN), (ox, IMG_H - MARGIN)], fill=AXIS_COLOR, width=2)
    # Axis labels at edges
    draw.text((IMG_W - MARGIN + 4, oy - 7), "x", fill=AXIS_COLOR, font=font_sm)
    draw.text((ox + 4, MARGIN - 14), "y", fill=AXIS_COLOR, font=font_sm)

    # Tick labels
    step = max(1, int((x_max - x_min) / 10))
    for gx in range(int(math.ceil(x_min)), int(math.floor(x_max)) + 1, step):
        if gx == 0:
            continue
        px, py = to_px(gx, 0)
        draw.text((px - 5, oy + 4), str(gx), fill=AXIS_COLOR, font=font_sm)
    step = max(1, int((y_max - y_min) / 8))
    for gy in range(int(math.ceil(y_min)), int(math.floor(y_max)) + 1, step):
        if gy == 0:
            continue
        px, py = to_px(0, gy)
        draw.text((ox - 20, py - 6), str(gy), fill=AXIS_COLOR, font=font_sm)

    # Vertical asymptotes (dashed)
    for xv in graph.get("vertical_asymptotes", []):
        px, _ = to_px(xv, 0)
        dash_len = 8
        gap = 5
        y = MARGIN
        while y < IMG_H - MARGIN:
            draw.line([(px, y), (px, min(y + dash_len, IMG_H - MARGIN))], fill=ASYM_COLOR, width=1)
            y += dash_len + gap
        draw.text((px + 3, MARGIN + 2), f"x={xv:g}", fill=ASYM_COLOR, font=font_sm)

    # Oblique / horizontal asymptote lines (dashed)
    for al in graph.get("asymptote_lines", []):
        pts = al.get("points") or []
        if len(pts) != 2:
            continue
        p1 = to_px(pts[0][0], pts[0][1])
        p2 = to_px(pts[1][0], pts[1][1])
        dash_len = 8
        gap = 5
        # Dashed line between the two points
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = (dx * dx + dy * dy) ** 0.5
        if length == 0:
            continue
        ux, uy = dx / length, dy / length
        step = dash_len + gap
        t = 0.0
        while t < length:
            x1 = p1[0] + ux * t
            y1 = p1[1] + uy * t
            x2 = p1[0] + ux * min(t + dash_len, length)
            y2 = p1[1] + uy * min(t + dash_len, length)
            draw.line([(x1, y1), (x2, y2)], fill=ASYM_COLOR, width=1)
            t += step
        label = al.get("label", "y = ...")
        mx = (p1[0] + p2[0]) / 2
        my = (p1[1] + p2[1]) / 2
        draw.text((mx + 4, my - 14), label, fill=ASYM_COLOR, font=font_sm)

    # Curve segments
    for seg in graph.get("curve", []):
        if len(seg) < 2:
            continue
        coords = [to_px(p[0], p[1]) for p in seg]
        # Draw as polyline
        for i in range(len(coords) - 1):
            draw.line([coords[i], coords[i + 1]], fill=CURVE_COLOR, width=2)

    # Tangent lines
    tangents = graph.get("tangents") or ([graph["tangent"]] if graph.get("tangent") else [])
    for tangent in tangents:
        if len(tangent) != 2:
            continue
        p1 = to_px(tangent[0][0], tangent[0][1])
        p2 = to_px(tangent[1][0], tangent[1][1])
        draw.line([p1, p2], fill=TANGENT_COLOR, width=2)
        # Small label at midpoint
        mx = (tangent[0][0] + tangent[1][0]) / 2
        my = (tangent[0][1] + tangent[1][1]) / 2
        mpx, mpy = to_px(mx, my)
        draw.text((mpx + 4, mpy - 14), "T", fill=TANGENT_COLOR, font=font_sm)

    # Labeled points
    for pt in graph.get("points", []):
        px, py = to_px(pt["x"], pt["y"])
        r = 4
        draw.ellipse([px - r, py - r, px + r, py + r], fill=POINT_COLOR)
        label = pt.get("label", "")
        if label:
            draw.text((px + 7, py - 7), label, fill=POINT_COLOR, font=font)

    # Title
    if function_expr:
        title = f"Reference: {function_expr}"
        draw.text((MARGIN, 4), title, fill=LABEL_COLOR, font=font_title)

    # Legend
    legend_y = IMG_H - MARGIN + 8
    items = [
        (CURVE_COLOR, "Curve"),
        (ASYM_COLOR, "Asymptote"),
        (TANGENT_COLOR, "Tangent"),
        (POINT_COLOR, "Points"),
    ]
    lx = MARGIN
    for color, label in items:
        draw.rectangle([lx, legend_y, lx + 12, legend_y + 10], fill=color)
        draw.text((lx + 16, legend_y - 1), label, fill=LABEL_COLOR, font=font_sm)
        lx += 80

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
