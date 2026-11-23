"""PDF report generation (fpdf2). Built-in fonts are Latin-1 only, so text is sanitised."""
from datetime import datetime

from fpdf import FPDF

from app.utils.knowledge import clean_disease_name, disease_description, disease_precautions, pretty_symptom
from app.utils.recommend import recommendations

TEAL, INDIGO, SLATE, MUTED = (13, 148, 136), (79, 70, 229), (15, 23, 42), (100, 116, 139)
LEVEL_RGB = {"LOW": (16, 185, 129), "MEDIUM": (245, 158, 11), "HIGH": (239, 68, 68)}
LEVEL_LABEL = {"LOW": "LOW RISK", "MEDIUM": "MODERATE RISK", "HIGH": "HIGH RISK"}

_REPL = {"–": "-", "—": "-", "‘": "'", "’": "'", "“": '"', "”": '"', "·": "|", "≥": ">=", "≤": "<=", "→": "->",
         "←": "<-", "µ": "u", "²": "2", "•": "-", "≈": "~", "×": "x", "…": "...", "÷": "/"}


def _t(s) -> str:
    s = "" if s is None else str(s)
    for k, v in _REPL.items():
        s = s.replace(k, v)
    return s.encode("latin-1", "replace").decode("latin-1")


class _PDF(FPDF):
    def header(self):
        steps = 70  # smooth teal -> indigo gradient band
        for i in range(steps):
            f = i / (steps - 1)
            self.set_fill_color(*(int(TEAL[k] + (INDIGO[k] - TEAL[k]) * f) for k in range(3)))
            self.rect(210 / steps * i, 0, 210 / steps + 0.6, 26, "F")
        self.set_xy(12, 7)
        self.set_text_color(255, 255, 255)
        self.set_font("Helvetica", "B", 18)
        self.cell(0, 8, "MediPredict", new_x="LMARGIN", new_y="NEXT")
        self.set_x(12)
        self.set_font("Helvetica", "", 9)
        self.cell(0, 5, "Explainable AI health screening report")
        self.set_y(32)

    def footer(self):
        self.set_y(-14)
        self.set_font("Helvetica", "I", 7.5)
        self.set_text_color(*MUTED)
        self.multi_cell(0, 3.8, _t("Educational screening estimate - not a medical diagnosis. Consult a qualified clinician. "
                                   f"Page {self.page_no()}"), align="C")


def _h(pdf, text):
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 7, _t(text), new_x="LMARGIN", new_y="NEXT")
    pdf.set_draw_color(*TEAL)
    pdf.set_line_width(0.5)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.l_margin + 28, pdf.get_y())
    pdf.ln(2.5)


def _p(pdf, text, size=9.5, color=SLATE, style=""):
    pdf.set_font("Helvetica", style, size)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, 5, _t(text), new_x="LMARGIN", new_y="NEXT")


def _meta(pdf, user, when):
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(95, 5, _t(f"Patient: {user.get('name', '-')}"))
    pdf.cell(0, 5, _t(f"Generated: {when}"), new_x="LMARGIN", new_y="NEXT")
    bits = [b for b in (f"Age: {user['age']}" if user.get("age") else "", f"Sex: {user['sex']}" if user.get("sex") else "") if b]
    if bits:
        pdf.cell(0, 5, _t("  |  ".join(bits)), new_x="LMARGIN", new_y="NEXT")


