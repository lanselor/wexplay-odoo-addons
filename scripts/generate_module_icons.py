from __future__ import annotations

from pathlib import Path
from typing import Callable

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]

SIZE = 512
PADDING = 24
RADIUS = 74
PRIMARY = "#73C799"
SECONDARY = "#A68FCD"
WHITE = "#FFFFFF"
WHITE_SOFT = "#F6F4FB"
SHADOW = (61, 45, 89, 26)


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return tuple(int(value[i : i + 2], 16) for i in (0, 2, 4))


def make_gradient_background(size: int) -> Image.Image:
    start = hex_to_rgb(PRIMARY)
    end = hex_to_rgb(SECONDARY)
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    pixels = image.load()
    for y in range(size):
        for x in range(size):
            mix = ((x * 0.6) + (y * 0.4)) / ((size - 1) * 1.0)
            rgb = tuple(int(start[i] + (end[i] - start[i]) * mix) for i in range(3))
            pixels[x, y] = (*rgb, 255)
    return image


def rounded_mask(size: int, radius: int) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=radius, fill=255)
    return mask


def build_base_icon(size: int = SIZE) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    gradient = make_gradient_background(size)
    mask = rounded_mask(size, RADIUS)

    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow = Image.new("RGBA", (size, size), SHADOW)
    shadow_mask = rounded_mask(size, RADIUS)
    shadow_canvas = Image.new("RGBA", (size + 12, size + 18), (0, 0, 0, 0))
    shadow_canvas.paste(shadow, (6, 10), shadow_mask)
    canvas.alpha_composite(shadow_canvas.crop((0, 0, size, size)))
    canvas.paste(gradient, (0, 0), mask)

    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((0, 0, size - 1, size - 1), radius=RADIUS, outline=(255, 255, 255, 24), width=2)
    draw.arc((18, 22, 494, 500), start=212, end=342, fill=(255, 255, 255, 35), width=10)
    return canvas, draw


def line(draw: ImageDraw.ImageDraw, points: list[tuple[int, int]], width: int = 18, fill: str = WHITE) -> None:
    draw.line(points, fill=fill, width=width, joint="curve")


def rounded_rect(draw: ImageDraw.ImageDraw, box: tuple[int, int, int, int], radius: int, *, outline: str = WHITE, width: int = 16, fill=None) -> None:
    draw.rounded_rectangle(box, radius=radius, outline=outline, width=width, fill=fill)


def circle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, *, outline: str = WHITE, width: int = 14, fill=None) -> None:
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=outline, width=width, fill=fill)


def draw_printer(draw: ImageDraw.ImageDraw) -> None:
    rounded_rect(draw, (118, 180, 394, 342), 30, fill=WHITE)
    rounded_rect(draw, (156, 114, 356, 232), 18, outline=WHITE, width=14)
    rounded_rect(draw, (154, 276, 358, 398), 14, outline=WHITE_SOFT, width=14, fill=WHITE_SOFT)
    line(draw, [(188, 320), (324, 320)], width=12, fill=SECONDARY)
    line(draw, [(188, 352), (302, 352)], width=12, fill=SECONDARY)
    circle(draw, 348, 260, 10, fill=PRIMARY, outline=PRIMARY, width=1)


def draw_barcode(draw: ImageDraw.ImageDraw) -> None:
    rounded_rect(draw, (108, 126, 404, 386), 28, outline=WHITE, width=16)
    x = 154
    widths = [10, 18, 8, 14, 10, 22, 8, 16, 10, 14, 8, 20]
    heights = [160, 186, 144, 188, 168, 190, 150, 184, 156, 174, 146, 186]
    for bar_width, bar_height in zip(widths, heights):
        draw.rectangle((x, 176, x + bar_width, 176 + bar_height), fill=WHITE)
        x += bar_width + 8
    line(draw, [(150, 420), (362, 420)], width=14, fill=WHITE_SOFT)


def draw_browser(draw: ImageDraw.ImageDraw) -> None:
    rounded_rect(draw, (96, 116, 416, 366), 30, outline=WHITE, width=16)
    line(draw, [(124, 176), (388, 176)], width=12)
    for x in (140, 174, 208):
        circle(draw, x, 146, 10, fill=WHITE, outline=WHITE, width=1)


def draw_chat(draw: ImageDraw.ImageDraw, *, with_phone: bool = False) -> None:
    rounded_rect(draw, (116, 200, 346, 344), 30, outline=WHITE, width=16)
    line(draw, [(188, 344), (154, 388), (222, 348)], width=14)
    line(draw, [(154, 246), (304, 246)], width=12)
    line(draw, [(154, 286), (270, 286)], width=12)
    if with_phone:
        line(draw, [(278, 226), (304, 206), (336, 220), (328, 248), (348, 266), (324, 286), (294, 272), (276, 244)], width=16)


