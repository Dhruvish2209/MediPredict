"""Shared renderer for the three structured risk assessments (diabetes / heart / liver).
Everything is driven by app.utils.schemas.SPECS - the page files are one-liners."""
from datetime import datetime

import streamlit as st

from app.utils import db, ui
from app.utils.predict import predict_risk_only, run_assessment
from app.utils.recommend import recommendations
from app.utils.report import build_risk_pdf
from app.utils.schemas import SPECS, range_status
from app.utils.session import require_login

SECTION_ICONS = {"About you": "person", "Lab values": "science", "Symptoms & exercise": "monitor_heart",
                 "Vitals & labs": "bloodtype", "ECG & stress test": "ecg_heart",
                 "Bilirubin & proteins": "science", "Liver enzymes": "labs"}
STATUS_STYLE = {"low": ("Below range", "info"), "normal": ("In range", "good"), "high": ("Above range", "warn")}


# ----------------------------------------------------------------- state helpers
def _k(spec, key):
    return f"{spec.name}:{key}"


def _coerce(f, v):
    if f.kind != "number" or v is None:
        return v
    v = max(f.min, min(f.max, v))
    return int(round(v)) if f.is_int else float(v)


def _init_state(spec, user):
    """Seed widget state. Streamlit drops widget keys when you leave a page, so we keep a copy
    of the form in `_forms` and restore it when you come back."""
    saved = st.session_state.setdefault("_forms", {}).setdefault(spec.name, {})
    for f in spec.fields:
        k = _k(spec, f.key)
        if k not in st.session_state:
            v = saved.get(k, f.default)
            if k not in saved:  # first visit: personalise from the profile
                if f.key == "Age" and user.get("age"):
                    v = int(user["age"])
                if f.key in ("Sex", "Gender") and user.get("sex") in ("Male", "Female"):
                    v = ("M" if user["sex"] == "Male" else "F") if f.key == "Sex" else user["sex"]
            st.session_state[k] = _coerce(f, v)
        if f.optional and f"{k}:unknown" not in st.session_state:
            st.session_state[f"{k}:unknown"] = saved.get(f"{k}:unknown", False)


def _remember(spec):
    saved = st.session_state["_forms"][spec.name]
    for f in spec.fields:
        k = _k(spec, f.key)
        if k in st.session_state:
            saved[k] = st.session_state[k]
        if f.optional and f"{k}:unknown" in st.session_state:
            saved[f"{k}:unknown"] = st.session_state[f"{k}:unknown"]


def _apply_preset(spec, values):
    for f in spec.fields:
        if f.key in values:
            st.session_state[_k(spec, f.key)] = _coerce(f, values[f.key])
        if f.optional:
            st.session_state[f"{_k(spec, f.key)}:unknown"] = False
    st.session_state.pop(f"{spec.name}:result", None)


def _reset(spec):
    for f in spec.fields:
        st.session_state[_k(spec, f.key)] = _coerce(f, f.default)
        if f.optional:
            st.session_state[f"{_k(spec, f.key)}:unknown"] = False
    st.session_state.pop(f"{spec.name}:result", None)


def _collect(spec):
    vals = {}
    for f in spec.fields:
        k = _k(spec, f.key)
        v = st.session_state.get(k, f.default)
        if f.optional and st.session_state.get(f"{k}:unknown"):
            v = None
        vals[f.key] = v
    return vals


def _fmt(step):
    s = f"{step:.10f}".rstrip("0")
    return "%d" if "." not in s or s.endswith(".") else f"%.{len(s.split('.')[1])}f"


# ----------------------------------------------------------------------- inputs
def _render_field(spec, f):
    k = _k(spec, f.key)
    label = f.label + (f" ({f.unit})" if f.unit else "")
    if f.kind == "number":
        unknown = bool(f.optional and st.session_state.get(f"{k}:unknown"))
        if f.is_int:
            st.number_input(label, int(f.min), int(f.max), step=int(f.step or 1), key=k, help=f.help or None, disabled=unknown)
        else:
            st.number_input(label, float(f.min), float(f.max), step=float(f.step), format=_fmt(f.step), key=k,
                            help=f.help or None, disabled=unknown)
        val = None if unknown else st.session_state[k]
        status = range_status(f, val)
        bits = []
        if status:
            txt, tone = STATUS_STYLE[status]
            bits.append(f"<span class='mp-dot' style='background:{ui.TONES[tone][0]}'></span>"
                        f"<b style='color:{ui.TONES[tone][0]}'>{txt}</b>")
        if f.ref_text:
            bits.append(f"typical {f.ref_text}")
        if bits and not unknown:
            st.markdown(ui.html(f"<div class='mp-ref'>{' · '.join(bits)}</div>"), unsafe_allow_html=True)
        if f.optional:
            st.checkbox("I don't know / not tested", key=f"{k}:unknown",
                        help="The model will assume a typical value learned from the training data.")
    else:
        opts = [v for v, _ in f.options]
        labels = dict(f.options)
        if f.kind == "binary" or len(opts) == 2:
            st.radio(label, opts, format_func=lambda v, l=labels: l[v], key=k, horizontal=True, help=f.help or None)
        else:
            st.selectbox(label, opts, format_func=lambda v, l=labels: l[v], key=k, help=f.help or None)


