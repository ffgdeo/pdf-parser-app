#!/usr/bin/env python3
"""Generate a 3-page Certificate of Analysis for a coffee shipment.

Tests multi-page behavior: the parser should emit blocks across all 3 pages,
each with its own page_number, so the app's focus selector auto-scrolls the
PDF preview to the right page when a block is selected.

Page 1 — header, sample/shipment info, product info, summary results
Page 2 — physical & chemical analysis tables
Page 3 — microbiological tests, sensory cupping, chain of custody, signatures
"""

import os
import random
from datetime import date, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, gray, HexColor
from reportlab.pdfgen import canvas

random.seed(7)

OUTPUT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "CoA_MultiPage_Arabica_Coffee_LOT-MP-2026-001.pdf")

LAB_NAME = "ASTRA Commodities Lab"
LAB_LOCATION = "Houston, TX"
LAB_ACCRED = "ISO/IEC 17025:2017"
ANALYST = "M. Okafor"
LOT = "LOT-MP-2026-001"
CONTRACT = "JVLN-CC-2026-742"
SAMPLE_ID = "S-58472"
LAB_REF = "R-93281"
RECEIVED = date.today() - timedelta(days=12)
SAMPLED = RECEIVED - timedelta(days=4)
SIGNED = date.today() - timedelta(days=2)


def jitter(v, a=1.0):
    return v + random.uniform(-a, a)


def hand_text(c, x, y, text, font="Courier", size=11):
    c.saveState()
    dx = random.uniform(-0.8, 0.8); dy = random.uniform(-0.6, 0.6)
    sz = size + random.uniform(-0.3, 0.3)
    c.setFont(font, sz)
    angle = random.uniform(-1.0, 1.0)
    c.translate(x + dx, y + dy); c.rotate(angle)
    c.drawString(0, 0, text)
    c.restoreState()


def printed(c, x, y, text, size=10, bold=False, color=black):
    c.saveState()
    c.setFillColor(color)
    c.setFont(f"Helvetica-Bold" if bold else "Helvetica", size)
    c.drawString(x, y, text)
    c.restoreState()


def hline(c, x1, y, x2, color=gray, width=0.5):
    c.saveState()
    c.setStrokeColor(color); c.setLineWidth(width)
    c.line(x1, y, x2, y)
    c.restoreState()


def hand_underline(c, x, y, w):
    c.saveState()
    c.setStrokeColor(black); c.setLineWidth(0.7)
    p = c.beginPath(); p.moveTo(x, y - 2)
    steps = max(1, int(w / 6))
    for i in range(steps + 1):
        p.lineTo(x + i * 6, y - 2 + random.uniform(-0.4, 0.4))
    c.drawPath(p)
    c.restoreState()


def draw_letterhead(c, page_no, page_total, title):
    printed(c, 0.6 * inch, 10.3 * inch, LAB_NAME, size=16, bold=True)
    printed(c, 0.6 * inch, 10.0 * inch,
            f"{LAB_LOCATION}  ·  Accredited: {LAB_ACCRED}", size=9, color=gray)
    printed(c, 6.4 * inch, 10.3 * inch,
            f"Cert No.  ASTRA-{LOT}", size=9, color=gray)
    printed(c, 6.4 * inch, 10.15 * inch,
            f"Page {page_no} of {page_total}", size=9, color=gray)
    hline(c, 0.6 * inch, 9.85 * inch, 7.9 * inch, color=black, width=1.0)
    printed(c, 0.6 * inch, 9.55 * inch, title, size=14, bold=True)


def draw_field(c, x, y, label, value, label_w=85, font="Courier"):
    printed(c, x, y, label, size=9, color=gray)
    hand_text(c, x + label_w, y, value, font=font, size=11)


def draw_section_header(c, x, y, text):
    printed(c, x, y, text, size=10, bold=True)
    hline(c, x, y - 4, 7.9 * inch, color=black, width=0.7)