def draw_portal(draw: ImageDraw.ImageDraw, *, with_check: bool = False, with_chat: bool = False, with_phone: bool = False, with_chart: bool = False, with_knowledge: bool = False) -> None:
    draw_browser(draw)
    line(draw, [(194, 316), (194, 218), (248, 186), (318, 186), (318, 316)], width=16)
    line(draw, [(246, 184), (246, 316)], width=12)
    if with_check:
        circle(draw, 342, 324, 56, fill=WHITE, outline=WHITE, width=1)
        line(draw, [(314, 324), (334, 344), (372, 304)], width=16, fill=SECONDARY)
    if with_chat:
        rounded_rect(draw, (278, 230, 394, 312), 18, outline=WHITE_SOFT, width=12)
        line(draw, [(316, 312), (302, 338), (334, 314)], width=10, fill=WHITE_SOFT)
        if with_phone:
            line(draw, [(308, 252), (322, 240), (344, 248), (338, 268), (352, 282), (334, 294), (314, 286), (304, 266)], width=12, fill=WHITE_SOFT)
        else:
            line(draw, [(302, 256), (370, 256)], width=10, fill=WHITE_SOFT)
            line(draw, [(302, 284), (354, 284)], width=10, fill=WHITE_SOFT)
    if with_chart:
        line(draw, [(136, 326), (170, 290), (212, 320), (250, 258)], width=14)
        circle(draw, 250, 258, 10, fill=PRIMARY, outline=PRIMARY, width=1)
        line(draw, [(136, 224), (136, 326), (268, 326)], width=10)
    if with_knowledge:
        circle(draw, 352, 252, 38, outline=WHITE_SOFT, width=10)
        line(draw, [(352, 218), (352, 286)], width=10, fill=WHITE_SOFT)
        line(draw, [(320, 252), (384, 252)], width=10, fill=WHITE_SOFT)
        line(draw, [(336, 276), (352, 296), (368, 276)], width=10, fill=WHITE_SOFT)


def draw_knowledge(draw: ImageDraw.ImageDraw) -> None:
    line(draw, [(118, 166), (118, 360), (240, 342), (256, 338), (272, 342), (394, 360), (394, 166)], width=16)
    line(draw, [(256, 164), (256, 334)], width=12)
    line(draw, [(146, 196), (210, 196)], width=12)
    line(draw, [(302, 196), (366, 196)], width=12)
    circle(draw, 256, 160, 72, outline=WHITE, width=14)
    line(draw, [(228, 248), (246, 272), (256, 298), (266, 272), (284, 248)], width=14)
    line(draw, [(232, 314), (280, 314)], width=14)


def draw_image_frame(draw: ImageDraw.ImageDraw, with_wrench: bool = False) -> None:
    rounded_rect(draw, (116, 122, 396, 352), 28, outline=WHITE, width=16)
    circle(draw, 334, 186, 22, fill=WHITE, outline=WHITE, width=1)
    line(draw, [(150, 314), (218, 242), (274, 292), (334, 224), (364, 256)], width=16)
    if with_wrench:
        line(draw, [(246, 336), (320, 410)], width=18)
        line(draw, [(306, 350), (348, 308), (370, 330), (392, 308), (392, 270), (354, 270), (332, 292), (310, 270)], width=16)


def draw_gear(draw: ImageDraw.ImageDraw, *, with_wrench: bool = False, with_check: bool = False, with_flow: bool = False) -> None:
    center = (256, 256)
    outer = 132
    inner = 72
    for start in range(0, 360, 45):
        if start in (0, 180):
            box = (center[0] - 30, center[1] - outer, center[0] + 30, center[1] - outer + 58)
        elif start in (90, 270):
            box = (center[0] + (outer - 58 if start == 90 else -outer), center[1] - 30, center[0] + (outer if start == 90 else -outer + 58), center[1] + 30)
        else:
            offset_x = 78 if start in (45, 315) else -78
            offset_y = -78 if start in (45, 135) else 78
            box = (center[0] + offset_x - 28, center[1] + offset_y - 28, center[0] + offset_x + 28, center[1] + offset_y + 28)
        rounded_rect(draw, box, 10, fill=WHITE, outline=WHITE, width=1)
    circle(draw, center[0], center[1], outer - 28, outline=WHITE, width=18)
    circle(draw, center[0], center[1], inner, outline=WHITE, width=18)

    if with_wrench:
        line(draw, [(178, 332), (332, 178)], width=22)
        line(draw, [(300, 170), (334, 136), (366, 168), (350, 186), (376, 212), (404, 190)], width=18)
        circle(draw, 168, 344, 14, outline=WHITE, width=12)
        circle(draw, 344, 168, 18, fill=PRIMARY, outline=PRIMARY, width=1)
    elif with_check:
        line(draw, [(184, 270), (232, 318), (328, 214)], width=22)
    elif with_flow:
        circle(draw, 174, 200, 24, fill=WHITE, outline=WHITE, width=1)
        circle(draw, 344, 170, 24, fill=PRIMARY, outline=PRIMARY, width=1)
        circle(draw, 338, 336, 24, fill=WHITE_SOFT, outline=WHITE_SOFT, width=1)
        line(draw, [(202, 198), (316, 176)], width=14)
        line(draw, [(344, 202), (338, 304)], width=14)
        line(draw, [(314, 326), (204, 224)], width=14)
        line(draw, [(304, 166), (316, 176), (304, 186)], width=10, fill=WHITE)
        line(draw, [(330, 294), (338, 304), (346, 294)], width=10, fill=WHITE)
        line(draw, [(214, 214), (204, 224), (218, 226)], width=10, fill=WHITE)


