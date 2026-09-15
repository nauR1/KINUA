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
from .report_brand import (
    GRAY,
    MINT,
    NAVY,
    TEAL,
    apply_typography,
    brand_header,
    format_date,
    label,
    motion_signal_label,
    pose_engine_label,
    rom_measurement_label,
    technical_version_label,
)
from .storage import get_storage, storage_operation


NOTICE = (
    "Os resultados automatizados apresentados constituem ferramenta de apoio à "
    "avaliação profissional e devem ser interpretados em conjunto com exame clínico, "
    "histórico e julgamento do profissional responsável."
)
QUALITY_NOTICE = (
    "A própria análise técnica indicou limitação de estabilidade ou qualidade da "
    "captura. Interprete as medidas com cautela e confirme os achados na revisão "
    "profissional."
)


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
        point["name"]: point
        for point in frame["landmarks"]
        if point["visibility"] >= 0.65
        and 0 <= point["x"] <= 1
        and 0 <= point["y"] <= 1
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

    def xy(point):
        return (point["x"] * picture.width, point["y"] * picture.height)

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
    values = [frame["measurements"]["values"].get(key) for frame in frames]
    valid = [value for value in values if value is not None]
    if not valid:
        return None
    drawing = Drawing(460, 170)
    lo = min(valid)
    hi = max(valid)
    span = max(hi - lo, 1)
    last = max(frames[-1]["timestamp_ms"], 1)
    drawing.add(String(5, 155, motion_signal_label(analysis), fontSize=9))
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


def capture_quality_limited(analysis):
    if analysis.get("quality", {}).get("messages"):
        return True
    for record in analysis.get("rom_measurements", []):
        if record.get("details", {}).get("movement_start_index") is None:
            return True
    return False


def make_table(data, widths):
    table = Table(data, colWidths=widths, repeatRows=1)
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
    return table


