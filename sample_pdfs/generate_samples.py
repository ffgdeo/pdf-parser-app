#!/usr/bin/env python3
"""Generate 5 sample PDFs that simulate handwritten notes."""

import random
import math
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.colors import black, gray, red, blue, darkblue, HexColor
from reportlab.pdfgen import canvas

random.seed(42)

OUTPUT_DIR = "/Users/filipe.deo/projects/pdf-parser-app/sample_pdfs"

# Helpers for handwriting simulation
def jitter(val, amount=2):
    return val + random.uniform(-amount, amount)

def hand_text(c, x, y, text, font="Courier", size=11, color=black, angle=None):
    """Draw text with slight random offset and optional rotation to simulate handwriting."""
    c.saveState()
    c.setFillColor(color)
    dx = random.uniform(-1.5, 1.5)
    dy = random.uniform(-1.0, 1.0)
    sz = size + random.uniform(-0.3, 0.3)
    c.setFont(font, sz)
    if angle is None:
        angle = random.uniform(-1.2, 1.2)
    c.translate(x + dx, y + dy)
    c.rotate(angle)
    c.drawString(0, 0, text)
    c.restoreState()

def draw_strikethrough(c, x, y, width, color=black):
    """Draw a wavy strikethrough line."""
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(1.2)
    p = c.beginPath()
    p.moveTo(x - 2, y + 4)
    steps = int(width / 4)
    for i in range(steps):
        px = x + (i * 4)
        py = y + 4 + random.uniform(-1.5, 1.5)
        p.lineTo(px, py)
    p.lineTo(x + width + 2, y + 4 + random.uniform(-1, 1))
    c.drawPath(p)
    c.restoreState()

def draw_checkbox(c, x, y, checked=False):
    """Draw a hand-drawn checkbox."""
    c.saveState()
    c.setStrokeColor(black)
    c.setLineWidth(0.8)
    size = 10
    # Slightly irregular box
    c.line(x + jitter(0, 1), y + jitter(0, 1), x + size + jitter(0, 1), y + jitter(0, 1))
    c.line(x + size + jitter(0, 1), y + jitter(0, 1), x + size + jitter(0, 1), y + size + jitter(0, 1))
    c.line(x + size + jitter(0, 1), y + size + jitter(0, 1), x + jitter(0, 1), y + size + jitter(0, 1))
    c.line(x + jitter(0, 1), y + size + jitter(0, 1), x + jitter(0, 1), y + jitter(0, 1))
    if checked:
        c.setLineWidth(1.5)
        c.line(x + 2, y + 5, x + 4, y + 2)
        c.line(x + 4, y + 2, x + 9, y + 9)
    c.restoreState()

def draw_underline(c, x, y, width, color=black):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(0.7)
    p = c.beginPath()
    p.moveTo(x, y - 2)
    steps = int(width / 6)
    for i in range(steps + 1):
        px = x + (i * 6)
        py = y - 2 + random.uniform(-0.5, 0.5)
        p.lineTo(px, py)
    c.drawPath(p)
    c.restoreState()

def draw_arrow(c, x1, y1, x2, y2, color=black):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(1.0)
    c.line(x1, y1, x2, y2)
    angle = math.atan2(y2 - y1, x2 - x1)
    arrow_len = 8
    c.line(x2, y2, x2 - arrow_len * math.cos(angle - 0.4), y2 - arrow_len * math.sin(angle - 0.4))
    c.line(x2, y2, x2 - arrow_len * math.cos(angle + 0.4), y2 - arrow_len * math.sin(angle + 0.4))
    c.restoreState()

def draw_circle_around(c, x, y, w, h, color=red):
    """Draw a rough circle/ellipse around an area."""
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(1.0)
    cx, cy = x + w / 2, y + h / 2
    rx, ry = w / 2 + 5, h / 2 + 5
    p = c.beginPath()
    steps = 30
    for i in range(steps + 1):
        t = 2 * math.pi * i / steps
        px = cx + (rx + random.uniform(-2, 2)) * math.cos(t)
        py = cy + (ry + random.uniform(-2, 2)) * math.sin(t)
        if i == 0:
            p.moveTo(px, py)
        else:
            p.lineTo(px, py)
    c.drawPath(p)
    c.restoreState()