def draw_shield(draw: ImageDraw.ImageDraw, with_check: bool = True) -> None:
    line(draw, [(256, 112), (366, 152), (366, 252), (350, 336), (256, 406), (162, 336), (146, 252), (146, 152), (256, 112)], width=16)
    if with_check:
        line(draw, [(194, 252), (236, 294), (320, 210)], width=20, fill=PRIMARY)
        circle(draw, 256, 252, 40, outline=WHITE_SOFT, width=10)


def draw_document(draw: ImageDraw.ImageDraw, *, signed: bool = False, printer: bool = False) -> None:
    rounded_rect(draw, (146, 104, 366, 404), 24, outline=WHITE, width=16)
    line(draw, [(194, 186), (318, 186)], width=12)
    line(draw, [(194, 232), (318, 232)], width=12)
    line(draw, [(194, 278), (302, 278)], width=12)
    if signed:
        line(draw, [(196, 342), (228, 316), (258, 350), (314, 302)], width=14)
    if printer:
        rounded_rect(draw, (112, 272, 400, 390), 28, fill=WHITE)
        rounded_rect(draw, (170, 228, 342, 304), 12, outline=WHITE, width=12)
        line(draw, [(170, 324), (342, 324)], width=10, fill=SECONDARY)
        line(draw, [(170, 352), (310, 352)], width=10, fill=SECONDARY)
        circle(draw, 356, 314, 10, fill=PRIMARY, outline=PRIMARY, width=1)


def draw_document_scan(draw: ImageDraw.ImageDraw) -> None:
    rounded_rect(draw, (152, 104, 360, 390), 24, outline=WHITE, width=16)
    line(draw, [(196, 184), (314, 184)], width=12)
    line(draw, [(196, 230), (314, 230)], width=12)
    line(draw, [(196, 276), (292, 276)], width=12)
    line(draw, [(118, 154), (118, 118), (154, 118)], width=14)
    line(draw, [(394, 154), (394, 118), (358, 118)], width=14)
    line(draw, [(118, 338), (118, 374), (154, 374)], width=14)
    line(draw, [(394, 338), (394, 374), (358, 374)], width=14)
    line(draw, [(184, 332), (232, 300), (270, 320), (328, 252)], width=14)
    circle(draw, 328, 252, 10, fill=PRIMARY, outline=PRIMARY, width=1)


def draw_monitor(draw: ImageDraw.ImageDraw) -> None:
    rounded_rect(draw, (112, 126, 400, 300), 28, outline=WHITE, width=16)
    line(draw, [(202, 350), (310, 350)], width=16)
    line(draw, [(256, 300), (256, 388)], width=16)
    line(draw, [(160, 250), (222, 188), (272, 230), (330, 166)], width=16)
    line(draw, [(278, 296), (352, 370)], width=18)
    line(draw, [(338, 310), (380, 268), (402, 290), (424, 268), (424, 230), (386, 230), (364, 252), (342, 230)], width=16)


def draw_box(draw: ImageDraw.ImageDraw, with_check: bool = True) -> None:
    line(draw, [(128, 180), (256, 114), (384, 180), (256, 246), (128, 180)], width=16)
    line(draw, [(128, 180), (128, 328), (256, 398), (384, 328), (384, 180)], width=16)
    line(draw, [(256, 246), (256, 398)], width=16)
    if with_check:
        circle(draw, 364, 338, 62, fill=WHITE, outline=WHITE, width=1)
        line(draw, [(330, 338), (354, 362), (398, 316)], width=16, fill=SECONDARY)