def draw_table(c, x, y, headers_widths, rows):
    """rows: list of (printed_cells_list, hand_cells_indexes_list).
    headers_widths: list of (label, dx) for column positions, matching cell order.
    """
    for label, dx in headers_widths:
        printed(c, x + dx, y, label, size=9, bold=True)
    hline(c, x, y - 4, x + 480, color=black, width=0.7)
    row_y = y - 22
    for cells, hand_idxs in rows:
        for col_i, ((_, dx), val) in enumerate(zip(headers_widths, cells)):
            if col_i in hand_idxs:
                hand_text(c, x + dx, row_y, val, size=11, font="Courier-Bold")
            else:
                color = gray if col_i in (1, 4) else black
                printed(c, x + dx, row_y, val, size=10 if col_i == 0 else 9, color=color)
        hline(c, x, row_y - 6, x + 480, color=HexColor("#dddddd"), width=0.3)
        row_y -= 22
    return row_y


def draw_footer(c, page_no, page_total):
    printed(c, 0.6 * inch, 0.5 * inch,
            f"This certificate refers solely to the sample analyzed.  Page {page_no} of {page_total}",
            size=7, color=gray)


# ---- Page builders ---------------------------------------------------------

def page_1(c, total):
    draw_letterhead(c, 1, total, "CERTIFICATE OF ANALYSIS")

    block_y = 9.0 * inch
    draw_field(c, 0.6 * inch, block_y, "Lot No.:", LOT)
    draw_field(c, 4.4 * inch, block_y, "Sample ID:", SAMPLE_ID, label_w=70)
    draw_field(c, 0.6 * inch, block_y - 0.30 * inch, "Contract Ref:", CONTRACT)
    draw_field(c, 4.4 * inch, block_y - 0.30 * inch, "Sampled:", SAMPLED.strftime("%d-%b-%Y"), label_w=70)
    draw_field(c, 0.6 * inch, block_y - 0.60 * inch, "Received:", RECEIVED.strftime("%d-%b-%Y"))
    draw_field(c, 4.4 * inch, block_y - 0.60 * inch, "Lab Ref:", LAB_REF, label_w=70)

    prod_y = block_y - 1.2 * inch
    draw_section_header(c, 0.6 * inch, prod_y, "PRODUCT")
    draw_field(c, 0.6 * inch, prod_y - 0.30 * inch, "Commodity:", "Arabica Coffee — Green Beans")
    draw_field(c, 0.6 * inch, prod_y - 0.55 * inch, "Origin:",    "Brazil — Cerrado Mineiro")
    draw_field(c, 0.6 * inch, prod_y - 0.80 * inch, "Variety:",   "Yellow Catuaí / Mundo Novo")
    draw_field(c, 0.6 * inch, prod_y - 1.05 * inch, "Process:",   "Pulped Natural")
    draw_field(c, 0.6 * inch, prod_y - 1.30 * inch, "Grade:",     "Specialty — Strictly Soft, Fine Cup")
    draw_field(c, 0.6 * inch, prod_y - 1.55 * inch, "Crop Year:", "2025/2026")

    # Shipment info
    ship_y = prod_y - 2.2 * inch
    draw_section_header(c, 0.6 * inch, ship_y, "SHIPMENT")
    draw_field(c, 0.6 * inch, ship_y - 0.30 * inch, "Bags:",     "320 × 60 kg jute bags")
    draw_field(c, 4.4 * inch, ship_y - 0.30 * inch, "Net wt.:",  "19,200.0 kg", label_w=70)
    draw_field(c, 0.6 * inch, ship_y - 0.55 * inch, "Container:", "MSCU-7384921")
    draw_field(c, 4.4 * inch, ship_y - 0.55 * inch, "Seal:",     "JVLN-552839", label_w=70)

    # Summary results table
    sum_y = ship_y - 1.4 * inch
    draw_section_header(c, 0.6 * inch, sum_y, "SUMMARY RESULTS")
    rows = [
        (["Moisture",          "ISO 6673",     f"{random.uniform(10.5, 11.8):.1f}",  "%",     "≤ 12.5"], {2}),
        (["Bulk Density",      "ICO 5/2002",   f"{random.uniform(670, 705):.0f}",     "g/L",   "650 – 730"], {2}),
        (["Defect Count (300g)", "SCA Method", f"{random.randint(2, 6)}",             "count", "≤ 8"], {2}),
        (["Cup Score (overall)", "SCA Cupping", f"{random.uniform(85.0, 87.5):.2f}",  "pts",   "≥ 80"], {2}),
    ]
    headers = [("Test / Parameter", 0), ("Method", 165), ("Result", 270),
               ("Units", 335), ("Specification", 395)]
    draw_table(c, 0.6 * inch, sum_y - 0.4 * inch, headers, rows)

    # Note pointing forward
    note_y = 1.4 * inch
    printed(c, 0.6 * inch, note_y, "FULL ANALYTICAL PANEL ON FOLLOWING PAGES",
            size=9, bold=True)
    printed(c, 0.6 * inch, note_y - 0.18 * inch,
            "See pages 2–3 for detailed physical, chemical, microbiological and sensory results.",
            size=8, color=gray)

    draw_footer(c, 1, total)


