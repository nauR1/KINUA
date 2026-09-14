"""Local vector identity and embedded typography for KINUA reports."""

import json
import re
from pathlib import Path

from reportlab.graphics.shapes import Circle, Drawing, Group, String
from reportlab.graphics.shapes import Path as VectorPath
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

NAVY = "#0B2D5B"
TEAL = "#14B8A6"
MINT = "#A7F3D0"
GRAY = "#E5EAF0"
ASSETS = Path(__file__).parent / "assets"
LABELS = {
    "postural": "Postural",
    "functional": "Funcional",
    "movement": "Movimento",
    "sports": "Esportiva",
    "followup": "Acompanhamento",
    "draft": "Em preparação",
    "review": "A revisar",
    "completed": "Concluída",
    "detected": "Detectado",
    "needs_review": "A revisar",
    "professional_confirmed": "Confirmado pelo profissional",
    "professional_rejected": "Descartado pelo profissional",
    "bilateral_squat": "Agachamento bilateral",
    "single_leg_squat": "Agachamento unipodal",
    "arm_raise": "Elevação de braço",
}


def label(value):
    return LABELS.get(value, value)


def apply_typography(styles):
    for name, filename in [("Manrope", "Regular"), ("Manrope-SemiBold", "SemiBold")]:
        if name not in pdfmetrics.getRegisteredFontNames():
            pdfmetrics.registerFont(
                TTFont(name, str(ASSETS / "fonts" / f"Manrope-{filename}.ttf"))
            )
    pdfmetrics.registerFontFamily(
        "Manrope",
        normal="Manrope",
        bold="Manrope-SemiBold",
        italic="Manrope",
        boldItalic="Manrope-SemiBold",
    )
    for name, style in styles.byName.items():
        style.fontName = (
            "Manrope-SemiBold"
            if name.startswith("Heading") or name == "Title"
            else "Manrope"
        )
        style.textColor = HexColor(NAVY)
    styles["BodyText"].fontSize = 9
    styles["BodyText"].leading = 13
    styles["BodyText"].spaceBefore = 4
    styles["Title"].fontSize = 20
    styles["Title"].leading = 26
    styles["Title"].alignment = 0


def brand_header():
    drawing = Drawing(465, 64)
    symbol = Group()
    symbol.add(Circle(77, 17, 12, fillColor=HexColor(NAVY), strokeColor=None))
    geometry = json.loads((ASSETS / "kinua-geometry.json").read_text())
    for index, value in enumerate(geometry["paths"]):
        path = VectorPath(
            fillColor=HexColor(NAVY if index < 2 else TEAL), strokeColor=None
        )
        tokens = iter(re.findall(r"[MCLZ]|-?\d+(?:\.\d+)?", value))
        for command in tokens:
            if command == "Z":
                path.closePath()
            else:
                count = 6 if command == "C" else 2
                coordinates = [float(next(tokens)) for _ in range(count)]
                {"M": path.moveTo, "L": path.lineTo, "C": path.curveTo}[command](
                    *coordinates
                )
        symbol.add(path)
    symbol.transform = (0.4, 0, 0, -0.4, 0, 64)
    drawing.add(symbol)
    drawing.add(
        String(
            65,
            28,
            "KINUA",
            fontName="Manrope-SemiBold",
            fontSize=28,
            fillColor=HexColor(NAVY),
        )
    )
    drawing.add(
        String(
            66,
            12,
            "INTELIGÊNCIA EM MOVIMENTO HUMANO",
            fontName="Manrope",
            fontSize=6.5,
            fillColor=HexColor(NAVY),
        )
    )
    return drawing