def draw_horizontal_line(c, x, y, width, color=gray):
    c.saveState()
    c.setStrokeColor(color)
    c.setLineWidth(0.3)
    c.setDash(1, 2)
    c.line(x, y, x + width, y)
    c.restoreState()


# ============================================================
# 1. Field Inspection Notes
# ============================================================
def create_field_inspection():
    path = f"{OUTPUT_DIR}/field_inspection_notes.pdf"
    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter

    # Title area
    hand_text(c, 72, h - 60, "FIELD INSPECTION NOTES", size=16, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, h - 62, 280, darkblue)

    y = h - 95
    hand_text(c, 72, y, "Date: 03/14/2026", size=12)
    hand_text(c, 350, y, "Inspector: R. Vasquez", size=11)
    y -= 20
    hand_text(c, 72, y, "Address: 4817 Oakmont Dr, Unit 3B", size=12)
    y -= 18
    hand_text(c, 72, y, "         Portland, OR 97203", size=12)
    y -= 18
    hand_text(c, 72, y, "Property Type: Commercial / Mixed-Use", size=11)
    y -= 18
    hand_text(c, 72, y, "Permit #: BLD-2026-04481", size=11)

    y -= 35
    hand_text(c, 72, y, "STRUCTURAL OBSERVATIONS", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 240, darkblue)

    observations = [
        "- NE corner foundation: hairline crack observed",
        "  crack width: ~3mm  (measured w/ feeler gauge)",
        "  crack length: approx 18in, diagonal pattern",
        "- Load bearing wall (west side) - OK",
        "- Floor joists 2nd floor - slight deflection noted",
        "  measured ~1/4in sag over 12ft span",
        "- Roof truss connections: all appear secure",
        "- Basement wall: efflorescence visible, no active leak",
    ]

    y -= 25
    for line in observations:
        hand_text(c, 85, y, line, size=10)
        y -= 17

    # Margin note about the crack
    hand_text(c, 430, h - 235, "** could be", size=9, color=red, angle=-3)
    hand_text(c, 430, h - 248, "settling issue", size=9, color=red, angle=-2)
    hand_text(c, 430, h - 261, "- recheck in 6mo", size=9, color=red, angle=-4)

    # Checkboxes section
    y -= 25
    hand_text(c, 72, y, "INSPECTION CHECKLIST", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 210, darkblue)

    checklist = [
        ("Foundation intact", True),
        ("Load bearing walls", True),
        ("Roof structure", True),
        ("Electrical rough-in", False),
        ("Plumbing rough-in", True),
        ("Fire stops installed", False),
        ("Egress windows", True),
        ("Ventilation adequate", True),
    ]

    y -= 25
    col1_x, col2_x = 90, 320
    for i, (item, checked) in enumerate(checklist):
        xi = col1_x if i < 4 else col2_x
        yi = y - (i % 4) * 22
        draw_checkbox(c, xi, yi - 3, checked)
        status = "PASS" if checked else "FAIL"
        hand_text(c, xi + 16, yi, f"{item}", size=10)
        color = HexColor("#006600") if checked else red
        hand_text(c, xi + 180, yi, status, size=10, color=color)

    y = y - 4 * 22 - 30

    # Measurements table
    hand_text(c, 72, y, "MEASUREMENTS & QUANTITIES", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 260, darkblue)

    y -= 22
    hand_text(c, 85, y, "Item", size=10, font="Courier-Bold")
    hand_text(c, 280, y, "Measurement", size=10, font="Courier-Bold")
    hand_text(c, 430, y, "Notes", size=10, font="Courier-Bold")
    draw_horizontal_line(c, 85, y - 5, 440)

    measurements = [
        ("Ceiling height (1F)", '9ft 2in', "OK"),
        ("Ceiling height (2F)", '8ft 4in', "OK - min 7ft6"),
        ("Stairway width", '36.5in', "meets code"),
        ("Handrail height", '34in', "min 34in - barely"),
        ("Window sill (bedroom)", '28in', "need 24in max - FAIL"),
        ("Concrete PSI test", '700 psi', "spec: 3000 min !!"),
        ("Beam span (kitchen)", '14ft 3in', "check load calcs"),
    ]

    for item, meas, note in measurements:
        y -= 18
        hand_text(c, 85, y, item, size=10)
        hand_text(c, 280, y, meas, size=10)
        ncolor = red if "FAIL" in note or "!!" in note else black
        hand_text(c, 430, y, note, size=9, color=ncolor)

    # Circled note about 700 psi
    draw_circle_around(c, 275, y + 17, 75, 16, red)
    hand_text(c, 360, y + 6, "<-- verify! 700 or 100??", size=9, color=red, angle=-1)

    y -= 35
    hand_text(c, 72, y, "SUMMARY / NEXT STEPS", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 220, darkblue)
    y -= 22
    hand_text(c, 85, y, "1. Electrical rough-in needs re-inspection after corrections", size=10)
    y -= 17
    hand_text(c, 85, y, "2. Fire stops must be installed before drywall", size=10)
    y -= 17
    hand_text(c, 85, y, "3. Window sill height in bedroom - must be corrected", size=10)
    y -= 17
    hand_text(c, 85, y, "4. Concrete PSI reading questionable - retest req'd", size=10, color=red)
    y -= 17
    hand_text(c, 85, y, "5. Schedule follow-up: on or before 04/01/2026", size=10)

    y -= 40
    hand_text(c, 72, y, "Inspector Signature: R. Vasquez", size=11, font="Courier-Oblique")
    hand_text(c, 350, y, "Date: 03/14/2026", size=11)

    c.save()
    print(f"  Created: {path}")


