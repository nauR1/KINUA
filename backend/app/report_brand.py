"""Local vector identity and presentation helpers for KINUA reports."""

import json
import re
import unicodedata
from datetime import date, datetime
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
    "review": "Pendente de revisão profissional",
    "completed": "Concluída",
    "detected": "Identificado para revisão profissional",
    "needs_review": "Pendente de revisão profissional",
    "professional_confirmed": "Confirmado pelo profissional",
    "professional_rejected": "Descartado pelo profissional",
    "not_started": "Não iniciada",
    "in_progress": "Em andamento",
    "skipped": "Ignorada com justificativa",
    "bilateral_squat": "Agachamento bilateral",
    "single_leg_squat": "Agachamento unipodal",
    "arm_raise": "Elevação de braço",
    "anterior": "Anterior",
    "posterior": "Posterior",
    "lateral_right": "Lateral direita",
    "lateral_left": "Lateral esquerda",
    "right": "Direito",
    "left": "Esquerdo",
    "bilateral": "Bilateral",
    "frontal": "Frontal",
    "sagittal": "Sagital",
    "rom": "KINUA ROM",
}
MOVEMENT_LABELS = {
    "shoulder_flexion": "Flexão do ombro",
    "shoulder_abduction": "Abdução do ombro",
    "elbow_flexion": "Flexão do cotovelo",
    "elbow_extension": "Extensão do cotovelo",
    "hip_flexion": "Flexão do quadril",
    "knee_flexion": "Flexão do joelho",
    "knee_extension": "Extensão do joelho",
}


def label(value):
    return LABELS.get(value, value)


def movement_label(config):
    return MOVEMENT_LABELS.get(config.get("movement"), config.get("name", "Movimento"))


def rom_measurement_label(config, side):
    side_label = label(side).lower()
    return f"{movement_label(config)} — {side_label}"


def motion_signal_label(analysis):
    motion = analysis.get("motion") or {}
    config = motion.get("rom")
    if config:
        return rom_measurement_label(config, motion.get("side", "bilateral"))
    return "Movimento"


def technical_version_label(analysis):
    motion = analysis.get("motion") or {}
    config = motion.get("rom")
    if config:
        version = str(config.get("version", "")).removeprefix("rom-")
        return f"KINUA ROM {version}" if version else "KINUA ROM"
    version = str(analysis.get("biomechanics_version", ""))
    if re.fullmatch(r"\d+(?:\.\d+)+", version):
        return f"KINUA Biomecânica {version}"
    return "KINUA"


def pose_engine_label(provider_version):
    match = re.search(r"mediapipe-python/([0-9.]+)", str(provider_version))
    return f"MediaPipe {match.group(1)}" if match else None


def format_date(value):
    raw = str(value)
    try:
        parsed = datetime.fromisoformat(raw.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            parsed = date.fromisoformat(raw[:10])
        except ValueError:
            return raw[:10]
    return parsed.strftime("%d/%m/%Y")


def report_filename(patient_name, created_at):
    normalized = unicodedata.normalize("NFKD", str(patient_name))
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    safe_name = re.sub(r"[^A-Za-z0-9]+", "_", ascii_name).strip("_") or "Paciente"
    safe_date = str(created_at)[:10]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", safe_date):
        safe_date = "sem_data"
    return f"KINUA_{safe_name}_{safe_date}.pdf"


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
