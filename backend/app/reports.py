import io
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from .models import AssessmentMedia
from .report_brand import GRAY, MINT, NAVY, TEAL, apply_typography, brand_header, label
from .storage import LocalStorageProvider


def frame_image(path, media, frame):
    from PIL import Image as PILImage
    from PIL import ImageDraw

    if media.mime.startswith("video/"):
        import cv2

        cap = cv2.VideoCapture(str(path))
        try:
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame["frame_index"])
            ok, bgr = cap.read()
            if not ok:
                return None
            picture = PILImage.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
        finally:
            cap.release()
    else:
        with PILImage.open(path) as source:
            picture = source.convert("RGB")
    picture.thumbnail((1200, 1200))
    draw = ImageDraw.Draw(picture)
    points = {
        p["name"]: p
        for p in frame["landmarks"]
        if p["visibility"] >= 0.65 and 0 <= p["x"] <= 1 and 0 <= p["y"] <= 1
    }
    edges = [("left_shoulder", "right_shoulder"), ("left_hip", "right_hip")]
    for side in ("left", "right"):
        edges += [
            (side + "_" + a, side + "_" + b)
            for a, b in [
                ("shoulder", "elbow"),
                ("elbow", "wrist"),
                ("shoulder", "hip"),
                ("hip", "knee"),
                ("knee", "ankle"),
                ("ankle", "foot_index"),
            ]
        ]

    def xy(p):
        return (p["x"] * picture.width, p["y"] * picture.height)

    for a, b in edges:
        if a in points and b in points:
            draw.line([xy(points[a]), xy(points[b])], fill=TEAL, width=3)
    for point in points.values():
        x, y = xy(point)
        draw.ellipse((x - 3, y - 3, x + 3, y + 3), fill=MINT)
    buffer = io.BytesIO()
    picture.save(buffer, format="JPEG")
    buffer.seek(0)
    return buffer


def motion_chart(analysis):
    from reportlab.graphics.shapes import Drawing, Line, PolyLine, String

    key = analysis["motion"]["signal"]
    frames = analysis["frames"]
    values = [f["measurements"]["values"].get(key) for f in frames]
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    drawing = Drawing(460, 170)
    lo = min(valid)
    hi = max(valid)
    span = max(hi - lo, 1)
    last = max(frames[-1]["timestamp_ms"], 1)
    drawing.add(String(5, 155, key, fontSize=9))
    drawing.add(Line(35, 25, 450, 25, strokeColor=colors.grey))
    drawing.add(String(2, 135, f"{hi:.1f}", fontSize=8))
    drawing.add(String(2, 25, f"{lo:.1f}", fontSize=8))
    drawing.add(String(35, 10, "0 s", fontSize=8))
    drawing.add(String(410, 10, f"{last / 1000:.1f} s", fontSize=8))
    segment = []

    def flush():
        if len(segment) >= 4:
            drawing.add(
                PolyLine(
                    segment.copy(),
                    strokeColor=colors.HexColor(TEAL),
                    strokeWidth=1.5,
                )
            )
        segment.clear()

    for frame, value in zip(frames, values):
        if value is None:
            flush()
        else:
            segment.extend(
                [
                    35 + frame["timestamp_ms"] / last * 415,
                    25 + (value - lo) / span * 110,
                ]
            )
    flush()
    return drawing


NOTICE = "Os resultados automatizados apresentados constituem ferramenta de apoio à avaliação profissional e devem ser interpretados em conjunto com exame clínico, histórico e julgamento do profissional responsável."