# ============================================================
# 2. Patient Intake Form
# ============================================================
def create_patient_intake():
    path = f"{OUTPUT_DIR}/patient_intake_form.pdf"
    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter

    # Header
    hand_text(c, 180, h - 55, "PATIENT INTAKE FORM", size=16, font="Courier-Bold", color=darkblue)
    draw_underline(c, 180, h - 57, 230, darkblue)
    hand_text(c, 72, h - 75, "Greenfield Family Medicine", size=11, color=gray)
    hand_text(c, 72, h - 88, "1200 Elm Street, Suite 204, Denver, CO 80202", size=9, color=gray)

    y = h - 115
    # Patient info section
    hand_text(c, 72, y, "PATIENT INFORMATION", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 210, darkblue)

    fields = [
        ("Name:", "Margaret (Maggie) Chen"),
        ("Date of Birth:", "08/23/1974"),
        ("Phone:", "(303) 555-0147"),
        ("Email:", "m.chen74@gmail.com"),
        ("Emergency Contact:", "David Chen (husband) - (303) 555-0192"),
        ("Insurance:", "Blue Cross PPO  ID# XKR-8841207"),
        ("Today's Date:", "03/20/2026"),
        ("Referring Dr:", "self-referred"),
    ]

    y -= 22
    for label, value in fields:
        hand_text(c, 85, y, label, size=10, font="Courier-Bold")
        hand_text(c, 210, y, value, size=10)
        draw_horizontal_line(c, 210, y - 4, 310)
        y -= 19

    y -= 15
    hand_text(c, 72, y, "CURRENT SYMPTOMS / CHIEF COMPLAINT", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 340, darkblue)

    symptoms = [
        "- persistent headaches for ~3 weeks",
        "  (mostly behind eyes, worse in morning)",
        "- occasional dizziness when standing up fast",
        "- fatigue / low energy past month",
        "- mild nausea, no vomiting",
        "- blurry vision intermittent (L eye?)",
        "- sleeping poorly, waking at 3-4am",
    ]
    y -= 22
    for s in symptoms:
        hand_text(c, 85, y, s, size=10)
        y -= 16

    # Margin note
    hand_text(c, 440, h - 310, "BP was", size=9, color=red, angle=-5)
    hand_text(c, 440, h - 322, "148/92 !!", size=10, color=red, angle=-3)
    hand_text(c, 440, h - 335, "recheck", size=9, color=red, angle=-2)

    y -= 12
    hand_text(c, 72, y, "CURRENT MEDICATIONS", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 220, darkblue)

    meds = [
        "1. Lisinopril 10mg - daily (blood pressure)",
        "2. Vitamin D3 2000 IU - daily",
        "3. Ibuprofen 400mg - as needed (headaches)",
        "4. Melatonin 5mg - at bedtime (started recently)",
    ]
    y -= 20
    for m in meds:
        hand_text(c, 85, y, m, size=10)
        y -= 17

    # Strikethrough on a previous med
    y -= 3
    hand_text(c, 85, y, "5. Atorvastatin 20mg - discontinued 01/2026", size=10, color=gray)
    draw_strikethrough(c, 85, y, 340)

    y -= 25
    hand_text(c, 72, y, "ALLERGIES", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 100, darkblue)
    y -= 20
    hand_text(c, 85, y, "- Penicillin (rash, hives)", size=10, color=red)
    y -= 16
    hand_text(c, 85, y, "- Sulfa drugs (GI upset)", size=10, color=red)
    y -= 16
    hand_text(c, 85, y, "- No known food allergies", size=10)

    y -= 25
    hand_text(c, 72, y, "MEDICAL HISTORY", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 170, darkblue)
    history = [
        "- Hypertension (diagnosed 2019)",
        "- Appendectomy (2005)",
        "- Gestational diabetes (2008, resolved)",
        "- Family hx: father - stroke at 62",
        "            mother - type 2 diabetes",
    ]
    y -= 20
    for h_item in history:
        hand_text(c, 85, y, h_item, size=10)
        y -= 16

    y -= 20
    hand_text(c, 72, y, "DOCTOR'S NOTES", size=12, font="Courier-Bold", color=blue)
    draw_underline(c, 72, y - 2, 150, blue)
    y -= 20
    hand_text(c, 85, y, "- order CBC, CMP, TSH, lipid panel", size=10, color=blue)
    y -= 16
    hand_text(c, 85, y, "- schedule ophthalmology referral", size=10, color=blue)
    y -= 16
    hand_text(c, 85, y, "- consider increasing Lisinopril to 20mg", size=10, color=blue)
    y -= 16
    hand_text(c, 85, y, "- follow up in 2 weeks to review labs", size=10, color=blue)
    draw_circle_around(c, 80, y - 5, 290, 18, red)

    y -= 30
    hand_text(c, 72, y, "Patient Signature: M. Chen", size=11, font="Courier-Oblique")
    hand_text(c, 350, y, "Date: 03/20/2026", size=11)

    c.save()
    print(f"  Created: {path}")


