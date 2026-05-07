#!/usr/bin/env python3
"""Generate 6 synthetic Certificate of Analysis (CoA) PDFs for the Javelin demo.

Pre-printed form layout (typed) with handwritten test values filled in by a
lab analyst — the realistic shape of a commodities CoA document. Designed to
exercise ai_parse_document then ai_extract for downstream tabular extraction.

Output: ./coa_samples/CoA_<commodity>_<lot>.pdf
Run:    python3 generate_coa_samples.py
Deps:   pip install --user reportlab
"""

import os
import random
import math
from datetime import date, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, gray, blue, HexColor
from reportlab.pdfgen import canvas

random.seed(42)

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))


# ---- Handwriting helpers (adapted from the original sample generator) ------

def jitter(v, a=1.5):
    return v + random.uniform(-a, a)


def hand_text(c, x, y, text, font="Courier", size=11, color=black, angle=None):
    """Draw text with slight random offset/rotation to simulate handwriting."""
    c.saveState()
    c.setFillColor(color)
    dx = random.uniform(-1.0, 1.0)
    dy = random.uniform(-0.8, 0.8)
    sz = size + random.uniform(-0.3, 0.3)
    c.setFont(font, sz)
    if angle is None:
        angle = random.uniform(-1.2, 1.2)
    c.translate(x + dx, y + dy)
    c.rotate(angle)
    c.drawString(0, 0, text)
    c.restoreState()


def printed_text(c, x, y, text, font="Helvetica", size=10, color=black, bold=False):
    c.saveState()
    c.setFillColor(color)
    c.setFont(f"{font}-Bold" if bold else font, size)
    c.drawString(x, y, text)
    c.restoreState()


def hline(c, x1, y, x2, color=gray, width=0.5):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(width)
    c.line(x1, y, x2, y)
    c.restoreState()


def hand_underline(c, x, y, width, color=black):
    """Slightly wavy hand-drawn underline."""
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(0.7)
    p = c.beginPath()
    p.moveTo(x, y - 2)
    steps = max(1, int(width / 6))
    for i in range(steps + 1):
        px = x + (i * 6)
        py = y - 2 + random.uniform(-0.4, 0.4)
        p.lineTo(px, py)
    c.drawPath(p)
    c.restoreState()


# ---- CoA spec data --------------------------------------------------------

LABS = [
    ("ASTRA Commodities Lab",        "Houston, TX",    "ISO/IEC 17025:2017"),
    ("Mercator Analytical Services", "Rotterdam, NL",  "ISO/IEC 17025:2017"),
    ("Ridgeline Inspection Group",   "Singapore",       "ISO/IEC 17025:2017"),
]