def make_pdf(snapshot: dict, db) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=(21 * cm, 29.7 * cm),
        title="KINUA - Relatório de avaliação corporal",
        author="KINUA",
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
    )
    styles = getSampleStyleSheet()
    apply_typography(styles)
    styles["Title"].textColor = colors.HexColor(NAVY)

    def p(value, style="BodyText"):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])

    a = snapshot["assessment"]
    flow = [
        brand_header(),
        Spacer(1, 0.5 * cm),
        p("Relatório de avaliação corporal", "Title"),
        p(snapshot["patient"]["name"], "Heading2"),
        p(
            "Data: "
            + a["created_at"][:10]
            + " · Profissional: "
            + snapshot["professional"]
        ),
        p("Tipo: " + label(a["kind"]) + " · Estado: " + label(a["status"])),
        Spacer(1, 0.4 * cm),
        p(NOTICE),
    ]
    protocol = a.get("assessment_protocol")
    if protocol:
        flow += [
            p(protocol["snapshot"]["name"], "Heading2"),
            p("KINUA Assessment Protocols · versão " + protocol["snapshot"]["version"]),
        ]
        step_states = {
            "not_started": "Não iniciada",
            "in_progress": "Em andamento",
            "completed": "Concluída",
            "skipped": "Ignorada com justificativa",
        }
        for index, step in enumerate(protocol["steps"], 1):
            flow.append(
                p(
                    f"{index}. {step['definition']['name']} · {step_states[step['state']]}",
                    "Heading3",
                )
            )
            flow.append(
                p("Resultado profissional: " + (step["result"] or "Não registrado."))
            )
            if step["note"]:
                flow.append(p("Observação / justificativa: " + step["note"]))
            if step["completed_at"]:
                flow.append(p("Concluída em " + step["completed_at"]))
            if step["skipped_at"]:
                flow.append(p("Ignorada em " + step["skipped_at"]))
            if step["child_assessment_id"]:
                flow.append(p("Avaliação vinculada: " + step["child_assessment_id"]))
        for child in snapshot.get("protocol_children", []):
            flow += [
                p("Revisão da captura " + child["id"], "Heading3"),
                p("Estado: " + label(child["status"])),
                p("Observações: " + (child["notes"] or "Não registradas.")),
                p(
                    "Conclusão profissional: "
                    + (child["conclusion"] or "Ainda não concluída.")
                ),
            ]
    for analysis in a["analyses"]:
        flow += [p("Captura · " + analysis["media"]["view"], "Heading2")]
        media = db.get(AssessmentMedia, analysis["media_id"])
        verified = LocalStorageProvider().verified_path(
            media.storage_key, media.sha256, media.size
        )
        frames = analysis["frames"]
        motion = analysis.get("motion", {})
        if motion.get("rom"):
            config = motion["rom"]
            flow += [
                p("KINUA ROM · " + config["name"], "Heading2"),
                p(
                    "Plano: "
                    + ("frontal" if config["plane"] == "frontal" else "sagital")
                    + " · versão "
                    + config["version"]
                ),
            ]
            for record in analysis.get("rom_measurements", []):
                side = "Direito" if record["side"] == "right" else "Esquerdo"
                peak_label = (
                    "Flexão residual mínima"
                    if config["direction"] < 0
                    else "Pico observado"
                )
                flow += [
                    p(side, "Heading3"),
                    p(
                        f"{peak_label}: {record['peak_value']:.1f}° · mínimo {record['minimum']:.1f}° · máximo {record['maximum']:.1f}° · excursão observada {record['excursion']:.1f}°."
                    ),
                    p(
                        f"Frame do pico: {record['peak_frame_index']} · {record['peak_timestamp_ms'] / 1000:.2f} s · visibilidade no pico {record['confidence'] * 100:.0f}%."
                    ),
                    p(
                        f"Amostras válidas: {record['details']['valid_samples']}/{record['details']['total_samples']}. Visibilidade não representa acurácia clínica."
                    ),
                ]
        indexes = [0]
        if motion:
            indexes += [
                e["index"]
                for e in motion["phase_detection"]["events"]
                if e["type"] == "maximum"
            ][:2]
            flow.append(
                p(
                    "Protocolo: "
                    + motion["protocol"]
                    + " · Resumo temporal das amostras válidas."
                )
            )
            flow.append(p(motion["phase_limitations"]))
        for index in dict.fromkeys(indexes):
            buffer = frame_image(verified, media, frames[index])
            if buffer is None:
                flow.append(p("Frame indisponível para ilustração."))
                continue
            image = Image(buffer)
            scale = min(15 * cm / image.imageWidth, 8 * cm / image.imageHeight)
            image.drawWidth, image.drawHeight = (
                image.imageWidth * scale,
                image.imageHeight * scale,
            )
            flow += [
                image,
                p(
                    f"Frame {frames[index]['frame_index']} · {frames[index]['timestamp_ms'] / 1000:.2f} s"
                ),
                Spacer(1, 0.3 * cm),
            ]
        if motion:
            chart = motion_chart(analysis)
            if chart:
                flow.append(chart)
        data = [[p("Medida"), p("Valor"), p("Visibilidade técnica")]]
        for m in analysis["measurements"]:
            value = (
                f"{m['value']:.1f} {m['unit']}"
                if m["value"] is not None
                else "Não mensurável"
            )
            if m["value"] is not None and "min" in m["details"]:
                value += f" (média)\nMín. {m['details']['min']:.1f}\nMáx. {m['details']['max']:.1f}\nAmplitude {m['details']['amplitude']:.1f}"
            data.append([p(m["label"]), p(value), p(f"{m['confidence'] * 100:.0f}%")])
        table = Table(data, colWidths=[9 * cm, 3.5 * cm, 4 * cm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9F8F4")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor(GRAY)),
                ]
            )
        )
        flow.append(table)
        for message in (
            analysis["quality"]["messages"] + analysis["quality"]["limitations"]
        ):
            flow.append(p(message))
        flow.append(p("Revisão profissional", "Heading3"))
        for finding in analysis["findings"]:
            flow.append(
                p(finding["description"] + " Estado: " + label(finding["state"]))
            )
            for review in finding["reviews"]:
                flow.append(
                    p(
                        review["created_at"]
                        + " · "
                        + label(review["state"])
                        + " · "
                        + review["note"]
                    )
                )
        flow.append(
            p(
                "Versões: "
                + analysis["provider_version"]
                + " / Biomecânica "
                + analysis["biomechanics_version"]
                + " / Regras "
                + analysis["rules_version"]
            )
        )
    if snapshot.get("comparison"):
        comparison = snapshot["comparison"]
        flow += [
            p("Comparação longitudinal", "Heading2"),
            p("A: " + comparison["date_a"] + " · B: " + comparison["date_b"]),
            p(comparison["notice"]),
        ]
        data = [[p("Medida"), p("A"), p("B"), p("B - A")]]
        for item in comparison["measurements"]:

            def number(value):
                return (
                    f"{value:.2f} {item['unit']}"
                    if value is not None
                    else "Indisponível"
                )

            data.append(
                [
                    p(
                        item["label"]
                        + (" · média" if item["statistic"] == "mean" else "")
                    ),
                    p(number(item["a"])),
                    p(number(item["b"])),
                    p(number(item["difference"])),
                ]
            )
        table = Table(data, colWidths=[7.5 * cm, 3 * cm, 3 * cm, 3 * cm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E9F8F4")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ]
            )
        )
        flow.append(table)
    flow += [
        p("Observações do profissional", "Heading2"),
        p(a["notes"] or "Não preenchidas."),
        p("Conclusão do fisioterapeuta", "Heading2"),
        p(a["conclusion"] or "Não preenchida. Relatório sem conclusão profissional."),
    ]

    def footer(canvas, document):
        canvas.setFont("Manrope", 8)
        canvas.setFillColor(colors.HexColor(NAVY))
        canvas.drawString(
            1.8 * cm, cm, "KINUA | " + a["id"] + " | Página " + str(document.page)
        )

    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
