#!/usr/bin/env python3
"""
QuizPoker Card Generator - Premium Design Edition.

Layout: 
- Side-by-side layout (Back + Front) for folding or double-processing.
- Card Size: 83.8 x 50.8 mm.
- DPI: 300.

Design:
- Modern, clean, pastel aesthetics.
- "Back" (Category Side): Full color with central logo placeholder.
- "Front" (Question Side): Clean white with minimal typography and colored accent.

Usage:
    python scripts/generate_cards_png.py --input data/questions.csv --outdir output/cards
"""

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont, ImageOps

# Try to import qrcode
try:
    import qrcode
    HAS_QRCODE = True
except ImportError:
    HAS_QRCODE = False
    print("Warning: qrcode module not found. Install with: pip install qrcode[pil]")


# ============================================================================
# CONSTANTS & CONFIG
# ============================================================================

# Dimensions
DPI = 600 # Increased from 300 for 2x resolution
MM_TO_PX = lambda mm: int(round(mm / 25.4 * DPI))

CARD_W_MM = 83.8
CARD_H_MM = 50.8
PAGE_W_MM = 210
PAGE_H_MM = 297

GRID_COLS = 2
GRID_ROWS = 5
GAP_MM = 0  # No gap for fold-over layout (or small gap if cutting separately)

# Colors (Pastel / Modern)
PALETTE = {
    "A": {"bg": "#9DBC79", "text": "#ffffff", "accent": "#5d7542"}, # Nature (Green)
    "B": {"bg": "#E5D9C4", "text": "#ffffff", "accent": "#8a7b62"}, # Culture (Beige)
    "C": {"bg": "#88C0E8", "text": "#ffffff", "accent": "#456f8f"}, # Tech (Blue)
    "default": {"bg": "#94a3b8", "text": "#ffffff", "accent": "#0f172a"},
}

COLOR_WHITE = "#ffffff"
COLOR_TEXT_MAIN = "#334155" # Slate 700
COLOR_TEXT_SUB = "#64748b"  # Slate 500
COLOR_QR_MAIN = "#334155"


# ============================================================================
# DATA
# ============================================================================

@dataclass
class CardData:
    id: str
    category: str
    subcategory: str
    question: str
    
    @property
    def cat_key(self) -> str:
        """Return 'A', 'B', or 'C'."""
        return self.category[0].upper() if self.category else "A"
    
    @property
    def theme(self) -> dict:
        return PALETTE.get(self.cat_key, PALETTE["default"])


# ============================================================================
# DRAWING HELPERS
# ============================================================================

def get_font(name: str, size_pt: float) -> ImageFont.FreeTypeFont:
    """Load font with fallback."""
    size_px = int(size_pt * DPI / 72)
    # List of preferred fonts (clean sans-serifs)
    candidates = [
        "HelveticaNeue-Bold.otf", "HelveticaNeue.ttc", 
        "Arial Bold.ttf", "Arial.ttf",
        "DejaVuSans-Bold.ttf", "DejaVuSans.ttf"
    ]
    
    # Try system paths
    search_paths = [
        Path("/System/Library/Fonts"),
        Path("/Library/Fonts"),
        Path("/usr/share/fonts"),
        Path("C:/Windows/Fonts"),
        Path("."),
    ]
    
    for fname in candidates:
        for folder in search_paths:
            fpath = folder / fname
            # Handle TTC collections (index 0)
            try:
                return ImageFont.truetype(str(fpath), size_px)
            except OSError:
                continue
    
    return ImageFont.load_default() # Fallback