def build_risk_pdf(user: dict, result: dict, when: str = None) -> bytes:
    from app.utils.schemas import SPECS
    spec = SPECS[result["disease"]]
    when = when or datetime.now().strftime("%d %b %Y, %H:%M")
    pdf = _PDF(format="A4")
    pdf.set_auto_page_break(True, 18)
    pdf.set_margins(12, 12, 12)
    pdf.add_page()
    _meta(pdf, user, when)

    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 9, _t(spec.title), new_x="LMARGIN", new_y="NEXT")

    # risk banner
    rgb = LEVEL_RGB[result["level"]]
    y = pdf.get_y() + 1
    pdf.set_fill_color(*rgb)
    pdf.rect(12, y, 186, 22, "F")
    pdf.set_xy(16, y + 3)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 24)
    pdf.cell(50, 10, f"{result['risk_pct']:.1f}%")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(60, 10, LEVEL_LABEL[result["level"]])
    pdf.set_font("Helvetica", "", 9)
    pdf.set_xy(16, y + 13)
    pdf.cell(0, 5, _t(f"Model: {result['model_name']}  |  Average patient in dataset: {result['base_pct']:.0f}%"))
    pdf.set_y(y + 26)

    _h(pdf, "What you entered")
    pdf.set_font("Helvetica", "", 9)
    col_w, rows = 93, result["factors"]
    lab_w = 55
    by_key = {f["key"]: f for f in rows}
    for i, f in enumerate(spec.fields):
        fr = by_key.get(f.key, {})
        if i % 2 == 0 and i:
            pdf.ln(5.4)
        pdf.set_text_color(*MUTED)
        pdf.cell(lab_w, 5.4, _t(f.label[:31]))
        pdf.set_text_color(*SLATE)
        pdf.set_font("Helvetica", "B", 9)
        pdf.cell(col_w - lab_w, 5.4, _t(str(fr.get("display", ""))[:22]))
        pdf.set_font("Helvetica", "", 9)
    pdf.ln(7)

    _h(pdf, "Why this result (SHAP explanation)")
    _p(pdf, "Each bar shows how much a factor moved your estimated risk, in percentage points, relative to the average "
            f"patient in the training data ({result['base_pct']:.0f}%). Red raises risk, green lowers it.", 8.5, MUTED)
    pdf.ln(1.5)
    top = [f for f in rows if abs(f["contribution"]) >= 0.05][:8]
    mx = max([abs(f["contribution"]) for f in top] + [1])
    centre, half = 140, 40
    for f in top:
        y = pdf.get_y()
        pdf.set_font("Helvetica", "", 8.5)
        pdf.set_text_color(*SLATE)
        pdf.set_xy(12, y)
        pdf.cell(76, 6, _t(f"{f['label'][:30]}  ({str(f['display'])[:16]})"))
        w = abs(f["contribution"]) / mx * half
        pdf.set_fill_color(*((239, 68, 68) if f["contribution"] > 0 else (16, 185, 129)))
        pdf.rect(centre if f["contribution"] > 0 else centre - w, y + 1, max(w, 0.6), 4, "F")
        pdf.set_xy(centre + (w if f["contribution"] > 0 else 0) + 1.5, y)
        if f["contribution"] < 0:
            pdf.set_xy(centre - w - 14, y)
        pdf.set_text_color(*MUTED)
        pdf.cell(12, 6, f"{f['contribution']:+.1f}")
        pdf.set_y(y + 6.6)
    pdf.set_draw_color(*MUTED)
    pdf.line(centre, pdf.get_y() - len(top) * 6.6 - 1, centre, pdf.get_y())

    if result.get("warnings") or result.get("unknown"):
        _h(pdf, "Data quality notes")
        for w_ in result.get("warnings", []):
            _p(pdf, "- " + w_, 8.5)
        if result.get("unknown"):
            _p(pdf, "- Not provided (typical values assumed): " + ", ".join(result["unknown"]), 8.5)

    _h(pdf, "Guidance")
    for r in recommendations(result["disease"], result["ui_values"], result["level"]):
        pdf.set_font("Helvetica", "B", 9.5)
        pdf.set_text_color(*SLATE)
        pdf.cell(0, 5.5, _t(r["title"]), new_x="LMARGIN", new_y="NEXT")
        _p(pdf, r["text"], 8.8, MUTED)
        pdf.ln(1)
    return bytes(pdf.output())


def build_symptom_pdf(user: dict, rec: dict, when: str = None) -> bytes:
    """rec: dict(symptoms, top: [(label, prob)], severity, duration, alerts)"""
    when = when or datetime.now().strftime("%d %b %Y, %H:%M")
    pdf = _PDF(format="A4")
    pdf.set_auto_page_break(True, 18)
    pdf.set_margins(12, 12, 12)
    pdf.add_page()
    _meta(pdf, user, when)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(*SLATE)
    pdf.cell(0, 9, "Symptom analysis", new_x="LMARGIN", new_y="NEXT")

    _h(pdf, "Symptoms reported")
    _p(pdf, ", ".join(pretty_symptom(s) for s in rec["symptoms"]) or "-")
    sev = rec.get("severity") or {}
    if sev:
        _p(pdf, f"Severity score: {sev.get('score', 0)} ({sev.get('level', '-')})" +
           (f"   |   Duration: {rec['duration']}" if rec.get("duration") else ""), 9, MUTED)
    for a in rec.get("alerts", []):
        pdf.ln(1)
        _p(pdf, "! " + a, 9, (185, 28, 28), "B")

    _h(pdf, "Most likely conditions")
    for i, (label, prob) in enumerate(rec["top"], 1):
        name = clean_disease_name(label)
        y = pdf.get_y()
        pdf.set_font("Helvetica", "B", 10.5)
        pdf.set_text_color(*SLATE)
        pdf.cell(110, 6, _t(f"{i}. {name}"))
        pdf.set_fill_color(226, 232, 240)
        pdf.rect(124, y + 1.5, 52, 3.5, "F")
        pdf.set_fill_color(*(INDIGO if i == 1 else (148, 163, 184)))
        pdf.rect(124, y + 1.5, 52 * min(prob, 1), 3.5, "F")
        pdf.set_xy(178, y)
        pdf.set_font("Helvetica", "B", 10)
        pdf.cell(20, 6, f"{prob * 100:.1f}%", new_x="LMARGIN", new_y="NEXT")
        if i == 1:
            _p(pdf, disease_description(label), 8.8, MUTED)
            prec = disease_precautions(label)
            if prec:
                pdf.ln(1)
                _p(pdf, "Suggested precautions: " + "; ".join(prec), 8.8)
        pdf.ln(2)
    return bytes(pdf.output())