# ============================================================
# 3. Meeting Notes
# ============================================================
def create_meeting_notes():
    path = f"{OUTPUT_DIR}/meeting_notes.pdf"
    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter

    hand_text(c, 72, h - 55, "MEETING NOTES", size=16, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, h - 57, 170, darkblue)

    y = h - 85
    hand_text(c, 72, y, "Date: Wednesday, March 18, 2026", size=11)
    y -= 18
    hand_text(c, 72, y, "Time: 2:00 PM - 3:15 PM", size=11)
    y -= 18
    hand_text(c, 72, y, "Location: Conf Room B / Zoom (hybrid)", size=11)
    y -= 18
    hand_text(c, 72, y, "Project: Atlas Platform Redesign - Sprint 14 Review", size=11)

    y -= 28
    hand_text(c, 72, y, "ATTENDEES", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 110, darkblue)
    attendees = [
        "Sarah Kim (PM) - facilitator",
        "Dev Patel (Eng Lead)",
        "Rachel Torres (UX)",
        "James O'Brien (Backend)",
        "Lisa Wang (QA) - remote",
        "Tom Bradley (Stakeholder) - joined late ~2:20",
    ]
    y -= 20
    for a in attendees:
        hand_text(c, 90, y, "- " + a, size=10)
        y -= 16

    y -= 18
    hand_text(c, 72, y, "AGENDA & DISCUSSION", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 210, darkblue)

    y -= 22
    hand_text(c, 80, y, "1. Sprint 13 Retrospective", size=11, font="Courier-Bold")
    y -= 18
    hand_text(c, 95, y, "- Auth module delivered on time", size=10)
    y -= 16
    hand_text(c, 95, y, "- Dashboard redesign slipped 3 days", size=10)
    # Margin note
    hand_text(c, 430, y + 8, "why?", size=10, color=red, angle=-5)
    y -= 16
    hand_text(c, 110, y, "=> dependency on design assets (Rachel)", size=10, color=blue)
    draw_arrow(c, 105, y + 5, 95, y + 18, blue)
    y -= 16
    hand_text(c, 95, y, "- API performance tests passed (97th pctl < 200ms)", size=10)

    y -= 22
    hand_text(c, 80, y, "2. Sprint 14 Planning", size=11, font="Courier-Bold")
    y -= 18
    hand_text(c, 95, y, "- User profile page (8 story pts) -> Dev + James", size=10)
    y -= 16
    hand_text(c, 95, y, "- Search functionality (13 pts) -> Dev", size=10)
    y -= 3
    # Cross out and correction
    hand_text(c, 95, y - 13, "- Notification system (5 pts) -> Lisa", size=10, color=gray)
    draw_strikethrough(c, 95, y - 13, 290)
    y -= 16
    hand_text(c, 95, y - 13, "  ^^ MOVED to Sprint 15 per Tom's request", size=9, color=red)
    y -= 30
    hand_text(c, 95, y, "- Payment integration research (3 pts) -> James", size=10)
    y -= 16
    hand_text(c, 95, y, "- UX audit of onboarding flow (5 pts) -> Rachel", size=10)

    y -= 22
    hand_text(c, 80, y, "3. Blockers & Risks", size=11, font="Courier-Bold")
    y -= 18
    hand_text(c, 95, y, "- Staging environment unstable (DevOps ticket #4412)", size=10)
    y -= 16
    hand_text(c, 95, y, "- 3rd party API rate limits hitting us in testing", size=10)
    y -= 16
    hand_text(c, 110, y, "=> James to talk to vendor about enterprise tier", size=10, color=blue)
    y -= 16
    hand_text(c, 95, y, "- Design system migration still incomplete", size=10)

    y -= 25
    hand_text(c, 72, y, "ACTION ITEMS", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 140, darkblue)

    actions = [
        ("Sarah", "Update Jira board w/ sprint 14 stories", "03/19"),
        ("Dev", "Set up branch + CI for search feature", "03/20"),
        ("Rachel", "Deliver profile page mockups", "03/21"),
        ("James", "Contact API vendor re: rate limits", "03/19"),
        ("Lisa", "Write test plan for profile + search", "03/22"),
        ("Tom", "Approve revised timeline for notifications", "03/25"),
    ]

    y -= 20
    hand_text(c, 90, y, "Owner", size=10, font="Courier-Bold")
    hand_text(c, 170, y, "Task", size=10, font="Courier-Bold")
    hand_text(c, 460, y, "Due", size=10, font="Courier-Bold")
    draw_horizontal_line(c, 85, y - 5, 430)

    for owner, task, due in actions:
        y -= 18
        draw_checkbox(c, 85, y - 3, False)
        hand_text(c, 100, y, owner, size=10)
        hand_text(c, 170, y, task, size=9)
        hand_text(c, 460, y, due, size=10)

    y -= 30
    hand_text(c, 72, y, "Next meeting: Friday 03/20 @ 10am (standup)", size=10, font="Courier-Oblique")

    # Doodle in corner - small box
    hand_text(c, 480, h - 60, "pg 1/1", size=8, color=gray)

    c.save()
    print(f"  Created: {path}")


