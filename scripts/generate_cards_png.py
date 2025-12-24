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

try:
    from tqdm import tqdm
    HAS_TQDM = True
except ImportError:
    HAS_TQDM = False

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
GAP_MM = 5.0  # 5mm gap between columns for cutting/bleed

# Colors (Pastel / Modern)
PALETTE = {
    "A": {"bg": "#9DBC79", "text": "#ffffff", "accent": "#5d7542"}, # Nature (Green)
    "B": {"bg": "#E5D9C4", "text": "#ffffff", "accent": "#8a7b62"}, # Culture (Beige)
    "C": {"bg": "#88C0E8", "text": "#ffffff", "accent": "#456f8f"}, # Tech (Blue)
    "default": {"bg": "#94a3b8", "text": "#ffffff", "accent": "#0f172a"},
}

COLOR_WHITE = "#ffffff"
COLOR_TEXT_MAIN = "#2d2d2d" # Dark Neutral Gray (no saturation)
COLOR_TEXT_SUB = "#666666"  # Medium Neutral Gray
COLOR_QR_MAIN = "#2d2d2d"


# Web App URL for QR codes
WEB_APP_URL = "https://derhansvader.github.io/QuizPoker"


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
        # System UI Font style
        "SanFranciscoDisplay-Bold.otf", "SF-Pro-Display-Bold.otf",
        "HelveticaNeue-Bold.otf", "HelveticaNeue.ttc", 
        "Roboto-Bold.ttf", "Roboto.ttf",
        "SegoeUI-Bold.ttf", "SegoeUI.ttf",
        "Arial Bold.ttf", "Arial.ttf"
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
    # Added ~1% of card height (h) to the top margin by reducing shift_y
    shift_y = MM_TO_PX(5) - int(h * 0.01)
    cx, cy = int(w / 2), int(h / 2) - shift_y
    
    # 1. Icon (draw first, hexagons go around it)
    # Reduced by 10% (from 0.58 to 0.522)
    icon_size = int(h * 0.522) 
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
    """
    Render the FRONT side - Compact Corner Accent Design.
    Safe margins: Top & Left (for printing).
    Accent: Small corner tab (top-left).
    QR: Bottom-right, compact.
    """
    img = Image.new("RGBA", (w, h), "#FFFFFF")
    draw = ImageDraw.Draw(img)
    
    accent_hex = card.theme["bg"]
    accent_rgb = hex_color_to_rgba(accent_hex, 1.0)
    dark_accent = card.theme.get("accent", accent_hex)
    
    # --- Safe Margins (for printing) ---
    safe_top = MM_TO_PX(4)
    safe_left = MM_TO_PX(4)
    safe_right = MM_TO_PX(3) # Smaller, as right edge is less critical
    safe_bottom = MM_TO_PX(3)
    
    # --- 0. Background Wash (Soft Tint) ---
    # User requested 100% white background
    img = Image.new("RGBA", (w, h), "#FFFFFF")
    draw = ImageDraw.Draw(img)

    # --- 1. Soft Corner Tab (Top-Left) ---
    # Fully rounded pill shape
    tab_h = MM_TO_PX(5.5)
    tab_padding_x = MM_TO_PX(3.5)
    
    font_sub = get_font("bold", 7)
    sub_text = card.subcategory.upper()
    bbox = draw.textbbox((0, 0), sub_text, font=font_sub)
    text_w = bbox[2] - bbox[0]
    
    tab_w = text_w + (tab_padding_x * 2)
    tab_x = safe_left
    tab_y = safe_top
    
    # Draw Tab (Soft Pill)
    draw.rounded_rectangle(
        [tab_x, tab_y, tab_x + tab_w, tab_y + tab_h],
        radius=tab_h / 2, # Fully rounded
        fill=accent_rgb
    )
    
    # Tab Text (White on Accent)
    # Optically centered
    text_draw_y = tab_y + (tab_h - (bbox[3] - bbox[1])) / 2 - MM_TO_PX(0.2)
    draw.text(
        (tab_x + tab_padding_x, text_draw_y),
        sub_text,
        font=font_sub,
        fill="#FFFFFF"
    )
    
    # --- 2. Question (Main Content) ---
    # Elegant, large, slightly lighter weight if possible, otherwise standard bold
    # We'll stick to bold for readability but ensure good spacing
    font_q = get_font("bold", 13.5)
    
    q_x = safe_left
    q_y = tab_y + tab_h + MM_TO_PX(5) # More breathing room below tab
    q_w = w - safe_left - safe_right
    
    # Reserve space for QR area at bottom
    qr_size = MM_TO_PX(10)
    q_h = h - q_y - qr_size - MM_TO_PX(5) 
    
    draw_wrapped_text(
        draw, card.question, font_q,
        (q_x, q_y, q_w, q_h),
        COLOR_TEXT_MAIN, # Dark Grey #2d2d2d
        align="left",   
        valign="center"
    )
    
    # --- 3. Bottom Row: ID (left) + QR (right) ---
    row_y = h - safe_bottom - qr_size
    
    # ID (Bottom Left)
    # Use Dark Accent Color for ID to tie it together
    font_id = get_font("bold", 8)
    id_text = f"#{card.id}"
    
    # Vertical divider line next to ID? No, keep it clean.
    # Just align with left margin.
    draw.text((safe_left, row_y + qr_size / 2 - MM_TO_PX(1.5)), id_text, font=font_id, fill=dark_accent)
    
    # QR Code (Bottom Right)
    if HAS_QRCODE:
        qr_x = w - safe_right - qr_size
        qr_y = row_y
        
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10, 
            border=0
        )
        qr.add_data(f"{WEB_APP_URL}?q={card.id}") 
        qr.make(fit=True)
        
        # Tinted QR Code (Dark Accent on Transparent/Tinted BG)
        qr_img = qr.make_image(fill_color=dark_accent, back_color="transparent")
        qr_img = qr_img.resize((qr_size, qr_size), Image.Resampling.LANCZOS)
        img.paste(qr_img, (int(qr_x), int(qr_y)), qr_img)

    return img.convert("RGB")


