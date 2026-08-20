"""Render one completed or interrupted session as a readable PDF."""

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


BLUE = colors.HexColor("#294a8a")
GRID = colors.HexColor("#cbd2dc")


def build_session_pdf(session: dict) -> bytes:
    """Build the report from small independently readable table helpers."""

    output = BytesIO()
    font = _font_name()
    styles = getSampleStyleSheet()
    normal = ParagraphStyle(
        "Prisma", parent=styles["BodyText"], fontName=font, fontSize=8, leading=10
    )
    heading = ParagraphStyle(
        "PrismaTitle", parent=styles["Title"], fontName=font,
        fontSize=17, alignment=TA_CENTER, spaceAfter=10,
    )
    document = SimpleDocTemplate(
        output, pagesize=landscape(A4), leftMargin=12 * mm, rightMargin=12 * mm,
        topMargin=12 * mm, bottomMargin=12 * mm,
    )
    story = [Paragraph("ПРИЗМА — отчёт о прохождении", heading),
             _summary_table(session, font), Spacer(1, 8 * mm)]
    scores = _scores_table(session.get("analysis") or {}, font)
    if scores:
        story.extend([scores, Spacer(1, 8 * mm)])
    story.extend([Paragraph("Исходные сравнения", normal), Spacer(1, 2 * mm),
                  _responses_table(session, font)])
    document.build(story)
    return output.getvalue()


def _font_name() -> str:
    candidates = (Path("C:/Windows/Fonts/arial.ttf"),
                  Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    for path in candidates:
        if path.exists():
            pdfmetrics.registerFont(TTFont("PrismaUnicode", str(path)))
            return "PrismaUnicode"
    return "Helvetica"


def _summary_table(session: dict, font: str) -> Table:
    rows = [
        ["Участник", session["user_name"], "Коллекция", session["collection_name"]],
        ["Начало", session["started_at"], "Завершение", session["finished_at"] or "—"],
        ["Режим времени", session["time_mode"], "Лимит, мс", session["time_limit_ms"] or "—"],
        ["Статус", session["status"], "Random seed", session["random_seed"]],
    ]
    table = Table(rows, colWidths=[30 * mm, 70 * mm, 32 * mm, 100 * mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#eef2f7")),
        ("BACKGROUND", (2, 0), (2, -1), colors.HexColor("#eef2f7")),
        ("GRID", (0, 0), (-1, -1), .3, GRID),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _scores_table(analysis: dict, font: str) -> Table | None:
    choice = {str(item["type_id"]): item for item in
              (analysis.get("choice_only", {}).get("overall") or [])}
    timed = {str(item["type_id"]): item for item in
             (analysis.get("choice_and_time", {}).get("overall") or [])}
    rows = [["Тип", "Только выбор", "Выбор + время"]]
    for type_id in dict.fromkeys([*choice, *timed]):
        item = choice.get(type_id) or timed[type_id]
        rows.append([item["type_name"], f'{choice.get(type_id, {}).get("percent", 0):.2f} %',
                     f'{timed.get(type_id, {}).get("percent", 0):.2f} %'])
    if len(rows) == 1:
        return None
    table = Table(rows, colWidths=[80 * mm, 45 * mm, 45 * mm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), .3, GRID), ("PADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _responses_table(session: dict, font: str) -> Table:
    rows = [["№", "Ур.", "Картинка A", "Тип A", "Картинка B", "Тип B",
             "Выбранный тип", "Время, мс", "Лимит", "Статус"]]
    for item in session.get("comparisons") or []:
        if not item["is_training"]:
            rows.append(_response_row(item))
    widths = [9, 9, 39, 22, 39, 22, 28, 20, 17, 18]
    table = Table(rows, repeatRows=1, colWidths=[value * mm for value in widths])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), font), ("FONTSIZE", (0, 0), (-1, -1), 6.5),
        ("BACKGROUND", (0, 0), (-1, 0), BLUE), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), .25, colors.HexColor("#d6dbe3")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"), ("PADDING", (0, 0), (-1, -1), 3),
    ]))
    return table


def _response_row(item: dict) -> list:
    reaction = item["reaction_time_ms"]
    return [item["presentation_index"], item["level_index"], item["left_item_id"],
            item["left_type_name"], item["right_item_id"], item["right_type_name"],
            item["selected_type_name"] or "—", f"{reaction:.2f}" if reaction is not None else "—",
            "да" if item["exceeded_time_limit"] else "нет", item["status"]]