# ============================================================
# 4. Inventory Count Sheet
# ============================================================
def create_inventory_count():
    path = f"{OUTPUT_DIR}/inventory_count_sheet.pdf"
    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter

    hand_text(c, 72, h - 55, "WAREHOUSE INVENTORY COUNT SHEET", size=15, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, h - 57, 370, darkblue)

    y = h - 85
    hand_text(c, 72, y, "Date: 03/22/2026", size=11)
    hand_text(c, 280, y, "Warehouse: Distribution Center #3 (Bldg A)", size=10)
    y -= 18
    hand_text(c, 72, y, "Counted by: M. Rodriguez / T. Nguyen", size=11)
    hand_text(c, 380, y, "Shift: Day (6am-2pm)", size=10)
    y -= 18
    hand_text(c, 72, y, "Cycle Count #: CC-2026-0087", size=11)

    y -= 30
    # Column headers
    headers = [
        (75, "Item Code"),
        (155, "Description"),
        (310, "Location"),
        (385, "System Qty"),
        (455, "Counted"),
        (510, "Variance"),
    ]
    for hx, hlabel in headers:
        hand_text(c, hx, y, hlabel, size=9, font="Courier-Bold")
    draw_horizontal_line(c, 72, y - 5, 470)

    items = [
        ("WH-10042", "Hex Bolt M8x30 (box/100)", "A-04-12", "850", "847", "-3"),
        ("WH-10043", "Hex Bolt M8x50 (box/100)", "A-04-13", "600", "601", "+1"),
        ("WH-10108", "Flat Washer M10 (bag/500)", "A-06-02", "1200", "1180", "-20"),
        ("WH-10215", "Cable Tie 300mm (bag/100)", "B-01-07", "450", None, None),  # correction
        ("WH-10287", "PVC Elbow 90deg 1/2in", "B-03-15", "320", "318", "-2"),
        ("WH-10301", "Copper Pipe 1/2in x 10ft", "C-01-01", "75", "74", "-1"),
        ("WH-10302", "Copper Pipe 3/4in x 10ft", "C-01-02", "48", "48", "0"),
        ("WH-10450", "LED Panel 2x4ft", "D-02-08", "160", "157", "-3"),
        ("WH-10451", "LED Panel 2x2ft", "D-02-09", "200", None, None),  # correction
        ("WH-10520", "Safety Goggles (box/12)", "E-01-03", "36", "36", "0"),
        ("WH-10611", "Duct Tape 2in (case/24)", "E-03-11", "84", "81", "-3"),
        ("WH-10750", "Wire Nut Lg (bag/100)", "F-01-04", "500", "493", "-7"),
        ("WH-10880", "Conduit 1in EMT 10ft", "G-02-01", "110", "108", "-2"),
        ("WH-10995", "Junction Box 4x4", "G-04-12", "225", "220", "-5"),
    ]

    y -= 5
    for code, desc, loc, sys_qty, counted, var in items:
        y -= 18
        hand_text(c, 75, y, code, size=9)
        # Truncate desc if too long
        hand_text(c, 155, y, desc[:25], size=9)
        hand_text(c, 310, y, loc, size=9)
        hand_text(c, 395, y, sys_qty, size=9)

        if code == "WH-10215":
            # Show correction: first wrote 445, crossed out, wrote 452
            hand_text(c, 455, y, "445", size=9, color=gray)
            draw_strikethrough(c, 455, y, 22)
            hand_text(c, 480, y, "452", size=9, color=blue)
            hand_text(c, 510, y, "+2", size=9)
            hand_text(c, 440, y + 12, "recount!", size=8, color=red, angle=-3)
        elif code == "WH-10451":
            # Another correction
            hand_text(c, 455, y, "198", size=9, color=gray)
            draw_strikethrough(c, 455, y, 22)
            hand_text(c, 480, y, "203", size=9, color=blue)
            hand_text(c, 510, y, "+3", size=9)
        else:
            hand_text(c, 460, y, counted, size=9)
            vc = red if var and abs(int(var)) >= 5 else black
            hand_text(c, 515, y, var, size=9, color=vc)

        draw_horizontal_line(c, 72, y - 5, 470)

    # Summary at bottom
    y -= 35
    hand_text(c, 72, y, "COUNT SUMMARY", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 150, darkblue)
    y -= 22
    hand_text(c, 85, y, "Total SKUs counted:   14", size=10)
    y -= 18
    hand_text(c, 85, y, "SKUs with variance:   10", size=10)
    y -= 18
    hand_text(c, 85, y, "SKUs requiring recount: 2  (WH-10215, WH-10451)", size=10, color=red)
    y -= 18
    hand_text(c, 85, y, "Largest variance: WH-10108 (-20 units)", size=10, color=red)
    draw_circle_around(c, 80, y - 5, 310, 18, red)

    y -= 30
    hand_text(c, 85, y, "Notes:", size=10, font="Courier-Bold")
    y -= 16
    hand_text(c, 95, y, "- Aisle A labels faded, hard to read bin numbers", size=10)
    y -= 16
    hand_text(c, 95, y, "- WH-10108 may have been pulled for order #SO-7814", size=10)
    y -= 16
    hand_text(c, 100, y, "before count started - check with shipping", size=10)
    y -= 16
    hand_text(c, 95, y, "- Forklift in aisle G blocked access, came back later", size=10)

    y -= 30
    hand_text(c, 72, y, "Signatures:", size=10, font="Courier-Bold")
    y -= 18
    hand_text(c, 85, y, "Counter 1: M. Rodriguez", size=10, font="Courier-Oblique")
    hand_text(c, 330, y, "Counter 2: T. Nguyen", size=10, font="Courier-Oblique")

    c.save()
    print(f"  Created: {path}")