def page_2(c, total):
    draw_letterhead(c, 2, total, "PHYSICAL & CHEMICAL ANALYSIS")

    headers = [("Test / Parameter", 0), ("Method", 165), ("Result", 270),
               ("Units", 335), ("Specification", 395)]

    # Physical
    phys_y = 9.0 * inch
    draw_section_header(c, 0.6 * inch, phys_y, "PHYSICAL TESTS")
    rows = [
        (["Moisture",            "ISO 6673",     f"{random.uniform(10.5, 11.8):.1f}", "%",     "≤ 12.5"], {2}),
        (["Bulk Density",        "ICO 5/2002",   f"{random.uniform(670, 705):.0f}",   "g/L",   "650 – 730"], {2}),
        (["Screen Size 17/18",   "ISO 4150",     f"{random.uniform(85, 94):.0f}",     "%",     "≥ 80"], {2}),
        (["Screen Size 15/16",   "ISO 4150",     f"{random.uniform(4, 10):.0f}",       "%",     "≤ 15"], {2}),
        (["Defect Count (300g)", "SCA Method",   f"{random.randint(2, 6)}",            "count", "≤ 8"], {2}),
        (["Foreign Matter",      "ISO 4149",     f"{random.uniform(0.05, 0.18):.2f}",  "%",     "≤ 0.50"], {2}),
        (["Black/Sour Beans",    "SCA Method",   f"{random.uniform(0.2, 0.9):.1f}",    "%",     "≤ 1.0"], {2}),
    ]
    end_y = draw_table(c, 0.6 * inch, phys_y - 0.4 * inch, headers, rows)

    # Chemical
    chem_y = end_y - 0.5 * inch
    draw_section_header(c, 0.6 * inch, chem_y, "CHEMICAL TESTS")
    rows = [
        (["Caffeine",          "ISO 4052",     f"{random.uniform(1.05, 1.35):.2f}",  "%",     "1.0 – 1.5"], {2}),
        (["Trigonelline",      "HPLC",         f"{random.uniform(0.95, 1.20):.2f}",  "%",     "0.8 – 1.3"], {2}),
        (["Chlorogenic Acids", "HPLC",         f"{random.uniform(5.5, 7.2):.2f}",    "%",     "5.0 – 8.0"], {2}),
        (["Ash",               "ISO 1577",     f"{random.uniform(3.6, 4.3):.2f}",    "%",     "≤ 5.0"], {2}),
        (["Lipids (Oil Content)", "Soxhlet",   f"{random.uniform(13.5, 16.5):.1f}",  "%",     "12 – 18"], {2}),
        (["Pesticides (Total)", "GC-MS/MS",    "Not Detected",                       "—",     "≤ MRL"], set()),
    ]
    draw_table(c, 0.6 * inch, chem_y - 0.4 * inch, headers, rows)

    draw_footer(c, 2, total)