COMMODITIES = [
    {
        "name": "Arabica Coffee — Green Beans",
        "origin": "Brazil — Cerrado Mineiro",
        "grade": "Specialty Grade — Strictly Soft",
        "tests": [
            ("Moisture",            "ISO 6673",    lambda: f"{random.uniform(10.5, 12.0):.1f}",  "%",     "≤ 12.5"),
            ("Bulk Density",        "ICO 5/2002",  lambda: f"{random.uniform(660, 720):.0f}",     "g/L",   "650 – 730"),
            ("Defect Count (300g)", "SCA Method",  lambda: f"{random.randint(2, 7)}",             "count", "≤ 8"),
            ("Screen Size 17/18",   "ISO 4150",    lambda: f"{random.uniform(82, 95):.0f}",       "%",     "≥ 80"),
            ("Cup Score",           "SCA Cupping", lambda: f"{random.uniform(84.5, 87.5):.2f}",   "pts",   "≥ 80"),
        ],
    },
    {
        "name": "Cocoa Beans — Fermented",
        "origin": "Côte d'Ivoire — San Pedro",
        "grade": "Grade I — Main Crop",
        "tests": [
            ("Moisture",        "ISO 2291",     lambda: f"{random.uniform(6.8, 7.6):.1f}",   "%",     "≤ 8.0"),
            ("Fat Content",     "ISO 23275",    lambda: f"{random.uniform(53, 56):.1f}",     "%",     "≥ 50"),
            ("Fermentation",    "Cut Test",     lambda: f"{random.randint(86, 96)}",         "%",     "≥ 85"),
            ("Mouldy Beans",    "Cut Test",     lambda: f"{random.uniform(0.5, 2.5):.1f}",   "%",     "≤ 3.0"),
            ("Bean Count/100g", "ISO 2451",     lambda: f"{random.randint(95, 110)}",        "count", "100 ± 10"),
        ],
    },
    {
        "name": "Hard Red Spring Wheat",
        "origin": "USA — North Dakota",
        "grade": "U.S. No. 1 HRS — 14% Protein",
        "tests": [
            ("Moisture",        "AACC 44-15",  lambda: f"{random.uniform(11.5, 13.0):.1f}", "%",   "≤ 14.0"),
            ("Protein (12% mb)","AACC 46-30",  lambda: f"{random.uniform(13.8, 14.6):.1f}", "%",   "≥ 13.5"),
            ("Falling Number",  "AACC 56-81",  lambda: f"{random.randint(330, 410)}",       "sec", "≥ 300"),
            ("Test Weight",     "AACC 55-10",  lambda: f"{random.uniform(60.5, 62.5):.1f}", "lb/bu","≥ 60.0"),
            ("Wet Gluten",      "ICC 137",     lambda: f"{random.uniform(30, 34):.1f}",     "%",   "≥ 28"),
        ],
    },
    {
        "name": "Soybeans — IP Non-GMO",
        "origin": "USA — Iowa",
        "grade": "U.S. No. 2 Yellow",
        "tests": [
            ("Moisture",       "AOCS Ac 2-41", lambda: f"{random.uniform(11.0, 13.0):.1f}", "%", "≤ 13.5"),
            ("Protein",        "AOCS Ba 4e-93",lambda: f"{random.uniform(34, 37):.1f}",      "%", "≥ 34.0"),
            ("Oil Content",    "AOCS Ba 3-38", lambda: f"{random.uniform(18.5, 20.5):.1f}",  "%", "≥ 18.0"),
            ("Foreign Matter", "FGIS",         lambda: f"{random.uniform(0.5, 1.8):.2f}",    "%", "≤ 2.0"),
            ("Damaged Kernels","FGIS",         lambda: f"{random.uniform(0.8, 2.5):.2f}",    "%", "≤ 3.0"),
        ],
    },
    {
        "name": "Raw Cane Sugar (VHP)",
        "origin": "Brazil — Santos Port",
        "grade": "VHP — Very High Polarization",
        "tests": [
            ("Polarization",  "ICUMSA GS2-3",  lambda: f"{random.uniform(99.20, 99.55):.2f}", "°Z",  "≥ 99.30"),
            ("Color (ICUMSA)","ICUMSA GS1-7",  lambda: f"{random.randint(680, 1100)}",         "IU",  "≤ 1200"),
            ("Moisture",      "ICUMSA GS2-9",  lambda: f"{random.uniform(0.07, 0.15):.2f}",   "%",   "≤ 0.20"),
            ("Ash",           "ICUMSA GS1-15", lambda: f"{random.uniform(0.10, 0.18):.2f}",   "%",   "≤ 0.25"),
            ("Reducing Sugar","ICUMSA GS1-2",  lambda: f"{random.uniform(0.40, 0.65):.2f}",   "%",   "≤ 0.80"),
        ],
    },
    {
        "name": "Aluminum Ingot — P1020A",
        "origin": "UAE — Khalifa Port",
        "grade": "LME P1020A — 99.70% min",
        "tests": [
            ("Aluminum Purity", "ASTM E1251", lambda: f"{random.uniform(99.72, 99.86):.3f}", "%",   "≥ 99.70"),
            ("Iron (Fe)",       "ASTM E1251", lambda: f"{random.uniform(0.06, 0.13):.3f}",   "%",   "≤ 0.20"),
            ("Silicon (Si)",    "ASTM E1251", lambda: f"{random.uniform(0.03, 0.09):.3f}",   "%",   "≤ 0.10"),
            ("Copper (Cu)",     "ASTM E1251", lambda: f"{random.uniform(0.001, 0.006):.4f}", "%",   "≤ 0.010"),
            ("Zinc (Zn)",       "ASTM E1251", lambda: f"{random.uniform(0.005, 0.018):.4f}", "%",   "≤ 0.030"),
        ],
    },
]

ANALYSTS = [
    "M. Okafor",  "K. Hashimoto", "J. Pereira", "A. Volkov",
    "S. Patel",   "L. Rasmussen", "G. Mendoza", "R. Singh",
]


# ---- Drawing logic --------------------------------------------------------

def draw_letterhead(c, lab):
    name, location, accred = lab
    printed_text(c, 0.6 * inch, 10.3 * inch, name, size=16, bold=True)
    printed_text(c, 0.6 * inch, 10.0 * inch, f"{location}  ·  Accredited: {accred}",
                 size=9, color=gray)
    hline(c, 0.6 * inch, 9.85 * inch, 7.9 * inch, color=black, width=1.0)
    printed_text(c, 0.6 * inch, 9.55 * inch, "CERTIFICATE OF ANALYSIS",
                 size=14, bold=True)


def draw_field(c, x, y, label, value, label_w=85, font="Courier"):
    """Pre-printed label + handwritten value."""
    printed_text(c, x, y, label, size=9, color=gray)
    hand_text(c, x + label_w, y, value, font=font, size=11)