# ============================================================
# 5. Expense Report
# ============================================================
def create_expense_report():
    path = f"{OUTPUT_DIR}/expense_report.pdf"
    c = canvas.Canvas(path, pagesize=letter)
    w, h = letter

    hand_text(c, 72, h - 55, "EXPENSE REPORT", size=16, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, h - 57, 190, darkblue)

    y = h - 85
    hand_text(c, 72, y, "Employee: Jennifer Park", size=11)
    hand_text(c, 350, y, "Dept: Sales - West Region", size=10)
    y -= 18
    hand_text(c, 72, y, "Employee ID: EMP-04419", size=11)
    hand_text(c, 350, y, "Manager: K. Thompson", size=10)
    y -= 18
    hand_text(c, 72, y, "Period: 03/01/2026 - 03/15/2026", size=11)
    y -= 18
    hand_text(c, 72, y, "Trip: Portland Client Visit + Seattle Conference", size=11)

    y -= 30
    hand_text(c, 72, y, "EXPENSE DETAILS", size=13, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 170, darkblue)

    # Header
    y -= 22
    col_date, col_desc, col_cat, col_amt, col_rcpt = 75, 145, 340, 430, 500
    hand_text(c, col_date, y, "Date", size=9, font="Courier-Bold")
    hand_text(c, col_desc, y, "Description", size=9, font="Courier-Bold")
    hand_text(c, col_cat, y, "Category", size=9, font="Courier-Bold")
    hand_text(c, col_amt, y, "Amount", size=9, font="Courier-Bold")
    hand_text(c, col_rcpt, y, "Rcpt#", size=9, font="Courier-Bold")
    draw_horizontal_line(c, 72, y - 5, 470)

    expenses = [
        ("03/02", "Uber to airport (PDX)", "Transport", "$34.50", "R-01"),
        ("03/02", "Alaska Air PDX->SEA", "Airfare", "$189.00", "R-02"),
        ("03/02", "Hyatt Regency Seattle (2 nights)", "Lodging", "$478.00", "R-03"),
        ("03/03", "Lunch - client meeting (Canlis)", "Meals", "$142.75", "R-04"),
        ("03/03", "Uber to convention center", "Transport", "$18.20", "R-05"),
        ("03/03", "Conference registration", "Conf Fee", "$350.00", "R-06"),
        ("03/04", "Breakfast (hotel restaurant)", "Meals", "$28.50", "R-07"),
        ("03/04", "Lunch (conference venue)", "Meals", "$22.00", "R-08"),
        ("03/04", "Dinner - team (Shiro's Sushi)", "Meals", None, None),  # correction
        ("03/05", "Uber SEA->airport", "Transport", "$31.40", "R-10"),
        ("03/05", "Alaska Air SEA->PDX", "Airfare", "$176.00", "R-11"),
        ("03/05", "Airport parking (3 days)", "Parking", "$72.00", "R-12"),
        ("03/08", "Office supplies (Staples)", "Supplies", "$45.80", "R-13"),
        ("03/10", "Client gift basket", "Client Ent", "$85.00", "R-14"),
        ("03/12", "Uber to client site (local)", "Transport", "$16.50", "R-15"),
    ]

    running_total = 0
    for date, desc, cat, amt, rcpt in expenses:
        y -= 17
        hand_text(c, col_date, y, date, size=9)
        # Truncate desc
        hand_text(c, col_desc, y, desc[:28], size=9)
        hand_text(c, col_cat, y, cat, size=9)

        if desc.startswith("Dinner - team"):
            # Correction: wrote $187.50, crossed out, wrote $167.50
            hand_text(c, col_amt - 5, y, "$187.50", size=9, color=gray)
            draw_strikethrough(c, col_amt - 5, y, 48)
            hand_text(c, col_amt + 40, y, "$167.50", size=9, color=blue)
            hand_text(c, col_rcpt, y, "R-09", size=9)
            hand_text(c, col_amt + 30, y + 11, "tip was less", size=7, color=red, angle=-2)
            running_total += 167.50
        else:
            hand_text(c, col_amt, y, amt, size=9)
            hand_text(c, col_rcpt, y, rcpt, size=9)
            running_total += float(amt.replace("$", "").replace(",", ""))

        draw_horizontal_line(c, 72, y - 4, 470)

    # Totals section
    y -= 28
    draw_horizontal_line(c, 350, y + 8, 120)
    hand_text(c, 340, y, "Subtotal:", size=10, font="Courier-Bold")
    hand_text(c, 430, y, f"${running_total:,.2f}", size=10, font="Courier-Bold")
    y -= 18
    hand_text(c, 340, y, "Company card:", size=10)
    hand_text(c, 430, y, "-$189.00", size=10)
    hand_text(c, 500, y, "(airfare)", size=8, color=gray)
    y -= 16
    hand_text(c, 340, y, "Company card:", size=10)
    hand_text(c, 430, y, "-$176.00", size=10)
    hand_text(c, 500, y, "(airfare)", size=8, color=gray)
    y -= 18
    draw_horizontal_line(c, 350, y + 8, 120)

    reimbursable = running_total - 189.00 - 176.00
    hand_text(c, 340, y, "REIMBURSABLE:", size=11, font="Courier-Bold", color=darkblue)
    hand_text(c, 430, y, f"${reimbursable:,.2f}", size=11, font="Courier-Bold", color=darkblue)

    # Handwritten calculations in margin
    hand_text(c, 480, y + 60, "check:", size=8, color=blue, angle=-3)
    hand_text(c, 478, y + 46, f"{running_total:.2f}", size=8, color=blue, angle=-1)
    hand_text(c, 478, y + 34, "- 365.00", size=8, color=blue, angle=-2)
    hand_text(c, 478, y + 20, f"= {reimbursable:.2f}", size=8, color=blue, angle=-1)
    draw_underline(c, 478, y + 20, 55, blue)

    y -= 35
    hand_text(c, 72, y, "NOTES", size=12, font="Courier-Bold", color=darkblue)
    draw_underline(c, 72, y - 2, 65, darkblue)
    y -= 20
    hand_text(c, 85, y, "- R-04 (Canlis dinner): 3 attendees - client + partner", size=10)
    y -= 16
    hand_text(c, 85, y, "- R-09: original receipt shows $187.50, corrected to $167.50", size=10)
    y -= 16
    hand_text(c, 95, y, "  (auto-gratuity was removed, added manual tip)", size=10)
    y -= 16
    hand_text(c, 85, y, "- R-14: client gift per policy (< $100 limit)", size=10)
    y -= 16
    hand_text(c, 85, y, "- All original receipts attached (15 total)", size=10)

    y -= 35
    hand_text(c, 72, y, "Employee Signature: J. Park", size=11, font="Courier-Oblique")
    hand_text(c, 350, y, "Date: 03/15/2026", size=11)
    y -= 22
    hand_text(c, 72, y, "Manager Approval: _______________", size=11)
    hand_text(c, 350, y, "Date: ___________", size=11)

    c.save()
    print(f"  Created: {path}")


# ============================================================
# Generate all PDFs
# ============================================================
if __name__ == "__main__":
    print("Generating sample handwritten-style PDFs...")
    create_field_inspection()
    create_patient_intake()
    create_meeting_notes()
    create_inventory_count()
    create_expense_report()
    print("\nDone! All 5 PDFs created.")