def _bmi_helper(spec):
    with st.expander("Don't know your BMI? Calculate it", icon=":material/calculate:"):
        c1, c2 = st.columns(2)
        h = c1.number_input("Height (cm)", 100, 230, 170, key="bmi_h")
        w = c2.number_input("Weight (kg)", 25.0, 250.0, 70.0, step=0.5, key="bmi_w")
        bmi = round(w / ((h / 100) ** 2), 1)
        st.markdown(f"**Your BMI: {bmi}**")
        st.button("Use this BMI", icon=":material/check:", on_click=lambda: st.session_state.__setitem__(
            _k(spec, "BMI"), _coerce(spec.field("BMI"), bmi)))


def _render_form(spec, user):
    st.markdown(ui.html(f"<div class='mp-muted' style='font-size:.85rem;margin:.9rem 0 .35rem'>Quick start: load an example profile, or enter your own values.</div>"),
                unsafe_allow_html=True)
    b1, b2, b3, _ = st.columns([1, 1, 1, 1.4])
    names = list(spec.presets)
    b1.button(names[0], icon=":material/sentiment_satisfied:", on_click=_apply_preset, args=(spec, spec.presets[names[0]]), width="stretch", key=f"{spec.name}:p0")
    b2.button(names[1], icon=":material/warning:", on_click=_apply_preset, args=(spec, spec.presets[names[1]]), width="stretch", key=f"{spec.name}:p1")
    b3.button("Reset", icon=":material/restart_alt:", on_click=_reset, args=(spec,), width="stretch", key=f"{spec.name}:p2")

    sections = []
    for f in spec.fields:
        if f.section not in sections:
            sections.append(f.section)
    for sec in sections:
        with st.container(border=True):
            ic = SECTION_ICONS.get(sec, "list_alt")
            st.markdown(ui.html(f"<div style='display:flex;align-items:center;gap:.5rem;margin-bottom:.2rem'>"
                                f"{ui.icon(ic, 22, spec.accent)}<b style='font-size:1rem'>{sec}</b></div>"), unsafe_allow_html=True)
            fields = [f for f in spec.fields if f.section == sec]
            cols = st.columns(2, gap="large")
            for i, f in enumerate(fields):
                with cols[i % 2]:
                    _render_field(spec, f)
            if spec.name == "diabetes" and sec == "About you":
                _bmi_helper(spec)
    _remember(spec)


# ---------------------------------------------------------------------- results
def _summary_sentence(result):
    ups = [f for f in result["factors"] if f["contribution"] > 0.5][:3]
    downs = [f for f in result["factors"] if f["contribution"] < -0.5][:2]
    parts = []
    if ups:
        parts.append("**Raising your risk:** " + ", ".join(f"{f['label']} ({f['contribution']:+.1f})" for f in ups))
    if downs:
        parts.append("**Lowering it:** " + ", ".join(f"{f['label']} ({f['contribution']:+.1f})" for f in downs))
    return "  \n".join(parts) or "No single factor stands out strongly."


def _values_table(result):
    spec = SPECS[result["disease"]]
    rows = ""
    for c in result["comparison"]:
        f = spec.field(c["key"])
        you = "Not provided" if c["value"] is None else f.label_for(c["value"])
        status = ""
        if c["status"]:
            txt, tone = STATUS_STYLE[c["status"]]
            status = ui.pill_html(txt, tone)
        pct = f"{c['percentile']:.0f}%" if c.get("percentile") is not None else "–"
        typical = f"{c['median_neg']:g} → {c['median_pos']:g}" if c.get("median_neg") is not None else "–"
        rows += (f"<tr><td><b>{c['label']}</b></td><td>{you}</td><td>{c['ref_text'] or '–'}</td><td>{status or '–'}</td>"
                 f"<td>{pct}</td><td>{typical}</td></tr>")
    return ui.html(f"""<div class='mp-scroll'><table class='mp-table'><thead><tr><th>Measure</th><th>You</th><th>Typical range</th>
        <th>Status</th><th>Percentile</th><th>Median: healthy → affected</th></tr></thead><tbody>{rows}</tbody></table></div>""")