def draw_print_purge_strip(draw, w, total_h, spot_colors, y_offset=0):
    """Draw a CMYK + Spot color purge strip. Weighted heights."""
    # Define colors and their relative weights
    # C, M, Y get 0.5 weight, K and Spots get 1.0 weight
    weighted_colors = [
        ("#00FFFF", 0.5), # Cyan
        ("#FF00FF", 0.5), # Magenta
        ("#FFFF00", 0.5), # Yellow
        ("#000000", 1.0), # Black
    ] + [(c, 1.0) for c in spot_colors]
    
    total_weight = sum(wgt for col, wgt in weighted_colors)
    unit_h = total_h / total_weight
    
    current_y = y_offset
    for color, weight in weighted_colors:
        h_bar = weight * unit_h
        draw.rectangle([0, current_y, w, current_y + h_bar], fill=color)
        current_y += h_bar

def render_page(cards: List[CardData]) -> Image.Image:
    """Render a full A4 sheet with center bleed."""
    page_w_px = MM_TO_PX(PAGE_W_MM)
    page_h_px = MM_TO_PX(PAGE_H_MM)
    
    img = Image.new("RGB", (page_w_px, page_h_px), COLOR_WHITE)
    draw = ImageDraw.Draw(img)
    
    # --- Purge Strips (Top & Bottom 16mm) ---
    # Helps clean print heads before and after main content
    page_spot_colors = list(dict.fromkeys([c.theme["bg"] for c in cards]))
    strip_h_px = MM_TO_PX(16)
    
    # Top
    draw_print_purge_strip(draw, page_w_px, strip_h_px, page_spot_colors, y_offset=0)
    # Bottom
    draw_print_purge_strip(draw, page_w_px, strip_h_px, page_spot_colors, y_offset=page_h_px - strip_h_px)
    
    # Calculate geometry
    card_w_px = MM_TO_PX(CARD_W_MM)
    card_h_px = MM_TO_PX(CARD_H_MM)
    gap_px = MM_TO_PX(GAP_MM) # 5mm gap
    bleed_px = int(gap_px / 2) # 2.5mm bleed fill
    
    # Grid margins (center on page)
    grid_w = (card_w_px * 2) + gap_px
    grid_h = (card_h_px * GRID_ROWS)
    margin_x = (page_w_px - grid_w) // 2
    margin_y = (page_h_px - grid_h) // 2
    
    for idx, card in enumerate(cards):
        if idx >= GRID_ROWS: break
        
        y = margin_y + (idx * card_h_px)
        
        # Determine background color for bleed
        # Note: Back side is white-ish with hex patterns, but we might want to fill with white?
        # Actually, the user said "light green" (for category A), which implies they want the card's theme color.
        # But our current design uses white/off-white backgrounds.
        # IF the card background is tinted, we should use that tint.
        # The "Back" uses white with alpha composite hexes.
        # The "Front" uses a 3% tint.
        
        # Let's calculate that 3% tint color for the bleed
        accent_hex = card.theme["bg"]
        accent_rgb = hex_color_to_rgba(accent_hex, 1.0)
        
        # 3% Tint calculation (approximate to match the front side wash)
        # c_out = c_in * alpha + white * (1-alpha)
        # alpha = 0.03
        # User requested WHITE background, so bleed should also be WHITE
        tint_rgb = (255, 255, 255)
        
        # --- LEFT COLUMN (BACK) ---
        back_x = margin_x
        # 1. Draw Bleed to the Right of the card
        # (Fills the first half of the gap)
        draw.rectangle(
            [back_x + card_w_px, y, back_x + card_w_px + bleed_px + 1, y + card_h_px],
            fill=tint_rgb # Or white if back is white? Back is WHITE in current code.
        )
        # Render and paste card
        back_img = render_card_back(card, card_w_px, card_h_px)
        img.paste(back_img, (back_x, y))
        
        # --- RIGHT COLUMN (FRONT) ---
        front_x = margin_x + card_w_px + gap_px
        # 2. Draw Bleed to the Left of the card
        # (Fills the second half of the gap)
        draw.rectangle(
            [front_x - bleed_px - 1, y, front_x, y + card_h_px],
            fill=tint_rgb # Matches the front side tint
        )
        # Render and paste card
        front_img = render_card_front(card, card_w_px, card_h_px)
        img.paste(front_img, (front_x, y))
        
    # Convert to CMYK immediately before return to support "native printer language"
    # Note: PIL conversion is simple RGB->CMYK. For 100% K black text, 
    # the input black RGB(0,0,0) usually maps to rich black (mixed inks).
    # To strictly enforce K-only black for text, advanced channel manipulation would be needed,
    # but saving as CMYK PDF is the industry standard step for this workflow.
    return img.convert("CMYK")


