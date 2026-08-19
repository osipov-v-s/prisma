"""Compact PDF report for one completed or interrupted session."""

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _font_name() -> str:
    for path in (Path("C:/Windows/Fonts/arial.ttf"), Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")):
        if path.exists():
            pdfmetrics.registerFont(TTFont("PrismaUnicode", str(path)))
            return "PrismaUnicode"
    return "Helvetica"


def build_session_pdf(session: dict) -> bytes:
    output = BytesIO()
    font = _font_name()
    styles = getSampleStyleSheet()
    normal = ParagraphStyle("Prisma", parent=styles["BodyText"], fontName=font, fontSize=8, leading=10)
    heading = ParagraphStyle("PrismaTitle", parent=styles["Title"], fontName=font,
                             fontSize=17, alignment=TA_CENTER, spaceAfter=10)
    document = SimpleDocTemplate(output, pagesize=landscape(A4), leftMargin=12 * mm,
                                 rightMargin=12 * mm, topMargin=12 * mm, bottomMargin=12 * mm)
    story = [Paragraph("ПРИЗМА — отчёт о прохождении", heading)]
    summary = [
        ["Участник", session["user_name"], "Коллекция", session["collection_name"]],
        ["Начало", session["started_at"], "Завершение", session["finished_at"] or "—"],
        ["Режим времени", session["time_mode"], "Лимит, мс", session["time_limit_ms"] or "—"],
        ["Статус", session["status"], "Random seed", session["random_seed"]],
    ]
    table = Table(summary, colWidths=[30 * mm, 70 * mm, 32 * mm, 100 * mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f7")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eef2f7")),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd2dc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    story.extend([table, Spacer(1, 8 * mm)])

    analysis = session.get("analysis") or {}
    score_rows = [["Тип", "Только выбор", "Выбор + время"]]
    choice = {str(item["type_id"]): item for item in (analysis.get("choice_only", {}).get("overall") or [])}
    timed = {str(item["type_id"]): item for item in (analysis.get("choice_and_time", {}).get("overall") or [])}
    for type_id in dict.fromkeys([*choice, *timed]):
        item = choice.get(type_id) or timed[type_id]
        score_rows.append([item["type_name"], f'{choice.get(type_id, {}).get("percent", 0):.2f} %',
                           f'{timed.get(type_id, {}).get("percent", 0):.2f} %'])
    if len(score_rows) > 1:
        scores = Table(score_rows, colWidths=[80 * mm, 45 * mm, 45 * mm])
        scores.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#294a8a")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd2dc")),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]))
        story.extend([scores, Spacer(1, 8 * mm)])

    rows = [["№", "Ур.", "Картинка A", "Тип A", "Картинка B", "Тип B",
             "Выбранный тип", "Время, мс", "Лимит", "Статус"]]
    for item in session.get("comparisons") or []:
        if item["is_training"]:
            continue
        rows.append([item["presentation_index"], item["level_index"], item["left_item_id"],
                     item["left_type_name"], item["right_item_id"], item["right_type_name"],
                     item["selected_type_name"] or "—",
                     f'{item["reaction_time_ms"]:.2f}' if item["reaction_time_ms"] is not None else "—",
                     "да" if item["exceeded_time_limit"] else "нет", item["status"]])
    response_table = Table(rows, repeatRows=1,
                           colWidths=[9 * mm, 9 * mm, 39 * mm, 22 * mm, 39 * mm, 22 * mm,
                                      28 * mm, 20 * mm, 17 * mm, 18 * mm])
    response_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#294a8a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#d6dbe3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    story.extend([Paragraph("Исходные сравнения", normal), Spacer(1, 2 * mm), response_table])
    document.build(story)
    return output.getvalue()