def draw_layers(draw: ImageDraw.ImageDraw) -> None:
    line(draw, [(146, 182), (256, 124), (366, 182), (256, 238), (146, 182)], width=16)
    line(draw, [(162, 252), (256, 204), (350, 252), (256, 300), (162, 252)], width=16)
    line(draw, [(178, 326), (256, 286), (334, 326), (256, 366), (178, 326)], width=16)
    line(draw, [(256, 124), (256, 238)], width=12)
    line(draw, [(256, 204), (256, 300)], width=12)
    line(draw, [(256, 286), (256, 366)], width=12)


def draw_clipboard(draw: ImageDraw.ImageDraw) -> None:
    rounded_rect(draw, (142, 126, 370, 402), 28, outline=WHITE, width=16)
    rounded_rect(draw, (198, 88, 314, 148), 22, fill=WHITE, outline=WHITE, width=1)
    for y in (202, 264, 326):
        circle(draw, 190, y, 18, outline=WHITE, width=10)
        line(draw, [(224, y), (324, y)], width=12)
    line(draw, [(176, 200), (188, 212), (208, 186)], width=10, fill=PRIMARY)
    line(draw, [(176, 262), (188, 274), (208, 248)], width=10, fill=PRIMARY)
    line(draw, [(176, 324), (188, 336), (208, 310)], width=10, fill=PRIMARY)


def draw_phone(draw: ImageDraw.ImageDraw, *, with_check: bool = False, with_signal: bool = False) -> None:
    rounded_rect(draw, (154, 96, 358, 416), 34, outline=WHITE, width=16)
    line(draw, [(222, 130), (292, 130)], width=12)
    circle(draw, 256, 380, 12, fill=WHITE, outline=WHITE, width=1)
    if with_signal:
        line(draw, [(198, 286), (224, 250), (250, 282), (286, 214), (320, 246)], width=16)
        circle(draw, 320, 246, 10, fill=PRIMARY, outline=PRIMARY, width=1)
    if with_check:
        circle(draw, 334, 330, 52, fill=WHITE, outline=WHITE, width=1)
        line(draw, [(308, 330), (326, 348), (360, 312)], width=14, fill=SECONDARY)


def draw_app_grid(draw: ImageDraw.ImageDraw) -> None:
    rounded_rect(draw, (108, 122, 404, 390), 30, outline=WHITE, width=16)
    tile_boxes = [
        (146, 178, 224, 256),
        (252, 178, 330, 256),
        (146, 284, 224, 362),
        (252, 284, 330, 362),
    ]
    for box in tile_boxes:
        rounded_rect(draw, box, 16, outline=WHITE_SOFT, width=12)
    line(draw, [(364, 188), (364, 348)], width=12)
    circle(draw, 364, 228, 16, fill=WHITE, outline=WHITE, width=1)
    circle(draw, 364, 308, 16, fill=WHITE, outline=WHITE, width=1)


ICON_BUILDERS: dict[str, Callable[[ImageDraw.ImageDraw], None]] = {
    "web_responsive_app_customizer": draw_app_grid,
    "wex_accounting_portal": lambda draw: draw_portal(draw, with_chart=True),
    "wex_device_test": lambda draw: draw_phone(draw, with_check=True, with_signal=True),
    "wexplay_image_core": draw_image_frame,
    "wexplay_knowledge_images": lambda draw: (draw_knowledge(draw), draw_image_frame(draw)),
    "wexplay_knowledge_portal": lambda draw: draw_portal(draw, with_knowledge=True),
    "wexplay_portal": draw_portal,
    "wexplay_portal_repair_communication": lambda draw: draw_portal(draw, with_chat=True),
    "wexplay_portal_repair_workflow": lambda draw: draw_portal(draw, with_check=True),
    "wexplay_portal_whatsapp": lambda draw: draw_portal(draw, with_chat=True, with_phone=True),
    "wexplay_product_print": lambda draw: (draw_printer(draw), line(draw, [(122, 248), (194, 196), (246, 222), (174, 274), (122, 248)], width=14)),
    "wexplay_repair": lambda draw: draw_gear(draw, with_wrench=True),
    "wexplay_repair_delivery": draw_box,
    "wexplay_repair_images": lambda draw: draw_image_frame(draw, with_wrench=True),
    "wexplay_repair_warranty": lambda draw: (draw_gear(draw), draw_shield(draw)),
    "wexplay_repair_workflow": lambda draw: draw_gear(draw, with_flow=True),
    "wexplay_sat_print": lambda draw: draw_document(draw, printer=True),
    "wex_consent": lambda draw: draw_document(draw, signed=True),
    "wex_it_maintenance": draw_monitor,
    "wex_knowledge": draw_knowledge,
    "wex_print_core": draw_printer,
    "wex_product_codes": draw_barcode,
    "wex_purchase_list": draw_clipboard,
    "wex_teardown": draw_layers,
    "wex_vendor_bill_ocr": draw_document_scan,
}