def draw_test_table(c, x, y, tests):
    headers = [("Test / Parameter", 0), ("Method", 165), ("Result", 270),
               ("Units", 335), ("Specification", 395)]
    for label, dx in headers:
        printed_text(c, x + dx, y, label, size=9, bold=True, color=black)
    hline(c, x, y - 4, x + 480, color=black, width=0.7)

    row_y = y - 22
    for tname, method, value_fn, units, spec in tests:
        printed_text(c, x, row_y, tname, size=10)
        printed_text(c, x + 165, row_y, method, size=9, color=gray)
        # Handwritten value
        hand_text(c, x + 270, row_y, value_fn(), size=11, font="Courier-Bold")
        printed_text(c, x + 335, row_y, units, size=9)
        printed_text(c, x + 395, row_y, spec, size=9, color=gray)
        hline(c, x, row_y - 6, x + 480, color=HexColor("#dddddd"), width=0.3)
        row_y -= 24


def draw_signature_block(c, x, y, analyst):
    today = date.today() - timedelta(days=random.randint(0, 14))
    printed_text(c, x, y, "Analyst signature", size=9, color=gray)
    hand_text(c, x, y - 26, analyst, font="Times-Italic", size=14)
    hand_underline(c, x - 4, y - 28, 130)

    printed_text(c, x + 250, y, "Date", size=9, color=gray)
    hand_text(c, x + 250, y - 26, today.strftime("%d / %m / %Y"),
              font="Courier", size=12)
    hand_underline(c, x + 246, y - 28, 130)


def make_coa(commodity, lab, analyst, idx):
    safe_name = commodity["name"].split("—")[0].strip().replace(" ", "_")
    lot = f"LOT-{random.randint(1000, 9999)}-{chr(ord('A')+idx)}"
    contract = f"JVLN-{random.choice(['CC','CO','WH','SB','SU','AL'])}-2026-{random.randint(100, 999)}"
    sample_id = f"S-{random.randint(10000, 99999)}"
    received = date.today() - timedelta(days=random.randint(8, 25))
    sampled  = received - timedelta(days=random.randint(2, 7))

    filename = f"CoA_{safe_name}_{lot}.pdf"
    path = os.path.join(OUTPUT_DIR, filename)
    c = canvas.Canvas(path, pagesize=letter)

    draw_letterhead(c, lab)

    # Sample / shipment info block
    block_y = 9.0 * inch
    draw_field(c, 0.6 * inch, block_y,             "Lot No.:",       lot)
    draw_field(c, 4.4 * inch, block_y,             "Sample ID:",     sample_id, label_w=70)
    draw_field(c, 0.6 * inch, block_y - 0.30 * inch,"Contract Ref:", contract,  label_w=85)
    draw_field(c, 4.4 * inch, block_y - 0.30 * inch,"Sampled:",      sampled.strftime("%d-%b-%Y"), label_w=70)
    draw_field(c, 0.6 * inch, block_y - 0.60 * inch,"Received:",     received.strftime("%d-%b-%Y"))
    draw_field(c, 4.4 * inch, block_y - 0.60 * inch,"Lab Ref:",      f"R-{random.randint(20000,99999)}", label_w=70)

    # Product info block
    prod_y = block_y - 1.2 * inch
    printed_text(c, 0.6 * inch, prod_y, "PRODUCT", size=10, bold=True, color=black)
    hline(c, 0.6 * inch, prod_y - 4, 7.9 * inch, color=black, width=0.7)
    draw_field(c, 0.6 * inch, prod_y - 0.30 * inch, "Commodity:", commodity["name"], label_w=85)
    draw_field(c, 0.6 * inch, prod_y - 0.55 * inch, "Origin:",    commodity["origin"], label_w=85)
    draw_field(c, 0.6 * inch, prod_y - 0.80 * inch, "Grade:",     commodity["grade"], label_w=85)

    # Test results
    tests_y = prod_y - 1.6 * inch
    printed_text(c, 0.6 * inch, tests_y, "ANALYTICAL RESULTS", size=10, bold=True)
    hline(c, 0.6 * inch, tests_y - 4, 7.9 * inch, color=black, width=0.7)
    draw_test_table(c, 0.6 * inch, tests_y - 0.4 * inch, commodity["tests"])

    # Signature
    sig_y = 1.5 * inch
    draw_signature_block(c, 0.6 * inch, sig_y, analyst)

    # Footer
    printed_text(c, 0.6 * inch, 0.5 * inch,
                 f"This certificate refers solely to the sample analyzed.  Page 1 of 1",
                 size=7, color=gray)

    c.showPage()
    c.save()
    return filename


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    generated = []
    for i, commodity in enumerate(COMMODITIES):
        lab = LABS[i % len(LABS)]
        analyst = ANALYSTS[i % len(ANALYSTS)]
        fname = make_coa(commodity, lab, analyst, i)
        generated.append(fname)
        print(f"  ✓ {fname}")
    print(f"\nGenerated {len(generated)} CoA PDFs in {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