# ============================================================================
# MAIN
# ============================================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="data/questions.csv", type=Path)
    parser.add_argument("--outdir", default="output/cards", type=Path)
    parser.add_argument("--start", type=int, default=None)
    parser.add_argument("--end", type=int, default=None)
    parser.add_argument("--ids", type=str, default=None, help="Comma-separated list of IDs to render (e.g. '1,2,5')")
    args = parser.parse_args()
    
    # Parse specific IDs if provided
    target_ids = []
    if args.ids:
        target_ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
    
    # Read CSV
    cards = []
    with args.input.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cid = int(row["id"])
            
            # Filtering logic
            if target_ids:
                if cid not in target_ids: continue
            else:
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
    
    generated_pages = []
    
    # Use tqdm for progress bar if available
    iterator = range(0, len(cards), batch_size)
    if HAS_TQDM:
        iterator = tqdm(iterator, total=total_pages, desc="Rendering Pages", unit="page")
    
    for i in iterator:
        batch = cards[i : i + batch_size]
        
        if not HAS_TQDM:
            page_num = (i // batch_size) + 1
            print(f"Rendering page {page_num}/{total_pages}...")
            
        img = render_page(batch)
        # Convert to CMYK and append to list
        # Revert to RGB to fix color muddiness. Printer RIP will handle conversion better.
        generated_pages.append(img.convert("RGB"))
        
    # Save all pages to a single PDF
    if generated_pages:
        output_file = args.outdir / "QuizPoker_Cards_All.pdf"
        print(f"Saving combined PDF to {output_file}...")
        generated_pages[0].save(
            output_file, 
            save_all=True, 
            append_images=generated_pages[1:], 
            resolution=DPI
        )
        
    print(f"Done! {total_pages} sheets generated in {args.outdir}")


if __name__ == "__main__":
    main()
