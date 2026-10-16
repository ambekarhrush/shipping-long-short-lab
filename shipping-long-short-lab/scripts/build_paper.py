"""Render paper/paper.md to paper/shipping_long_short.pdf (ReportLab, house style)."""

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (Image, KeepTogether, ListFlowable, ListItem, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

ROOT = Path(__file__).resolve().parents[1]
FIG = {
    "Figure 1": ("02_fifteen_years.png", "Figure 1. Segment equity baskets against their Baltic freight index, rebased to 100."),
    "Figure 2": ("02_dispersion.png", "Figure 2. Inter-quartile spread of 12-month returns within each segment."),
    "Figure 3": ("02_lead_lag.png", "Figure 3. Correlation of weekly equity and freight changes at leads and lags."),
    "Figure 4": ("eq_curve.png", "Figure 4. Strategy vs S&P 500 and the equal-weight shipping basket, net of costs."),
    "Figure 5": ("07_attribution.png", "Figure 5. Contribution by segment and side."),
    "Figure 6": ("09_stress.png", "Figure 6. Stress windows."),
    "Figure 8": ("02_portwatch.png", "Figure 8. Aggregate ship-tracking data (IMF PortWatch) against freight, same and next four weeks."),
    "Figure 7": ("08_trials.png", "Figure 7. Every research variant tried, from the trials ledger."),
}
INK, MUTED, RULE = colors.HexColor("#1B1F24"), colors.HexColor("#6B7280"), colors.HexColor("#E5E7EB")
body = ParagraphStyle("b", fontName="Helvetica", fontSize=9.6, leading=14, textColor=INK, spaceAfter=6, alignment=TA_LEFT)
h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=13, leading=17, spaceBefore=12, spaceAfter=6, textColor=INK, keepWithNext=1)
title = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=24, leading=28, textColor=INK, spaceAfter=6)
sub = ParagraphStyle("s", fontName="Helvetica", fontSize=12, leading=16, textColor=MUTED, spaceAfter=10)
small = ParagraphStyle("sm", parent=body, fontSize=8, leading=11, textColor=MUTED)
cell = ParagraphStyle("c", parent=body, fontSize=8.4, leading=11, spaceAfter=0)


def inline(t):
    t = t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"\*(.+?)\*", r"<i>\1</i>", t)
    t = re.sub(r"`(.+?)`", r"<font face='Courier'>\1</font>", t)
    return t


def build(name="paper", out_name="shipping_long_short"):
    src = (ROOT / "paper" / f"{name}.md").read_text()
    fm = dict(re.findall(r'^(\w+): "(.*)"$', src.split("---")[1], re.M))
    text = src.split("---", 2)[2]
    width0 = A4[0] - 40 * mm
    from reportlab.platypus import HRFlowable
    kv = ParagraphStyle("kv", fontName="Helvetica-Bold", fontSize=17, leading=20, textColor=INK)
    kl = ParagraphStyle("kl", fontName="Helvetica", fontSize=7.6, leading=9.5, textColor=MUTED)
    keys = [("0.42", "Holdout Sharpe,<br/>2023 - Oct 2026"), ("-0.01", "Beta to the<br/>S&amp;P 500"),
            ("USD 25m", "Approximate<br/>capacity"), ("0.31", "Deflated-Sharpe<br/>probability (27 trials)"),
            ("1,003", "Ships mapped to<br/>21 listed owners")]
    strip = Table([[Paragraph(k, kv) for k, _ in keys], [Paragraph(v, kl) for _, v in keys]],
                  colWidths=[width0 / len(keys)] * len(keys))
    strip.setStyle(TableStyle([("LINEABOVE", (0, 0), (-1, 0), 1.2, INK), ("TOPPADDING", (0, 0), (-1, 0), 8),
                               ("BOTTOMPADDING", (0, 1), (-1, 1), 8), ("LINEBELOW", (0, 1), (-1, 1), 0.4, RULE),
                               ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
    story = [Spacer(1, 14 * mm), Paragraph("INDEPENDENT RESEARCH &middot; LISTED SHIPPING EQUITIES", kl),
             Spacer(1, 3 * mm), Paragraph(fm["title"], title), Paragraph(fm["subtitle"], sub),
             Paragraph(f"<b>{fm['author']}</b> &middot; {fm['date']} &middot; "
                       "github.com/ambekarhrush/shipping-long-short-lab", small),
             Spacer(1, 6 * mm)]
    if name == "paper":
        story += [strip, Spacer(1, 6 * mm)]
    else:
        story += [HRFlowable(width="100%", thickness=1.2, color=INK), Spacer(1, 4 * mm)]
    blocks = re.split(r"\n\s*\n", text.strip())
    fig_no = 0
    width = A4[0] - 40 * mm
    for b in blocks:
        b = b.strip()
        if b.startswith("## "):
            story.append(Paragraph(inline(b[3:]), h2))
        elif b.startswith("[Figure"):
            key = re.match(r"\[(Figure \d+)", b).group(1)
            f, cap = FIG[key]
            fig_no += 1
            cap = re.sub(r"^Figure \d+", f"Figure {fig_no}", cap)
            img = Image(str(ROOT / "figures" / f))
            r = width / img.imageWidth
            img.drawWidth, img.drawHeight = width, img.imageHeight * r
            story.append(KeepTogether([Spacer(1, 3), img, Paragraph(cap, small), Spacer(1, 6)]))
        elif b.startswith("|"):
            rows = [[c.strip() for c in ln.strip("|").split("|")] for ln in b.splitlines() if not re.match(r"^\|[-\s|]+\|$", ln)]
            data = [[Paragraph(inline(c), cell) for c in r] for r in rows]
            t = Table(data, colWidths=[width * 0.34] + [width * 0.66 / (len(rows[0]) - 1)] * (len(rows[0]) - 1))
            t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, 0), 0.8, INK), ("LINEBELOW", (0, 1), (-1, -1), 0.3, RULE),
                                   ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 3),
                                   ("BOTTOMPADDING", (0, 0), (-1, -1), 3), ("LEFTPADDING", (0, 0), (-1, -1), 0)]))
            story += [t, Spacer(1, 8)]
        elif re.match(r"^(\* |\d+\. )", b):
            items, numbered = [], b[0].isdigit()
            for it in re.split(r"\n(?=\* |\d+\. )", b):
                it = re.sub(r"^(\* |\d+\. )", "", it).replace("\n", " ")
                items.append(ListItem(Paragraph(inline(re.sub(r"\s+", " ", it)), body), leftIndent=12))
            story.append(ListFlowable(items, bulletType="1" if numbered else "bullet", start="1" if numbered else None,
                                      bulletFontSize=8, leftIndent=14))
        else:
            story.append(Paragraph(inline(re.sub(r"\s+", " ", b)), small if b.startswith("*Independent") else body))

    def footer(c, d):
        c.saveState(); c.setFont("Helvetica", 7.5); c.setFillColor(MUTED)
        c.drawString(20 * mm, 12 * mm, f"{fm['title']} · independent research · not investment advice")
        c.drawRightString(A4[0] - 20 * mm, 12 * mm, str(d.page)); c.restoreState()

    out = ROOT / "paper" / f"{out_name}.pdf"
    SimpleDocTemplate(str(out), pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm,
                      bottomMargin=20 * mm, title=fm["title"], author=fm["author"]).build(story, onFirstPage=footer, onLaterPages=footer)
    print(out)


if __name__ == "__main__":
    build()
    build("research_note", "research_note")