def page_3(c, total):
    draw_letterhead(c, 3, total, "MICROBIOLOGY · SENSORY · CHAIN OF CUSTODY")

    headers = [("Test / Parameter", 0), ("Method", 165), ("Result", 270),
               ("Units", 335), ("Specification", 395)]

    # Microbiology
    micro_y = 9.0 * inch
    draw_section_header(c, 0.6 * inch, micro_y, "MICROBIOLOGICAL TESTS")
    rows = [
        (["Total Plate Count", "ISO 4833-1",  f"{random.randint(800, 4500)}",   "CFU/g",  "≤ 10,000"], {2}),
        (["Yeasts & Moulds",   "ISO 21527-1", f"{random.randint(50, 280)}",     "CFU/g",  "≤ 500"], {2}),
        (["Aflatoxin B1",      "HPLC-FLD",    f"{random.uniform(0.4, 1.9):.1f}", "ppb",    "≤ 5"], {2}),
        (["Aflatoxin Total",   "HPLC-FLD",    f"{random.uniform(1.0, 4.0):.1f}", "ppb",    "≤ 10"], {2}),
        (["Ochratoxin A",      "HPLC-FLD",    f"{random.uniform(0.3, 1.6):.1f}", "ppb",    "≤ 5"], {2}),
        (["Salmonella spp.",   "ISO 6579",    "Not Detected",                    "/25g",   "Absent"], set()),
        (["E. coli",           "ISO 16649-2", "< 10",                            "CFU/g",  "≤ 100"], set()),
    ]
    end_y = draw_table(c, 0.6 * inch, micro_y - 0.4 * inch, headers, rows)

    # Sensory cupping
    cup_y = end_y - 0.5 * inch
    draw_section_header(c, 0.6 * inch, cup_y, "SENSORY EVALUATION (SCA CUPPING)")
    cup_headers = [("Attribute", 0), ("Score", 175), ("Notes", 240)]
    cup_rows = [
        (["Fragrance/Aroma", f"{random.uniform(8.0, 8.75):.2f}", "Caramel, milk chocolate, honey"], {1}),
        (["Flavor",          f"{random.uniform(8.25, 8.75):.2f}", "Brown sugar, almond, citrus finish"], {1}),
        (["Aftertaste",      f"{random.uniform(7.75, 8.5):.2f}", "Lingering sweetness"], {1}),
        (["Acidity",         f"{random.uniform(8.0, 8.5):.2f}", "Bright, malic"], {1}),
        (["Body",            f"{random.uniform(8.0, 8.5):.2f}", "Full, syrupy"], {1}),
        (["Balance",         f"{random.uniform(8.25, 8.75):.2f}", "Harmonious"], {1}),
        (["Overall",         f"{random.uniform(8.25, 8.75):.2f}", "Specialty grade"], {1}),
    ]
    cup_end = draw_table(c, 0.6 * inch, cup_y - 0.4 * inch, cup_headers, cup_rows)

    # Chain of custody
    coc_y = cup_end - 0.4 * inch
    draw_section_header(c, 0.6 * inch, coc_y, "CHAIN OF CUSTODY")
    draw_field(c, 0.6 * inch, coc_y - 0.30 * inch, "Sampled by:",   "T. Almeida (FE-CR-008)")
    draw_field(c, 4.4 * inch, coc_y - 0.30 * inch, "Sealed:",        SAMPLED.strftime("%d-%b-%Y"), label_w=70)
    draw_field(c, 0.6 * inch, coc_y - 0.55 * inch, "Storage:",       "Climate-controlled, 18°C / 55% RH")
    draw_field(c, 4.4 * inch, coc_y - 0.55 * inch, "Tamper seal:",   "Intact", label_w=70)

    # Signatures
    sig_y = 1.6 * inch
    printed(c, 0.6 * inch, sig_y, "Analyst signature", size=9, color=gray)
    hand_text(c, 0.6 * inch, sig_y - 26, ANALYST, font="Times-Italic", size=14)
    hand_underline(c, 0.6 * inch - 4, sig_y - 28, 130)

    printed(c, 4.4 * inch, sig_y, "Date", size=9, color=gray)
    hand_text(c, 4.4 * inch, sig_y - 26, SIGNED.strftime("%d / %m / %Y"),
              font="Courier", size=12)
    hand_underline(c, 4.4 * inch - 4, sig_y - 28, 130)

    draw_footer(c, 3, total)


def main():
    c = canvas.Canvas(OUTPUT, pagesize=letter)
    page_1(c, 3); c.showPage()
    page_2(c, 3); c.showPage()
    page_3(c, 3); c.showPage()
    c.save()
    print(f"Generated 3-page CoA: {OUTPUT}")


if __name__ == "__main__":
    main()