@storage_operation
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

    assessment = snapshot["assessment"]
    flow = [
        brand_header(),
        Spacer(1, 0.5 * cm),
        p("Relatório de avaliação corporal", "Title"),
        p(snapshot["patient"]["name"], "Heading2"),
        p(
            "Data: "
            + format_date(assessment["created_at"])
            + " · Profissional: "
            + snapshot["professional"]
        ),
        p(
            "Tipo: "
            + label(assessment["kind"])
            + " · Estado: "
            + label(assessment["status"])
        ),
        Spacer(1, 0.4 * cm),
        p(NOTICE),
    ]

    protocol = assessment.get("assessment_protocol")
    if protocol:
        flow += [
            p(protocol["snapshot"]["name"], "Heading2"),
            p("KINUA Assessment Protocols · versão " + protocol["snapshot"]["version"]),
        ]
        for index, step in enumerate(protocol["steps"], 1):
            flow.append(
                p(
                    f"{index}. {step['definition']['name']} · {label(step['state'])}",
                    "Heading3",
                )
            )
            flow.append(
                p("Resultado profissional: " + (step["result"] or "Não registrado."))
            )
            if step["note"]:
                flow.append(p("Observação / justificativa: " + step["note"]))
            if step["completed_at"]:
                flow.append(p("Concluída em " + format_date(step["completed_at"])))
            if step["skipped_at"]:
                flow.append(p("Ignorada em " + format_date(step["skipped_at"])))
        for index, child in enumerate(snapshot.get("protocol_children", []), 1):
            flow += [
                p(f"Revisão da captura {index}", "Heading3"),
                p("Estado: " + label(child["status"])),
                p("Observações: " + (child["notes"] or "Não registradas.")),
                p(
                    "Conclusão profissional: "
                    + (child["conclusion"] or "Ainda não concluída.")
                ),
            ]

    for analysis in assessment["analyses"]:
        flow.append(p("Captura · " + label(analysis["media"]["view"]), "Heading2"))
        media = db.get(AssessmentMedia, analysis["media_id"])
        verified = get_storage().verified_path(
            media.storage_key, media.sha256, media.size
        )
        frames = analysis["frames"]
        motion = analysis.get("motion", {})
        if motion.get("rom"):
            config = motion["rom"]
            flow += [
                p("KINUA ROM · " + config["name"], "Heading2"),
                p("Plano: " + label(config["plane"]) + " · versão " + config["version"]),
            ]
            for record in analysis.get("rom_measurements", []):
                peak_label = (
                    "Flexão residual mínima"
                    if config["direction"] < 0
                    else "Pico observado"
                )
                flow += [
                    p(rom_measurement_label(config, record["side"]), "Heading3"),
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
                if record.get("details", {}).get("movement_start_index") is None:
                    flow.append(
                        p("Início do movimento não identificado com estabilidade suficiente.")
                    )
        if capture_quality_limited(analysis):
            flow += [
                p("Qualidade de captura limitada", "Heading3"),
                p(QUALITY_NOTICE),
            ]

        indexes = [0]
        if motion:
            indexes += [
                event["index"]
                for event in motion["phase_detection"]["events"]
                if event["type"] == "maximum"
            ][:2]
            flow.append(
                p(
                    "Protocolo: "
                    + label(motion["protocol"])
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
            image.drawWidth = image.imageWidth * scale
            image.drawHeight = image.imageHeight * scale
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
        for measurement in analysis["measurements"]:
            value = (
                f"{measurement['value']:.1f} {measurement['unit']}"
                if measurement["value"] is not None
                else "Não mensurável"
            )
            if measurement["value"] is not None and "min" in measurement["details"]:
                value += (
                    f" (média)\nMín. {measurement['details']['min']:.1f}"
                    f"\nMáx. {measurement['details']['max']:.1f}"
                    f"\nAmplitude {measurement['details']['amplitude']:.1f}"
                )
            data.append(
                [
                    p(measurement["label"]),
                    p(value),
                    p(f"{measurement['confidence'] * 100:.0f}%"),
                ]
            )
        flow.append(make_table(data, [9 * cm, 3.5 * cm, 4 * cm]))

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
                        format_date(review["created_at"])
                        + " · "
                        + label(review["state"])
                        + " · "
                        + review["note"]
                    )
                )
        flow.append(p("Versão técnica: " + technical_version_label(analysis)))
        pose_engine = pose_engine_label(analysis.get("provider_version"))
        if pose_engine:
            flow.append(p("Motor de pose: " + pose_engine))

    if snapshot.get("comparison"):
        comparison = snapshot["comparison"]
        flow += [
            p("Comparação longitudinal", "Heading2"),
            p(
                "A: "
                + format_date(comparison["date_a"])
                + " · B: "
                + format_date(comparison["date_b"])
            ),
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
        flow.append(make_table(data, [7.5 * cm, 3 * cm, 3 * cm, 3 * cm]))

    flow += [
        p("Observações do profissional", "Heading2"),
        p(assessment["notes"] or "Não preenchidas."),
        p("Conclusão do fisioterapeuta", "Heading2"),
        p(
            assessment["conclusion"]
            or "Não preenchida. Relatório sem conclusão profissional."
        ),
    ]

    if snapshot.get("is_demo"):
        flow.insert(0, p("AMBIENTE DE DEMONSTRAÇÃO — DADOS FICTÍCIOS", "Heading2"))

    def footer(canvas, document):
        if snapshot.get("is_demo"):
            canvas.setFont("Manrope", 9)
            canvas.setFillColor(colors.HexColor(TEAL))
            canvas.drawString(
                1.8 * cm, 1.4 * cm, "AMBIENTE DE DEMONSTRAÇÃO — DADOS FICTÍCIOS"
            )
        canvas.setFont("Manrope", 8)
        canvas.setFillColor(colors.HexColor(NAVY))
        canvas.drawString(
            1.8 * cm,
            cm,
            "KINUA | Relatório de avaliação | Página " + str(document.page),
        )

    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