SVG_SYMBOLS: dict[str, str] = {
    "web_responsive_app_customizer": """
    <rect x="108" y="122" width="296" height="268" rx="30" class="outline"/>
    <rect x="146" y="178" width="78" height="78" rx="16" stroke="#F6F4FB" stroke-width="12" fill="none"/>
    <rect x="252" y="178" width="78" height="78" rx="16" stroke="#F6F4FB" stroke-width="12" fill="none"/>
    <rect x="146" y="284" width="78" height="78" rx="16" stroke="#F6F4FB" stroke-width="12" fill="none"/>
    <rect x="252" y="284" width="78" height="78" rx="16" stroke="#F6F4FB" stroke-width="12" fill="none"/>
    <path d="M364 188V348" class="outline thin"/>
    <circle cx="364" cy="228" r="16" class="solid"/>
    <circle cx="364" cy="308" r="16" class="solid"/>
    """,
    "wex_accounting_portal": """
    <rect x="96" y="116" width="320" height="250" rx="30" class="outline"/>
    <path d="M124 176H388" class="outline thin"/>
    <circle cx="140" cy="146" r="10" class="solid"/>
    <circle cx="174" cy="146" r="10" class="solid"/>
    <circle cx="208" cy="146" r="10" class="solid"/>
    <path d="M194 316V218L248 186H318V316" class="outline"/>
    <path d="M246 184V316" class="outline thin"/>
    <path d="M136 326L170 290L212 320L250 258" class="outline"/>
    <circle cx="250" cy="258" r="10" fill="#73C799"/>
    <path d="M136 224V326H268" class="outline thin"/>
    """,
    "wex_device_test": """
    <rect x="154" y="96" width="204" height="320" rx="34" class="outline"/>
    <path d="M222 130H292" class="outline thin"/>
    <circle cx="256" cy="380" r="12" class="solid"/>
    <path d="M198 286L224 250L250 282L286 214L320 246" class="outline"/>
    <circle cx="320" cy="246" r="10" fill="#73C799"/>
    <circle cx="334" cy="330" r="52" class="solid"/>
    <path d="M308 330L326 348L360 312" class="accent"/>
    """,
    "wexplay_image_core": """
    <rect x="116" y="122" width="280" height="230" rx="28" class="outline"/>
    <circle cx="334" cy="186" r="22" class="solid"/>
    <path d="M150 314L218 242L274 292L334 224L364 256" class="outline"/>
    """,
    "wexplay_knowledge_images": """
    <path d="M118 166V360L240 342L256 338L272 342L394 360V166" class="outline"/>
    <path d="M256 164V334" class="outline thin"/>
    <path d="M146 196H210M302 196H366" class="outline thin"/>
    <circle cx="256" cy="160" r="72" class="outline"/>
    <path d="M228 248L246 272L256 298L266 272L284 248" class="outline"/>
    <path d="M232 314H280" class="accent"/>
    <rect x="128" y="248" width="180" height="136" rx="22" stroke="#F6F4FB" stroke-width="12" fill="none"/>
    <circle cx="270" cy="286" r="16" fill="#F6F4FB"/>
    <path d="M150 356L194 312L230 340L268 294L290 320" stroke="#F6F4FB" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
    "wexplay_knowledge_portal": """
    <rect x="96" y="116" width="320" height="250" rx="30" class="outline"/>
    <path d="M124 176H388" class="outline thin"/>
    <circle cx="140" cy="146" r="10" class="solid"/>
    <circle cx="174" cy="146" r="10" class="solid"/>
    <circle cx="208" cy="146" r="10" class="solid"/>
    <path d="M194 316V218L248 186H318V316" class="outline"/>
    <path d="M246 184V316" class="outline thin"/>
    <circle cx="352" cy="252" r="38" stroke="#F6F4FB" stroke-width="10" fill="none"/>
    <path d="M352 218V286M320 252H384M336 276L352 296L368 276" stroke="#F6F4FB" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
    "wexplay_portal": """
    <rect x="96" y="116" width="320" height="250" rx="30" class="outline"/>
    <path d="M124 176H388" class="outline thin"/>
    <circle cx="140" cy="146" r="10" class="solid"/>
    <circle cx="174" cy="146" r="10" class="solid"/>
    <circle cx="208" cy="146" r="10" class="solid"/>
    <path d="M194 316V218L248 186H318V316" class="outline"/>
    <path d="M246 184V316" class="outline thin"/>
    """,
    "wexplay_portal_repair_communication": """
    <rect x="96" y="116" width="320" height="250" rx="30" class="outline"/>
    <path d="M124 176H388" class="outline thin"/>
    <circle cx="140" cy="146" r="10" class="solid"/>
    <circle cx="174" cy="146" r="10" class="solid"/>
    <circle cx="208" cy="146" r="10" class="solid"/>
    <path d="M194 316V218L248 186H318V316" class="outline"/>
    <path d="M246 184V316" class="outline thin"/>
    <rect x="278" y="230" width="116" height="82" rx="18" stroke="#F6F4FB" stroke-width="12" fill="none"/>
    <path d="M316 312L302 338L334 314" stroke="#F6F4FB" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <path d="M302 256H370M302 284H354" stroke="#F6F4FB" stroke-width="10" stroke-linecap="round" fill="none"/>
    """,
    "wexplay_portal_repair_workflow": """
    <rect x="96" y="116" width="320" height="250" rx="30" class="outline"/>
    <path d="M124 176H388" class="outline thin"/>
    <circle cx="140" cy="146" r="10" class="solid"/>
    <circle cx="174" cy="146" r="10" class="solid"/>
    <circle cx="208" cy="146" r="10" class="solid"/>
    <path d="M194 316V218L248 186H318V316" class="outline"/>
    <path d="M246 184V316" class="outline thin"/>
    <circle cx="342" cy="324" r="56" class="solid"/>
    <path d="M314 324L334 344L372 304" class="accent"/>
    """,
    "wexplay_portal_whatsapp": """
    <rect x="96" y="116" width="320" height="250" rx="30" class="outline"/>
    <path d="M124 176H388" class="outline thin"/>
    <circle cx="140" cy="146" r="10" class="solid"/>
    <circle cx="174" cy="146" r="10" class="solid"/>
    <circle cx="208" cy="146" r="10" class="solid"/>
    <path d="M194 316V218L248 186H318V316" class="outline"/>
    <path d="M246 184V316" class="outline thin"/>
    <rect x="278" y="230" width="116" height="82" rx="18" stroke="#F6F4FB" stroke-width="12" fill="none"/>
    <path d="M316 312L302 338L334 314" stroke="#F6F4FB" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    <path d="M308 252L322 240L344 248L338 268L352 282L334 294L314 286L304 266" stroke="#F6F4FB" stroke-width="12" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
    """,
    "wexplay_product_print": """
    <path d="M122 248L194 196L246 222L174 274L122 248Z" class="outline thin"/>
    <rect x="118" y="180" width="276" height="162" rx="30" class="solid"/>
    <rect x="156" y="114" width="200" height="118" rx="18" class="outline thin"/>
    <rect x="154" y="276" width="204" height="122" rx="14" class="soft"/>
    <path d="M188 320H324M188 352H302" class="accent"/>
    <circle cx="348" cy="260" r="10" fill="#73C799"/>
    """,
    "wexplay_repair": """
    <g class="solid">
      <rect x="226" y="94" width="60" height="58" rx="10"/>
      <rect x="226" y="360" width="60" height="58" rx="10"/>
      <rect x="360" y="226" width="58" height="60" rx="10"/>
      <rect x="94" y="226" width="58" height="60" rx="10"/>
      <rect x="306" y="126" width="56" height="56" rx="10" transform="rotate(45 334 154)"/>
      <rect x="306" y="330" width="56" height="56" rx="10" transform="rotate(45 334 358)"/>
      <rect x="150" y="330" width="56" height="56" rx="10" transform="rotate(45 178 358)"/>
      <rect x="150" y="126" width="56" height="56" rx="10" transform="rotate(45 178 154)"/>
    </g>
    <circle cx="256" cy="256" r="104" class="outline"/>
    <circle cx="256" cy="256" r="72" class="outline"/>
    <path d="M178 332L332 178" class="outline heavy"/>
    <path d="M300 170L334 136L366 168L350 186L376 212L404 190" class="outline"/>
    <circle cx="168" cy="344" r="14" class="outline"/>
    <circle cx="344" cy="168" r="18" fill="#73C799"/>
    """,
    "wexplay_repair_delivery": """
    <path d="M128 180L256 114L384 180L256 246L128 180Z" class="outline"/>
    <path d="M128 180V328L256 398L384 328V180" class="outline"/>
    <path d="M256 246V398" class="outline"/>
    <circle cx="364" cy="338" r="62" class="solid"/>
    <path d="M330 338L354 362L398 316" class="accent strong"/>
    """,
    "wexplay_repair_images": """
    <rect x="116" y="122" width="280" height="230" rx="28" class="outline"/>
    <circle cx="334" cy="186" r="22" class="solid"/>
    <path d="M150 314L218 242L274 292L334 224L364 256" class="outline"/>
    <path d="M246 336L320 410" class="outline heavy"/>
    <path d="M306 350L348 308L370 330L392 308V270H354L332 292L310 270" class="outline"/>
    """,
    "wexplay_repair_warranty": """
    <g class="solid">
      <rect x="226" y="94" width="60" height="58" rx="10"/>
      <rect x="226" y="360" width="60" height="58" rx="10"/>
      <rect x="360" y="226" width="58" height="60" rx="10"/>
      <rect x="94" y="226" width="58" height="60" rx="10"/>
      <rect x="306" y="126" width="56" height="56" rx="10" transform="rotate(45 334 154)"/>
      <rect x="306" y="330" width="56" height="56" rx="10" transform="rotate(45 334 358)"/>
      <rect x="150" y="330" width="56" height="56" rx="10" transform="rotate(45 178 358)"/>
      <rect x="150" y="126" width="56" height="56" rx="10" transform="rotate(45 178 154)"/>
    </g>
    <circle cx="256" cy="256" r="104" class="outline"/>
    <circle cx="256" cy="256" r="72" class="outline"/>
    <path d="M256 112L366 152V252L350 336L256 406L162 336L146 252V152L256 112Z" class="outline"/>
    <circle cx="256" cy="252" r="40" stroke="#F6F4FB" stroke-width="10" fill="none"/>
    <path d="M194 252L236 294L320 210" class="accent strong"/>
    """,
    "wexplay_repair_workflow": """
    <g class="solid">
      <rect x="226" y="94" width="60" height="58" rx="10"/>
      <rect x="226" y="360" width="60" height="58" rx="10"/>
      <rect x="360" y="226" width="58" height="60" rx="10"/>
      <rect x="94" y="226" width="58" height="60" rx="10"/>
      <rect x="306" y="126" width="56" height="56" rx="10" transform="rotate(45 334 154)"/>
      <rect x="306" y="330" width="56" height="56" rx="10" transform="rotate(45 334 358)"/>
      <rect x="150" y="330" width="56" height="56" rx="10" transform="rotate(45 178 358)"/>
      <rect x="150" y="126" width="56" height="56" rx="10" transform="rotate(45 178 154)"/>
    </g>
    <circle cx="256" cy="256" r="104" class="outline"/>
    <circle cx="256" cy="256" r="72" class="outline"/>
    <circle cx="174" cy="200" r="24" class="solid"/>
    <circle cx="344" cy="170" r="24" fill="#73C799"/>
    <circle cx="338" cy="336" r="24" fill="#F6F4FB"/>
    <path d="M202 198L316 176M344 202L338 304M314 326L204 224" class="outline thin"/>
    <path d="M304 166L316 176L304 186M330 294L338 304L346 294M214 214L204 224L218 226" class="outline thin"/>
    """,
    "wexplay_sat_print": """
    <rect x="146" y="104" width="220" height="300" rx="24" class="outline"/>
    <path d="M194 186H318M194 232H318M194 278H302" class="outline thin"/>
    <rect x="112" y="272" width="288" height="118" rx="28" class="solid"/>
    <rect x="170" y="228" width="172" height="76" rx="12" class="outline thin"/>
    <path d="M170 324H342M170 352H310" class="accent"/>
    <circle cx="356" cy="314" r="10" fill="#73C799"/>
    """,
    "wex_consent": """
    <rect x="146" y="104" width="220" height="300" rx="24" class="outline"/>
    <path d="M194 186H318M194 232H318M194 278H302" class="outline thin"/>
    <path d="M196 342L228 316L258 350L314 302" class="accent strong"/>
    """,
    "wex_it_maintenance": """
    <rect x="112" y="126" width="288" height="174" rx="28" class="outline"/>
    <path d="M202 350H310M256 300V388" class="outline"/>
    <path d="M160 250L222 188L272 230L330 166" class="outline"/>
    <path d="M278 296L352 370" class="outline heavy"/>
    <path d="M338 310L380 268L402 290L424 268V230H386L364 252L342 230" class="outline"/>
    """,
    "wex_knowledge": """
    <path d="M118 166V360L240 342L256 338L272 342L394 360V166" class="outline"/>
    <path d="M256 164V334" class="outline thin"/>
    <path d="M146 196H210M302 196H366" class="outline thin"/>
    <circle cx="256" cy="160" r="72" class="outline"/>
    <path d="M228 248L246 272L256 298L266 272L284 248" class="outline"/>
    <path d="M232 314H280" class="accent"/>
    """,
    "wex_print_core": """
    <rect x="118" y="180" width="276" height="162" rx="30" class="solid"/>
    <rect x="156" y="114" width="200" height="118" rx="18" class="outline thin"/>
    <rect x="154" y="276" width="204" height="122" rx="14" class="soft"/>
    <path d="M188 320H324M188 352H302" class="accent"/>
    <circle cx="348" cy="260" r="10" fill="#73C799"/>
    """,
    "wex_product_codes": """
    <rect x="108" y="126" width="296" height="260" rx="28" class="outline"/>
    <g class="solid">
      <rect x="154" y="176" width="10" height="160"/>
      <rect x="172" y="176" width="18" height="186"/>
      <rect x="198" y="176" width="8" height="144"/>
      <rect x="214" y="176" width="14" height="188"/>
      <rect x="236" y="176" width="10" height="168"/>
      <rect x="254" y="176" width="22" height="190"/>
      <rect x="284" y="176" width="8" height="150"/>
      <rect x="300" y="176" width="16" height="184"/>
      <rect x="324" y="176" width="10" height="156"/>
      <rect x="342" y="176" width="14" height="174"/>
    </g>
    <path d="M150 420H362" class="outline thin"/>
    """,
    "wex_purchase_list": """
    <rect x="142" y="126" width="228" height="276" rx="28" class="outline"/>
    <rect x="198" y="88" width="116" height="60" rx="22" class="solid"/>
    <circle cx="190" cy="202" r="18" class="outline thin"/>
    <circle cx="190" cy="264" r="18" class="outline thin"/>
    <circle cx="190" cy="326" r="18" class="outline thin"/>
    <path d="M224 202H324M224 264H324M224 326H324" class="outline thin"/>
    <path d="M176 200L188 212L208 186M176 262L188 274L208 248M176 324L188 336L208 310" class="accent"/>
    """,
    "wex_teardown": """
    <path d="M146 182L256 124L366 182L256 238L146 182Z" class="outline"/>
    <path d="M162 252L256 204L350 252L256 300L162 252Z" class="outline"/>
    <path d="M178 326L256 286L334 326L256 366L178 326Z" class="outline"/>
    <path d="M256 124V238M256 204V300M256 286V366" class="outline thin"/>
    """,
    "wex_vendor_bill_ocr": """
    <rect x="152" y="104" width="208" height="286" rx="24" class="outline"/>
    <path d="M196 184H314M196 230H314M196 276H292" class="outline thin"/>
    <path d="M118 154V118H154M394 154V118H358M118 338V374H154M394 338V374H358" class="outline"/>
    <path d="M184 332L232 300L270 320L328 252" class="outline"/>
    <circle cx="328" cy="252" r="10" fill="#73C799"/>
    """,
}