def draw_wrapped_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    box: Tuple[int, int, int, int], # (x, y, w, h)
    color: str,
    align: str = "center",
    valign: str = "center"
) -> None:
    """Draw text wrapped within a box."""
    x, y, w, h = box
    words = text.split()
    lines = []
    line = []
    
    # Simple wrapping
    for word in words:
        test_line = " ".join(line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        if (bbox[2] - bbox[0]) <= w:
            line.append(word)
        else:
            if line: lines.append(" ".join(line))
            line = [word]
    if line: lines.append(" ".join(line))
    
    # Calculate total text height
    line_spacing = 1.2
    # Get rough line height from font metrics
    ascent, descent = font.getmetrics()
    line_h = (ascent + descent) * line_spacing
    total_h = len(lines) * line_h
    
    # Vertical alignment start Y
    current_y = y
    if valign == "center":
        current_y += (h - total_h) / 2
    elif valign == "bottom":
        current_y += h - total_h
    
    # Draw lines
    for l in lines:
        bbox = draw.textbbox((0, 0), l, font=font)
        lw = bbox[2] - bbox[0]
        
        lx = x
        if align == "center":
            lx += (w - lw) / 2
        elif align == "right":
            lx += w - lw
            
        draw.text((lx, current_y), l, font=font, fill=color)
        current_y += line_h


def load_category_icon(category_key: str, size_px: int) -> Image.Image:
    """Load and resize the category icon from png files."""
    icon_map = {
        "A": "icons/nature_icon.png",
        "B": "icons/culture_icon.png",
        "C": "icons/tech_icon.png"
    }
    
    path = icon_map.get(category_key)
    if not path or not Path(path).exists():
        # Fallback to empty transparent image if file missing
        print(f"Warning: Icon not found for category {category_key} at {path}")
        return Image.new("RGBA", (size_px, size_px), (0,0,0,0))
        
    try:
        with Image.open(path) as img:
            # Maintain aspect ratio
            img = img.convert("RGBA")
            aspect = img.width / img.height
            
            if aspect > 1: # Wide
                new_w = size_px
                new_h = int(size_px / aspect)
            else: # Tall or square
                new_h = size_px
                new_w = int(size_px * aspect)
                
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
            
            # Center in the square box
            final = Image.new("RGBA", (size_px, size_px), (0,0,0,0))
            offset_x = (size_px - new_w) // 2
            offset_y = (size_px - new_h) // 2
            final.paste(img, (offset_x, offset_y), img)
            return final
    except Exception as e:
        print(f"Error loading icon {path}: {e}")
        return Image.new("RGBA", (size_px, size_px), (0,0,0,0))


# ============================================================================
# RENDER FUNCTIONS
# ============================================================================

def draw_rounded_hexagon(
    img: Image.Image,
    center: Tuple[int, int],
    radius: float,
    color: Tuple[int, int, int, int],
    thickness: int,
    corner_radius: float = 0
) -> None:
    """
    Draw a hexagon with rounded corners and proper alpha blending.
    Uses 4x supersampling for smooth antialiased edges.
    Rotation: Flat top (edges at top/bottom).
    """
    w, h = img.size
    scale = 4  # Supersampling factor
    
    # Create high-res transparent overlay
    overlay = Image.new("RGBA", (w * scale, h * scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)
    
    cx, cy = center[0] * scale, center[1] * scale
    r = radius * scale
    thick = max(1, int(thickness * scale))
    corner_r = corner_radius * scale
    
    # Calculate hexagon vertices (Pointy Top: 30, 90, 150...)
    # 30 deg is Bottom-Right (or Top-Right depending on coord system). 
    # In PIL (y down):
    # 0 is Right. 90 is Bottom. 
    # 30 is Bottom-Rightish.
    # Actually standard pointy top starts at -90 (Top) or 30 (Bottom Right vertex).
    # Let's use 30 offset to align with standard pointy top icon.
    
    vertices = []
    for i in range(6):
        angle_deg = 30 + (60 * i) 
        angle_rad = math.radians(angle_deg)
        x = cx + math.cos(angle_rad) * r
        y = cy + math.sin(angle_rad) * r
        vertices.append((x, y))
    
    full_path_points = []
    
    # Generate path with rounded corners (Quadratic Bezier approximation)
    steps_per_corner = 15
    
    for i in range(6):
        v = vertices[i]
        v_prev = vertices[(i - 1) % 6]
        v_next = vertices[(i + 1) % 6]
        
        # Vectors to neighbors
        dx_prev = v_prev[0] - v[0]
        dy_prev = v_prev[1] - v[1]
        len_prev = math.sqrt(dx_prev**2 + dy_prev**2)
        
        dx_next = v_next[0] - v[0]
        dy_next = v_next[1] - v[1]
        len_next = math.sqrt(dx_next**2 + dy_next**2)
        
        # Clamp corner radius to half edge length to avoid overlap
        limit = min(len_prev, len_next) / 2
        actual_r = min(corner_r, limit)
        
        # Start and End points of the curve at this corner
        # P_start is on the edge coming FROM prev
        p_start = (
            v[0] + (dx_prev / len_prev) * actual_r,
            v[1] + (dy_prev / len_prev) * actual_r
        )
        
        # P_end is on the edge going TO next
        p_end = (
            v[0] + (dx_next / len_next) * actual_r,
            v[1] + (dy_next / len_next) * actual_r
        )
        
        # If this is not the very first point, add line from previous corner's end
        # (This happens naturally if we just append points, but we need to handle the loop closing)
        
        # Generate curve points (Quadratic Bezier: P0 -> Control(v) -> P2)
        # B(t) = (1-t)^2 * P0 + 2(1-t)t * P1 + t^2 * P2
        for s in range(steps_per_corner + 1):
            t = s / steps_per_corner
            bx = (1-t)**2 * p_start[0] + 2*(1-t)*t * v[0] + t**2 * p_end[0]
            by = (1-t)**2 * p_start[1] + 2*(1-t)*t * v[1] + t**2 * p_end[1]
            full_path_points.append((bx, by))

    # Close the loop
    # The list now contains [Curve0_points, Curve1_points, ...]
    # The line between Curve0_End and Curve1_Start is implied by drawing sequence
    full_path_points.append(full_path_points[0])
    
    # Draw the continuous smooth path
    draw.line(full_path_points, fill=color, width=thick, joint="curve")
    
    # Downscale
    overlay = overlay.resize((w, h), Image.Resampling.LANCZOS)
    img.alpha_composite(overlay)


def hex_color_to_rgba(hex_code: str, opacity: float) -> tuple:
    """Convert #RRGGBB to (r, g, b, a)."""
    hex_code = hex_code.lstrip("#")
    r = int(hex_code[0:2], 16)
    g = int(hex_code[2:4], 16)
    b = int(hex_code[4:6], 16)
    a = int(255 * opacity)
    return (r, g, b, a)


def adjust_color_brightness(hex_color: str, factor: float) -> str:
    """Adjust brightness of a hex color. factor < 1 darkens, > 1 lightens."""
    r, g, b, a = hex_color_to_rgba(hex_color, 1.0)
    
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    
    return f"#{r:02x}{g:02x}{b:02x}"


def render_card_back(card: CardData, w: int, h: int) -> Image.Image:
    """Render the BACK side (Category + Logo)."""
    # Start with white RGBA for alpha compositing
    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    
    # Shift center up to make room for text at bottom
    shift_y = MM_TO_PX(5) 
    cx, cy = int(w / 2), int(h / 2) - shift_y
    
    # 1. Icon (draw first, hexagons go around it)
    icon_size = int(h * 0.58) # Increased by ~10% (from 0.52)
    icon = load_category_icon(card.cat_key, icon_size)
    
    # Paste icon centered using alpha composite
    icon_layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    icon_layer.paste(icon, (cx - icon_size//2, cy - icon_size//2))
    img.alpha_composite(icon_layer)
    
    # 2. Triple Hexagon Frame (fading outward)
    # Modified: Removed inner ring, kept middle and outer
    # Reduced base_radius slightly to avoid cutoff at top/bottom
    base_radius = int(icon_size * 0.52) # Reduced relative to icon (was 0.60)
    accent_hex = card.theme["bg"]
    
    spacing = MM_TO_PX(2.3)
    thickness = MM_TO_PX(1.0)
    corner_r = MM_TO_PX(1.5) 
    
    # Ring 1 (Middle - now inner-most visible) 50% opacity
    draw_rounded_hexagon(
        img, (cx, cy), 
        radius=base_radius + spacing, 
        color=hex_color_to_rgba(accent_hex, 0.5), 
        thickness=thickness,
        corner_radius=corner_r
    )
    
    # Ring 2 (Outer) 20% opacity
    draw_rounded_hexagon(
        img, (cx, cy), 
        radius=base_radius + spacing * 2, 
        color=hex_color_to_rgba(accent_hex, 0.2), 
        thickness=thickness,
        corner_radius=corner_r
    )
    
    # 3. Category Name (Bottom)
    draw = ImageDraw.Draw(img)
    font_cat = get_font("bold", 11) # Slightly larger/smaller? 11 is good balance.
    
    cat_text = card.subcategory.upper()
    
    # Calculate Y positions
    # Start drawing text below the outer ring
    outer_radius = base_radius + spacing * 2
    text_start_y = int(cy + outer_radius + MM_TO_PX(2)) # Reduced gap
    
    text_color = card.theme.get("accent", accent_hex)
    
    # Draw Subcategory as Main Title
    draw_wrapped_text(
        draw, cat_text, font_cat,
        (MM_TO_PX(2), text_start_y, w - MM_TO_PX(4), h - text_start_y),
        text_color, align="center", valign="top"
    )
    
    # 4. ID Removed
    
    return img.convert("RGB")


def render_card_front(card: CardData, w: int, h: int) -> Image.Image:
    """Render the FRONT side (Question + QR)."""
    # Use RGBA for layering
    img = Image.new("RGBA", (w, h), (255, 255, 255, 255))
    
    # 0. Background Color (Very faint accent color)
    accent_rgba = hex_color_to_rgba(card.theme["bg"], 0.08) # 8% opacity
    bg_layer = Image.new("RGBA", (w, h), accent_rgba)
    img.alpha_composite(bg_layer)
    
    draw = ImageDraw.Draw(img)
    
    # 1. Header Pill/Shape (Centered)
    # Style: Rounded Hexagon Pill (Hexagon with elongated center)
    # Or just a Hexagon stretched horizontally?
    
    header_w = w * 0.85 # 85% width
    header_h = MM_TO_PX(8)
    header_x = (w - header_w) / 2
    header_y = MM_TO_PX(4) # Spacing from top
    
    header_center = (w/2, header_y + header_h/2)
    accent_rgb = hex_color_to_rgba(card.theme["bg"], 1.0)
    
    # Draw a custom "Hex-Pill" shape
    # Left Point <--- Rect ---> Right Point
    # But user asked for "hexagon rounded hexagon shapes outwards left and right"
    # Let's try to draw a long rectangle with hexagon tips (pointy ends) but rounded?
    
    # Simpler and cleaner: A rounded rectangle (pill) is very modern. 
    # A "Hexagon Pill" would be:
    #   /---------\
    # <           >
    #   \---------/
    
    # Let's construct a path for this "Hex-Pill"
    # Points:
    # Left Tip (x, mid_y)
    # Top Left (x + h/2, y)
    # Top Right (x + w - h/2, y)
    # Right Tip (x + w, mid_y)
    # Bottom Right (x + w - h/2, y + h)
    # Bottom Left (x + h/2, y + h)
    
    x1, y1 = header_x, header_y
    x2, y2 = header_x + header_w, header_y + header_h
    mid_y = header_y + header_h / 2
    tip_width = header_h / 2 # 45 degree angle roughly
    
    # Vertices
    p_left_tip = (x1, mid_y)
    p_top_left = (x1 + tip_width, y1)
    p_top_right = (x2 - tip_width, y1)
    p_right_tip = (x2, mid_y)
    p_btm_right = (x2 - tip_width, y2)
    p_btm_left = (x1 + tip_width, y2)
    
    # Draw rounded rectangle (Pill)
    # Rectangle with full radius
    draw.rounded_rectangle(
        [header_x, header_y, header_x + header_w, header_y + header_h],
        radius=header_h / 2, # Full radius for pill shape
        fill=accent_rgb
    )
    
    # 2. Subcategory (Centered in Header Shape)
    font_sub = get_font("bold", 9) 
    text_color = "#FFFFFF" 
    
    sub_text = " ".join(list(card.subcategory.upper()))
    
    # Measure
    bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    
    # Center text visually in the shape
    # Shifted down slightly to be optically centered
    text_draw_y = header_y + (header_h - text_h) / 2 - MM_TO_PX(1) + MM_TO_PX(0.5) # Tweaked down
    
    draw.text(
        ((w - text_w) / 2, text_draw_y),
        sub_text,
        font=font_sub,
        fill=text_color
    )
    
    # 3. Question (Centered in main area)
    font_q = get_font("bold", 12) 
    
    margin = MM_TO_PX(8)
    qr_area_size = MM_TO_PX(10) # Reduced from 12mm to 10mm
    
    q_w = w - (margin * 2)
    top_margin = header_y + header_h + MM_TO_PX(3) # Reduced gap
    q_h = h - top_margin - margin - MM_TO_PX(4) # Reduced height significantly to avoid QR
    
    draw_wrapped_text(
        draw, card.question, font_q,
        (margin, top_margin, q_w, q_h),
        COLOR_TEXT_MAIN, align="center", valign="center"
    )
    
    # 4. QR Code (Bottom Right)
    if HAS_QRCODE:
        # Generate Dark Accent Color for QR
        qr_color = adjust_color_brightness(card.theme["bg"], 0.4) # 40% brightness of accent
        
        qr = qrcode.QRCode(box_size=10, border=0)
        qr.add_data(card.id) 
        qr.make(fit=True)
        # Use white back for reliability
        qr_img = qr.make_image(fill_color=qr_color, back_color="white") 
        qr_img = qr_img.resize((qr_area_size, qr_area_size), Image.Resampling.LANCZOS)
        
        qr_x = w - qr_area_size - MM_TO_PX(3)
        qr_y = h - qr_area_size - MM_TO_PX(3)
        img.paste(qr_img, (qr_x, qr_y))
    
    # 5. ID (Bottom Left)
    font_id = get_font("regular", 7)
    draw.text(
        (MM_TO_PX(4), h - MM_TO_PX(5)),
        f"#{card.id}",
        font=font_id,
        fill=COLOR_TEXT_SUB
    )
    
    return img.convert("RGB")


def render_page(cards: List[CardData]) -> Image.Image:
    """Render a full A4 sheet."""
    page_w_px = MM_TO_PX(PAGE_W_MM)
    page_h_px = MM_TO_PX(PAGE_H_MM)
    
    img = Image.new("RGB", (page_w_px, page_h_px), COLOR_WHITE)
    
    # Calculate geometry
    card_w_px = MM_TO_PX(CARD_W_MM)
    card_h_px = MM_TO_PX(CARD_H_MM)
    gap_px = MM_TO_PX(GAP_MM)
    
    # Grid margins (center on page)
    grid_w = (card_w_px * 2) + gap_px
    grid_h = (card_h_px * GRID_ROWS)
    margin_x = (page_w_px - grid_w) // 2
    margin_y = (page_h_px - grid_h) // 2
    
    for idx, card in enumerate(cards):
        if idx >= GRID_ROWS: break
        
        y = margin_y + (idx * card_h_px)
        
        # Left: Back (Category)
        back_img = render_card_back(card, card_w_px, card_h_px)
        img.paste(back_img, (margin_x, y))
        
        # Right: Front (Question)
        front_img = render_card_front(card, card_w_px, card_h_px)
        img.paste(front_img, (margin_x + card_w_px + gap_px, y))
        
        # Optional: Cut lines (very subtle gray dots)
        # ... skipped for cleaner look, edges serve as cut lines
        
    return img


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/questions.csv", type=Path)
    parser.add_argument("--outdir", default="output/cards", type=Path)
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    args = parser.parse_args()
    
    # Read CSV
    cards = []
    with args.input.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = int(row["id"])
            if args.start and cid < args.start: continue
            if args.end and cid > args.end: continue
            
            cards.append(CardData(
                id=row["id"],
                category=row["kategorie"],
                subcategory=row["subkategorie"],
                question=row["frage"]
            ))
            
    print(f"Loaded {len(cards)} cards.")
    args.outdir.mkdir(parents=True, exist_ok=True)
    
    # Process batches of 5 (one page)
    batch_size = 5
    total_pages = math.ceil(len(cards) / batch_size)
    
    for i in range(0, len(cards), batch_size):
        batch = cards[i : i + batch_size]
        page_num = (i // batch_size) + 1
        
        print(f"Rendering page {page_num}/{total_pages}...")
        img = render_page(batch)
        img.save(args.outdir / f"page_{page_num:03d}.png", dpi=(DPI, DPI))
        
    print(f"Done! {total_pages} sheets generated in {args.outdir}")


if __name__ == "__main__":
    main()