def render_result(result, user, prefix, interactive=True):
    spec = SPECS[result["disease"]]
    level, risk = result["level"], result["risk_pct"]
    uid = result.get("pred_id", "x")

    for w in result.get("warnings", []):
        ui.callout("warn", "Value outside training range", w)
    if result.get("unknown"):
        ui.callout("info", "Some values were not provided",
                   "Typical values from the training data were used for: " + ", ".join(result["unknown"]) + ".")

    left, right = st.columns([1, 1.75], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("<div style='text-align:center;font-weight:700;margin-bottom:-.4rem'>Estimated risk</div>", unsafe_allow_html=True)
            ui.show(ui.gauge_chart(risk, level), key=f"{prefix}:gauge:{uid}")
            st.markdown(ui.html(f"<div style='text-align:center'>{ui.risk_pill(level)}</div>"), unsafe_allow_html=True)
            st.markdown(ui.html(f"""<p class='mp-muted' style='text-align:center;font-size:.85rem;margin:.7rem 0 .2rem'>
                The average patient in the dataset scores <b>{result['base_pct']:.0f}%</b>.<br>
                Model: <b>{result['model_name']}</b></p>"""), unsafe_allow_html=True)
            st.download_button("Download PDF report", icon=":material/picture_as_pdf:", width="stretch", key=f"{prefix}:pdf:{uid}",
                               data=build_risk_pdf(user, result), mime="application/pdf",
                               file_name=f"MediPredict_{spec.short.replace(' ', '_')}_{datetime.now():%Y%m%d_%H%M}.pdf")
    with right:
        tabs = ["Why this result", "Waterfall", "Your values"] + (["What-if"] if interactive else [])
        tab_objs = st.tabs(tabs)
        with tab_objs[0]:
            st.markdown(_summary_sentence(result))
            ui.show(ui.factors_chart(result["factors"]), key=f"{prefix}:factors:{uid}")
            st.caption("SHAP values on the model's probability output: each bar is the change in estimated risk "
                       "(percentage points) caused by that factor compared with the average patient.")
        with tab_objs[1]:
            ui.show(ui.waterfall_chart(result["base_pct"], result["factors"], risk), key=f"{prefix}:waterfall:{uid}")
            st.caption("Starts at the dataset average and adds each factor's push until it reaches your estimated risk.")
        with tab_objs[2]:
            st.markdown(_values_table(result), unsafe_allow_html=True)
            st.caption("Percentile = share of patients in the training data with a lower value than yours.")
        if interactive:
            with tab_objs[3]:
                _what_if(spec, result, prefix)

    ui.section("Personalised guidance", "Based on your own values", "tips_and_updates", "violet")
    recs = recommendations(result["disease"], result["ui_values"], level)
    cols = st.columns(2, gap="medium")
    for i, r in enumerate(recs):
        with cols[i % 2]:
            ui.callout(r["tone"], r["title"], r["text"])
    ui.disclaimer()


def _what_if(spec, result, prefix):
    fields = [f for f in spec.fields if f.whatif and result["ui_values"].get(f.key) is not None][:3]
    if not fields:
        st.info("No adjustable measures available.")
        return
    st.markdown("Move the sliders to see how changing a value would change the model's estimate.")
    new_vals = dict(result["ui_values"])
    cols = st.columns(len(fields))
    for col, f in zip(cols, fields):
        cur = _coerce(f, result["ui_values"][f.key])
        lo, hi = (int(f.min), int(f.max)) if f.is_int else (float(f.min), float(f.max))
        step = int(f.step or 1) if f.is_int else float(f.step)
        with col:
            new_vals[f.key] = st.slider(f.label + (f" ({f.unit})" if f.unit else ""), lo, hi, cur, step,
                                        key=f"{prefix}:wi:{f.key}:{result.get('pred_id', 'x')}")
    new_risk, new_level = predict_risk_only(spec.name, new_vals)
    delta = new_risk - result["risk_pct"]
    m1, m2 = st.columns(2)
    m1.metric("Projected risk", f"{new_risk:.1f}%", f"{delta:+.1f} pts vs. your result", delta_color="inverse")
    m2.markdown(ui.html(f"<div style='padding-top:1.1rem'>{ui.risk_pill(new_level)}</div>"), unsafe_allow_html=True)
    st.caption("What-if estimates come from the same statistical model and are not medical advice.")


# ------------------------------------------------------------------------- page
def render(name: str):
    user = require_login()
    spec = SPECS[name]
    ui.page_header(spec.title, spec.blurb, spec.icon, chips=[spec.dataset.split(" · ")[0], "Explainable with SHAP", "PDF report"])
    _init_state(spec, user)
    _render_form(spec, user)

    st.write("")
    go = st.button(f"Assess {spec.short.lower()} risk", type="primary", icon=":material/analytics:", width="stretch", key=f"{name}:go")
    rkey = f"{name}:result"
    if go:
        values = _collect(spec)
        with st.spinner("Running the model and computing SHAP explanations…"):
            result = run_assessment(name, values)
        result["pred_id"] = db.save_prediction(
            user["user_id"], spec.short, result["risk_pct"], result["level"], result["ui_values"], kind="risk",
            model_name=result["model_name"], explanation={k: result[k] for k in (
                "base_pct", "factors", "comparison", "warnings", "unknown", "model_name", "disease")})
        st.session_state[rkey] = result
        st.toast("Saved to your history", icon="✅")

    result = st.session_state.get(rkey)
    if result:
        st.divider()
        from app.utils.predict import _jsonable
        if _jsonable(_collect(spec)) != result["ui_values"]:
            ui.callout("info", "Inputs changed since this result", "Press the assess button again to update the estimate.")
        render_result(result, user, name)
    else:
        st.write("")
        ui.callout("brand", "Your result will appear here",
                   "Fill in the form (or load an example), then run the assessment to get a risk estimate, a SHAP "
                   "explanation, a what-if simulator and a downloadable PDF.")