def build_svg(symbol_markup: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="512" height="512" viewBox="0 0 512 512" fill="none" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="bg" x1="64" y1="64" x2="448" y2="448" gradientUnits="userSpaceOnUse">
      <stop offset="0" stop-color="{PRIMARY}"/>
      <stop offset="1" stop-color="{SECONDARY}"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="512" height="512" rx="{RADIUS}" fill="url(#bg)"/>
  <path d="M36 278C84 210 176 154 304 154C386 154 438 176 476 202" stroke="white" stroke-opacity="0.14" stroke-width="10" stroke-linecap="round"/>
  <style>
    .outline {{ stroke: white; stroke-width: 16; stroke-linecap: round; stroke-linejoin: round; fill: none; }}
    .outline.thin {{ stroke-width: 12; }}
    .outline.heavy {{ stroke-width: 20; }}
    .solid {{ fill: white; }}
    .soft {{ fill: {WHITE_SOFT}; }}
    .accent {{ stroke: {PRIMARY}; stroke-width: 12; stroke-linecap: round; stroke-linejoin: round; fill: none; }}
    .accent.strong {{ stroke-width: 18; }}
  </style>
  {symbol_markup}
</svg>
"""


def save_icon(module_name: str, builder: Callable[[ImageDraw.ImageDraw], None]) -> None:
    module_path = ROOT / module_name / "static" / "description"
    module_path.mkdir(parents=True, exist_ok=True)

    image, draw = build_base_icon()
    builder(draw)
    image.save(module_path / "icon.png")

    symbol_markup = SVG_SYMBOLS.get(module_name)
    if symbol_markup:
        (module_path / "icon.svg").write_text(build_svg(symbol_markup), encoding="utf-8")


def main() -> None:
    for module_name, builder in ICON_BUILDERS.items():
        save_icon(module_name, builder)


if __name__ == "__main__":
    main()
