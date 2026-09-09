import io
from xml.sax.saxutils import escape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from .storage import LocalStorageProvider
from .models import AssessmentMedia

NOTICE = "Os resultados automatizados apresentados constituem ferramenta de apoio à avaliação profissional e devem ser interpretados em conjunto com exame clínico, histórico e julgamento do profissional responsável."


def make_pdf(snapshot: dict, db) -> bytes:
    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=(21 * cm, 29.7 * cm),
        rightMargin=1.8 * cm,
        leftMargin=1.8 * cm,
        topMargin=1.7 * cm,
        bottomMargin=1.7 * cm,
    )
    styles = getSampleStyleSheet()
    styles["Title"].textColor = colors.HexColor("#123c42")

    def p(value, style="BodyText"):
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])

    a = snapshot["assessment"]
    flow = [
        p("BIOMETRIA · Avaliação corporal", "Title"),
        p(snapshot["patient"]["name"], "Heading2"),
        p(
            "Data: "
            + a["created_at"][:10]
            + " · Profissional: "
            + snapshot["professional"]
        ),
        p("Tipo: " + a["kind"] + " · Estado: " + a["status"]),
        Spacer(1, 0.4 * cm),
        p(NOTICE),
    ]
    for analysis in a["analyses"]:
        flow += [p("Captura · " + analysis["media"]["view"], "Heading2")]
        media = db.get(AssessmentMedia, analysis["media_id"])
        image = Image(str(LocalStorageProvider().path(media.storage_key)))
        scale = min(15 * cm / image.imageWidth, 8 * cm / image.imageHeight)
        image.drawWidth, image.drawHeight = (
            image.imageWidth * scale,
            image.imageHeight * scale,
        )
        flow += [image, Spacer(1, 0.3 * cm)]
        data = [[p("Medida"), p("Valor"), p("Visibilidade técnica")]]
        for m in analysis["measurements"]:
            value = (
                f"{m['value']:.1f} {m['unit']}"
                if m["value"] is not None
                else "Não mensurável"
            )
            data.append([p(m["label"]), p(value), p(f"{m['confidence'] * 100:.0f}%")])
        table = Table(data, colWidths=[9 * cm, 3.5 * cm, 4 * cm], repeatRows=1)
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#eaf3f3")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.3, colors.HexColor("#d9e3e4")),
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
            flow.append(p(finding["description"] + " Estado: " + finding["state"]))
            for review in finding["reviews"]:
                flow.append(
                    p(
                        review["created_at"]
                        + " · "
                        + review["state"]
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
    flow += [
        p("Observações do profissional", "Heading2"),
        p(a["notes"] or "Não preenchidas."),
        p("Conclusão do fisioterapeuta", "Heading2"),
        p(a["conclusion"] or "Não preenchida. Relatório sem conclusão profissional."),
    ]

    def footer(canvas, document):
        canvas.setFont("Helvetica", 8)
        canvas.drawString(
            1.8 * cm, cm, "Biometria | " + a["id"] + " | Página " + str(document.page)
        )

    doc.build(flow, onFirstPage=footer, onLaterPages=footer)
    return output.getvalue()
