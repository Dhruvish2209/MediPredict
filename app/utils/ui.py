"""MediPredict design system: theme tokens, global CSS, HTML components and Plotly charts.

All custom HTML is produced through `html()` which strips indentation / blank lines, because
Streamlit's markdown parser would otherwise turn indented HTML into code blocks.
"""
import plotly.graph_objects as go
import streamlit as st

# --------------------------------------------------------------------------- tokens
RISK_COLORS = {"LOW": "#10b981", "MEDIUM": "#f59e0b", "HIGH": "#ef4444"}
RISK_LABELS = {"LOW": "Low risk", "MEDIUM": "Moderate risk", "HIGH": "High risk"}
TONES = {  # tone -> (accent, soft background light, soft background dark)
    "good": ("#10b981", "#ecfdf5", "rgba(16,185,129,.14)"),
    "info": ("#0ea5e9", "#f0f9ff", "rgba(14,165,233,.14)"),
    "warn": ("#f59e0b", "#fffbeb", "rgba(245,158,11,.14)"),
    "alert": ("#ef4444", "#fef2f2", "rgba(239,68,68,.14)"),
    "brand": ("#0d9488", "#f0fdfa", "rgba(13,148,136,.16)"),
    "violet": ("#6366f1", "#eef2ff", "rgba(99,102,241,.16)"),
}
TONE_ICONS = {"good": "check_circle", "info": "info", "warn": "warning", "alert": "warning", "brand": "verified",
              "violet": "auto_awesome"}

LIGHT = dict(bg="#f3f6fb", surface="#ffffff", surface2="#f8fafc", text="#0f172a", muted="#64748b",
             border="#e2e8f0", shadow="0 1px 2px rgba(15,23,42,.04), 0 8px 24px rgba(15,23,42,.06)",
             hover="0 2px 4px rgba(15,23,42,.06), 0 14px 32px rgba(13,148,136,.16)", plot_text="#334155",
             grid="#e2e8f0")
DARK = dict(bg="#0b1220", surface="#121c31", surface2="#16223a", text="#e5e7eb", muted="#94a3b8",
            border="#223152", shadow="0 1px 2px rgba(0,0,0,.4), 0 10px 28px rgba(0,0,0,.35)",
            hover="0 2px 4px rgba(0,0,0,.4), 0 14px 32px rgba(13,148,136,.28)", plot_text="#cbd5e1",
            grid="#223152")


def is_dark() -> bool:
    try:
        return st.context.theme.type == "dark"
    except Exception:
        return False


def tokens() -> dict:
    return DARK if is_dark() else LIGHT


def soft(tone: str) -> str:
    accent, light, dark = TONES[tone]
    return dark if is_dark() else light


def html(s: str) -> str:
    """Collapse an HTML snippet to one line so markdown never treats it as a code block."""
    return "".join(line.strip() for line in s.strip().splitlines())


def icon(name: str, size: int = 22, color: str = "currentColor", extra: str = "") -> str:
    return (f"<span class='mi' style='font-size:{size}px;color:{color};{extra}'>{name}</span>")


# ------------------------------------------------------------------------------ CSS
def inject_css():
    t = tokens()
    dark = is_dark()
    css = f"""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:opsz,wght,FILL,GRAD@24,400,1,0&display=swap');
    :root {{
      --bg:{t['bg']}; --surface:{t['surface']}; --surface2:{t['surface2']}; --text:{t['text']};
      --muted:{t['muted']}; --border:{t['border']}; --shadow:{t['shadow']}; --hover:{t['hover']};
      --primary:#0d9488; --primary2:#6366f1; --ok:#10b981; --warn:#f59e0b; --bad:#ef4444;
      --grad:linear-gradient(135deg,#0f766e 0%,#0d9488 38%,#4f46e5 100%);
      --radius:16px;
    }}
    html, body, .stApp, [class*="css"] {{ font-family:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif; }}
    .stApp {{ background:var(--bg); color:var(--text); }}
    h1,h2,h3,h4 {{ font-family:'Plus Jakarta Sans','Inter',sans-serif !important; letter-spacing:-.02em; color:var(--text); }}
    .mi {{ font-family:'Material Symbols Rounded'; font-weight:400; font-style:normal; line-height:1;
           display:inline-block; vertical-align:middle; letter-spacing:normal; text-transform:none;
           white-space:nowrap; direction:ltr; font-feature-settings:'liga'; -webkit-font-smoothing:antialiased;
           font-variation-settings:'FILL' 1,'wght' 500; user-select:none; }}

    /* ---- chrome ---- */
    #MainMenu, footer, [data-testid="stAppDeployButton"], .stDeployButton, [data-testid="stStatusWidget"] {{ visibility:hidden; display:none; }}
    header[data-testid="stHeader"] {{ background:transparent; height:2.6rem; }}
    [data-testid="stMainBlockContainer"], .block-container {{ max-width:1240px; padding:1.6rem 2rem 4rem; }}
    [data-testid="stVerticalBlock"] {{ gap:1rem; }}

    /* ---- sidebar ---- */
    [data-testid="stSidebar"] {{ background:linear-gradient(180deg,#0b1b3a 0%,#0e2a54 55%,#0b3b55 100%); border-right:0; }}
    [data-testid="stSidebar"] * {{ color:#dbe7f5; }}
    [data-testid="stSidebar"] hr {{ border-color:rgba(255,255,255,.12); }}
    [data-testid="stSidebarHeader"] {{ padding:.6rem 1rem 0; }}
    [data-testid="stSidebarNav"] {{ padding-top:.25rem; }}
    [data-testid="stSidebarNavLink"] {{ border-radius:12px; margin:2px 8px; padding:.5rem .75rem; transition:all .15s ease; }}
    [data-testid="stSidebarNavLink"]:hover {{ background:rgba(255,255,255,.08); }}
    [data-testid="stSidebarNavLink"][aria-current="page"] {{ background:linear-gradient(135deg,rgba(13,148,136,.9),rgba(79,70,229,.85)); box-shadow:0 6px 18px rgba(13,148,136,.35); }}
    [data-testid="stSidebarNavLink"][aria-current="page"] * {{ color:#fff !important; font-weight:600; }}
    [data-testid="stSidebarNav"] span[data-testid="stSidebarNavSeparator"], [data-testid="stNavSectionHeader"] {{ color:#8fb0d6 !important; text-transform:uppercase; font-size:.68rem; letter-spacing:.12em; }}
    [data-testid="stSidebar"] .stButton button {{ background:rgba(255,255,255,.08); border:1px solid rgba(255,255,255,.18); color:#fff; }}
    [data-testid="stSidebar"] .stButton button:hover {{ background:rgba(239,68,68,.25); border-color:rgba(239,68,68,.6); }}
    [data-testid="stSidebar"] [data-testid="stSidebarCollapseButton"] * {{ color:#dbe7f5; }}

    /* ---- buttons ---- */
    .stButton > button, .stDownloadButton > button, [data-testid^="stBaseButton"], [data-testid="stPageLink"] a {{ border-radius:12px; font-weight:600; transition:transform .12s ease, box-shadow .15s ease; }}
    [data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{ background:var(--grad); border:0; color:#fff !important; box-shadow:0 6px 18px rgba(13,148,136,.32); }}
    [data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {{ transform:translateY(-1px); box-shadow:0 10px 24px rgba(79,70,229,.35); filter:brightness(1.05); }}
    [data-testid="stBaseButton-secondary"], [data-testid="stBaseButton-secondaryFormSubmit"] {{ background:var(--surface); border:1px solid var(--border); color:var(--text); }}
    [data-testid="stBaseButton-secondary"]:hover {{ border-color:var(--primary); color:var(--primary); transform:translateY(-1px); }}
    [data-testid="stPageLink"] a {{ background:var(--surface); border:1px solid var(--border); padding:.55rem .9rem; }}
    [data-testid="stPageLink"] a:hover {{ border-color:var(--primary); box-shadow:var(--hover); }}

    /* ---- inputs ---- */
    [data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="textarea"], [data-baseweb="select"] > div {{ border-radius:12px !important; }}
    [data-testid="stTextInput"] input, [data-testid="stNumberInput"] input, textarea {{ font-size:.95rem; }}
    [data-testid="stWidgetLabel"] p {{ font-weight:600; font-size:.86rem; color:var(--text); }}
    [data-testid="stNumberInput"] [data-baseweb="input"]:focus-within, [data-testid="stTextInput"] [data-baseweb="input"]:focus-within,
    [data-baseweb="textarea"]:focus-within {{ box-shadow:0 0 0 3px rgba(13,148,136,.22); }}

    /* ---- tabs ---- */
    [data-baseweb="tab-list"] {{ gap:.25rem; background:var(--surface2); border:1px solid var(--border); border-radius:14px; padding:.3rem; width:fit-content; max-width:100%; overflow-x:auto; }}
    button[role="tab"] {{ border-radius:10px; padding:.45rem 1rem; font-weight:600; }}
    button[role="tab"][aria-selected="true"] {{ background:var(--surface); box-shadow:0 1px 3px rgba(15,23,42,.12); color:var(--primary); }}
    [data-baseweb="tab-highlight"], [data-baseweb="tab-border"] {{ display:none; }}

    /* ---- containers ---- */
    [data-testid="stMetric"] {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:.9rem 1.1rem; box-shadow:var(--shadow); }}
    [data-testid="stExpander"] {{ border:1px solid var(--border); border-radius:14px; background:var(--surface); overflow:hidden; }}
    [data-testid="stVerticalBlockBorderWrapper"] {{ border-radius:var(--radius); }}
    div[data-testid="stForm"] {{ border:1px solid var(--border); border-radius:var(--radius); background:var(--surface); padding:1.2rem; box-shadow:var(--shadow); }}
    [data-testid="stDataFrame"] {{ border-radius:14px; overflow:hidden; border:1px solid var(--border); }}
    [data-testid="stImage"] img {{ border-radius:14px; }}
    [data-testid="stAlert"] {{ border-radius:14px; }}

    /* ---- components ---- */
    .mp-hero {{ background:var(--grad); color:#fff; border-radius:22px; padding:1.6rem 1.8rem; position:relative; overflow:hidden;
                box-shadow:0 18px 40px rgba(13,148,136,.28); display:flex; gap:1.1rem; align-items:center; }}
    .mp-hero::after {{ content:''; position:absolute; right:-60px; top:-70px; width:240px; height:240px; border-radius:50%; background:rgba(255,255,255,.10); }}
    .mp-hero::before {{ content:''; position:absolute; right:90px; bottom:-90px; width:180px; height:180px; border-radius:50%; background:rgba(255,255,255,.07); }}
    .mp-hero .mp-hero-ic {{ width:58px; height:58px; border-radius:18px; background:rgba(255,255,255,.18); display:flex; align-items:center; justify-content:center; flex:none; backdrop-filter:blur(6px); }}
    .mp-hero h1 {{ color:#fff !important; font-size:1.75rem; margin:0; padding:0; line-height:1.15; }}
    .mp-hero p {{ color:rgba(255,255,255,.88); margin:.3rem 0 0; font-size:.98rem; max-width:62ch; }}
    .mp-hero .mp-chips {{ margin-top:.7rem; display:flex; flex-wrap:wrap; gap:.4rem; }}
    .mp-hero .mp-chip {{ background:rgba(255,255,255,.16); color:#fff; border-color:rgba(255,255,255,.22); }}
    .mp-chip {{ display:inline-flex; align-items:center; gap:.3rem; padding:.22rem .65rem; border-radius:999px; font-size:.76rem; font-weight:600; border:1px solid var(--border); background:var(--surface2); color:var(--muted); }}
    .mp-card {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius); padding:1.2rem 1.3rem; box-shadow:var(--shadow); }}
    .mp-card.hover {{ transition:transform .15s ease, box-shadow .2s ease, border-color .2s ease; }}
    .mp-card.hover:hover {{ transform:translateY(-3px); box-shadow:var(--hover); border-color:rgba(13,148,136,.45); }}
    .mp-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(200px,1fr)); gap:1rem; }}
    .mp-kpi {{ display:flex; align-items:center; gap:.9rem; }}
    .mp-kpi .ic {{ width:46px; height:46px; border-radius:14px; display:flex; align-items:center; justify-content:center; flex:none; }}
    .mp-kpi .lbl {{ font-size:.74rem; text-transform:uppercase; letter-spacing:.08em; color:var(--muted); font-weight:600; }}
    .mp-kpi .val {{ font-family:'Plus Jakarta Sans',sans-serif; font-size:1.6rem; font-weight:800; line-height:1.1; color:var(--text); }}
    .mp-kpi .sub {{ font-size:.76rem; color:var(--muted); }}
    .mp-pill {{ display:inline-flex; align-items:center; gap:.3rem; padding:.28rem .75rem; border-radius:999px; font-size:.78rem; font-weight:700; letter-spacing:.02em; }}
    .mp-section {{ display:flex; align-items:center; gap:.6rem; margin:.4rem 0 .2rem; }}
    .mp-section h3 {{ margin:0; font-size:1.18rem; }}
    .mp-section .sub {{ color:var(--muted); font-size:.88rem; }}
    .mp-callout {{ display:flex; gap:.8rem; padding:.9rem 1.05rem; border-radius:14px; border:1px solid; align-items:flex-start; }}
    .mp-callout .t {{ font-weight:700; font-size:.95rem; color:var(--text); }}
    .mp-callout .d {{ font-size:.88rem; color:var(--muted); margin-top:.1rem; line-height:1.45; }}
    .mp-tile .ic {{ width:50px; height:50px; border-radius:16px; display:flex; align-items:center; justify-content:center; margin-bottom:.8rem; color:#fff; }}
    .mp-tile h4 {{ margin:0 0 .25rem; font-size:1.02rem; }}
    .mp-tile p {{ margin:0; color:var(--muted); font-size:.86rem; line-height:1.45; }}
    .mp-disclaimer {{ display:flex; gap:.6rem; align-items:flex-start; font-size:.8rem; color:var(--muted); background:var(--surface2); border:1px dashed var(--border); border-radius:12px; padding:.7rem .9rem; }}
    .mp-bar {{ height:8px; border-radius:99px; background:var(--surface2); border:1px solid var(--border); overflow:hidden; }}
    .mp-bar > span {{ display:block; height:100%; border-radius:99px; }}
    .mp-row {{ display:flex; align-items:center; justify-content:space-between; gap:.8rem; padding:.55rem 0; border-bottom:1px solid var(--border); }}
    .mp-row:last-child {{ border-bottom:0; }}
    .mp-muted {{ color:var(--muted); }}
    .mp-brand {{ display:flex; align-items:center; gap:.65rem; padding:.2rem .4rem; }}
    .mp-brand .logo {{ width:38px; height:38px; border-radius:12px; background:var(--grad); display:flex; align-items:center; justify-content:center; box-shadow:0 6px 16px rgba(13,148,136,.45); }}
    .mp-brand .nm {{ font-family:'Plus Jakarta Sans',sans-serif; font-weight:800; font-size:1.15rem; color:#fff !important; line-height:1; }}
    .mp-brand .tg {{ font-size:.66rem; color:#8fb0d6 !important; letter-spacing:.06em; text-transform:uppercase; }}
    .mp-user {{ display:flex; align-items:center; gap:.7rem; padding:.7rem .8rem; background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.12); border-radius:14px; }}
    .mp-avatar {{ width:38px; height:38px; border-radius:50%; background:var(--grad); display:flex; align-items:center; justify-content:center; font-weight:800; color:#fff !important; flex:none; }}
    .mp-step {{ display:flex; gap:.8rem; align-items:flex-start; }}
    .mp-step .n {{ width:30px; height:30px; border-radius:50%; background:var(--grad); color:#fff; font-weight:800; display:flex; align-items:center; justify-content:center; flex:none; font-size:.85rem; }}
    .mp-sym {{ display:inline-flex; align-items:center; gap:.3rem; padding:.3rem .7rem; border-radius:999px; background:rgba(13,148,136,.12); color:var(--primary); font-weight:600; font-size:.82rem; margin:0 .3rem .4rem 0; border:1px solid rgba(13,148,136,.25); }}
    .mp-sym.neg {{ background:rgba(239,68,68,.1); color:#ef4444; border-color:rgba(239,68,68,.25); text-decoration:line-through; }}

    .mp-table {{ width:100%; border-collapse:collapse; font-size:.86rem; }}
    .mp-table th {{ text-align:left; font-size:.7rem; text-transform:uppercase; letter-spacing:.07em; color:var(--muted); padding:.5rem .6rem; border-bottom:1px solid var(--border); white-space:nowrap; }}
    .mp-table td {{ padding:.6rem .6rem; border-bottom:1px solid var(--border); color:var(--text); vertical-align:middle; }}
    .mp-table tr:last-child td {{ border-bottom:0; }}
    .mp-scroll {{ overflow-x:auto; -webkit-overflow-scrolling:touch; }}
    .hide-sm {{ display:block; }}
    .mp-ref {{ font-size:.74rem; color:var(--muted); margin:-.45rem 0 .2rem; display:flex; gap:.4rem; align-items:center; flex-wrap:wrap; }}
    .mp-dot {{ width:8px; height:8px; border-radius:50%; display:inline-block; }}

    /* ---- login ---- */
    .mp-auth-hero {{ background:var(--grad); border-radius:26px; padding:2.4rem 2.2rem; color:#fff; min-height:560px; position:relative; overflow:hidden; box-shadow:0 24px 50px rgba(13,148,136,.3); }}
    .mp-auth-hero::after {{ content:''; position:absolute; right:-80px; bottom:-80px; width:300px; height:300px; border-radius:50%; background:rgba(255,255,255,.09); }}
    .mp-auth-hero::before {{ content:''; position:absolute; left:-60px; top:-60px; width:200px; height:200px; border-radius:50%; background:rgba(255,255,255,.07); }}
    .mp-auth-hero h1 {{ color:#fff !important; font-size:2.25rem; line-height:1.12; margin:1.2rem 0 .6rem; }}
    .mp-auth-hero p {{ color:rgba(255,255,255,.9); font-size:1.02rem; max-width:44ch; }}
    .mp-feature {{ display:flex; gap:.8rem; align-items:center; margin:.75rem 0; position:relative; z-index:1; }}
    .mp-feature .ic {{ width:40px; height:40px; border-radius:12px; background:rgba(255,255,255,.18); display:flex; align-items:center; justify-content:center; flex:none; }}
    .mp-feature b {{ display:block; font-size:.95rem; }} .mp-feature span.d {{ font-size:.82rem; color:rgba(255,255,255,.82); }}
    .mp-stats {{ display:flex; gap:1.6rem; margin-top:1.6rem; position:relative; z-index:1; flex-wrap:wrap; }}
    .mp-stats b {{ font-family:'Plus Jakarta Sans',sans-serif; font-size:1.6rem; display:block; }} .mp-stats span {{ font-size:.75rem; opacity:.85; text-transform:uppercase; letter-spacing:.08em; }}
    {"[data-testid='stSidebar'], [data-testid='stSidebarCollapsedControl'] { display:none !important; }" if st.session_state.get("_hide_sidebar") else ""}

    /* ---- loading indicator: top progress bar + pill while Streamlit is (re)running ---- */
    .stApp[data-test-script-state="running"]::before {{ content:''; position:fixed; top:0; left:0; right:0; height:3px; z-index:1000000;
        background:linear-gradient(90deg,transparent 0%,#14b8a6 35%,#6366f1 65%,transparent 100%); background-size:45% 100%;
        background-repeat:no-repeat; animation:mp-bar 1.1s ease-in-out infinite; }}
    .stApp[data-test-script-state="running"]::after {{ content:'Loading…'; position:fixed; top:14px; left:50%; transform:translateX(-50%);
        z-index:1000000; background:var(--surface); color:var(--text); border:1px solid var(--border); border-radius:999px;
        padding:.32rem 1rem; font-size:.8rem; font-weight:600; box-shadow:var(--shadow); opacity:0; animation:mp-pill .25s ease .45s forwards, mp-pulse 1.2s ease-in-out .7s infinite; }}
    @keyframes mp-bar {{ 0% {{ background-position:-60% 0; }} 100% {{ background-position:170% 0; }} }}
    @keyframes mp-pill {{ to {{ opacity:1; }} }}
    @keyframes mp-pulse {{ 50% {{ box-shadow:0 0 0 6px rgba(13,148,136,.16); }} }}

    /* ---- no stray text caret / I-beam on clickable UI ---- */
    [data-testid="stSelectbox"] input, [data-baseweb="select"] input[aria-autocomplete] {{ caret-color:transparent !important; cursor:pointer !important; user-select:none !important; }}
    [data-testid="stSelectbox"] *, [data-testid="stMultiSelect"] [data-baseweb="tag"], [data-testid="stNumberInput"] button, [data-testid="stSlider"] * {{ cursor:pointer !important; }}
    [data-testid="stNumberInput"] input, [data-testid="stTextInput"] input, textarea {{ cursor:text !important; }}
    [data-baseweb="select"], [data-baseweb="select"] *, [data-baseweb="popover"] li, button, [role="tab"], [role="radio"], [role="checkbox"],
    label[data-baseweb="radio"], label[data-baseweb="checkbox"], summary, summary *, [data-testid="stSidebar"] a, [data-testid="stPageLink"] a {{ cursor:pointer !important; }}
    [data-testid="stSidebar"], .mp-hero, .mp-kpi, .mp-tile, [data-testid="stWidgetLabel"], button, [role="tab"], summary {{ user-select:none; -webkit-user-select:none; }}
    button:focus, [role="tab"]:focus, [role="radio"]:focus, summary:focus, a:focus {{ outline:none !important; }}
    [data-baseweb="select"]:focus-within {{ box-shadow:0 0 0 3px rgba(13,148,136,.22); border-radius:12px; }}

    /* ---- responsive ---- */
    @media (max-width: 900px) {{
      [data-testid="stMainBlockContainer"], .block-container {{ padding:1rem 1rem 3rem; }}
      .mp-hero {{ padding:1.2rem; border-radius:18px; flex-direction:row; }}
      .mp-hero h1 {{ font-size:1.35rem; }} .mp-hero p {{ font-size:.9rem; }}
      .mp-hero .mp-hero-ic {{ width:46px; height:46px; border-radius:14px; }}
      .mp-auth-hero {{ min-height:auto; padding:1.6rem 1.4rem; border-radius:20px; }}
      .mp-auth-hero h1 {{ font-size:1.7rem; }}
      .hide-sm {{ display:none; }}
      .mp-kpi .val {{ font-size:1.35rem; }}
    }}
    @media (max-width: 480px) {{
      .mp-hero {{ flex-direction:column; align-items:flex-start; }}
      .mp-grid {{ grid-template-columns:1fr 1fr; gap:.7rem; }}
      .mp-card {{ padding:1rem; }}
      .mp-stats {{ gap:1rem; }}
    }}
    """
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ------------------------------------------------------------------------ components
def page_header(title, subtitle="", icon_name="monitor_heart", chips=None):
    chip_html = "".join(f"<span class='mp-chip'>{c}</span>" for c in (chips or []))
    st.markdown(html(f"""
      <div class='mp-hero'>
        <div class='mp-hero-ic'>{icon(icon_name, 30, '#fff')}</div>
        <div style='position:relative;z-index:1'>
          <h1>{title}</h1>
          {f"<p>{subtitle}</p>" if subtitle else ""}
          {f"<div class='mp-chips'>{chip_html}</div>" if chips else ""}
        </div>
      </div>"""), unsafe_allow_html=True)


def section(title, subtitle="", icon_name=None, tone="brand"):
    ic = ""
    if icon_name:
        accent = TONES[tone][0]
        ic = (f"<div style='width:34px;height:34px;border-radius:11px;background:{soft(tone)};display:flex;"
              f"align-items:center;justify-content:center'>{icon(icon_name, 20, accent)}</div>")
    st.markdown(html(f"""<div class='mp-section'>{ic}<div><h3>{title}</h3>
        {f"<div class='sub'>{subtitle}</div>" if subtitle else ""}</div></div>"""), unsafe_allow_html=True)


def kpi_cards(items):
    """items: list of dict(label, value, sub, icon, tone)."""
    cells = ""
    for it in items:
        tone = it.get("tone", "brand")
        accent = TONES[tone][0]
        cells += (f"<div class='mp-card'><div class='mp-kpi'><div class='ic' style='background:{soft(tone)}'>"
                  f"{icon(it.get('icon', 'insights'), 24, accent)}</div><div><div class='lbl'>{it['label']}</div>"
                  f"<div class='val'>{it['value']}</div><div class='sub'>{it.get('sub', '')}</div></div></div></div>")
    st.markdown(html(f"<div class='mp-grid'>{cells}</div>"), unsafe_allow_html=True)


def pill_html(text, tone):
    accent = TONES[tone][0]
    return (f"<span class='mp-pill' style='background:{soft(tone)};color:{accent};border:1px solid {accent}33'>"
            f"{text}</span>")


def risk_pill(level, with_icon=True):
    tone = {"LOW": "good", "MEDIUM": "warn", "HIGH": "alert"}[level]
    ic = {"LOW": "check_circle", "MEDIUM": "error", "HIGH": "warning"}[level]
    label = RISK_LABELS[level]
    return pill_html((icon(ic, 16, TONES[tone][0]) + " " if with_icon else "") + label, tone)


def callout(tone, title, text="", icon_name=None):
    accent = TONES[tone][0]
    ic = icon_name or TONE_ICONS[tone]
    st.markdown(html(f"""<div class='mp-callout' style='background:{soft(tone)};border-color:{accent}44'>
        <div>{icon(ic, 24, accent)}</div><div><div class='t'>{title}</div>
        {f"<div class='d'>{text}</div>" if text else ""}</div></div>"""), unsafe_allow_html=True)


def disclaimer():
    st.markdown(html(f"""<div class='mp-disclaimer'>{icon('health_and_safety', 20, '#0d9488')}
        <div><b>Not a medical diagnosis.</b> MediPredict is an educational screening tool built on public datasets.
        It cannot replace a clinician. If you feel unwell or have an emergency, contact a doctor or your local emergency number.</div></div>"""),
        unsafe_allow_html=True)


def bar_html(pct, color):
    return f"<div class='mp-bar'><span style='width:{max(0, min(100, pct)):.1f}%;background:{color}'></span></div>"


def tile(icon_name, title, text, gradient="linear-gradient(135deg,#0d9488,#4f46e5)"):
    st.markdown(html(f"""<div class='mp-card hover mp-tile'><div class='ic' style='background:{gradient}'>
        {icon(icon_name, 26, '#fff')}</div><h4>{title}</h4><p>{text}</p></div>"""), unsafe_allow_html=True)


# ----------------------------------------------------------------------------- charts
def _layout(fig, height, margin=None):
    t = tokens()
    fig.update_layout(
        height=height, margin=margin or dict(l=8, r=8, t=28, b=8), paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)", font=dict(family="Inter, system-ui, sans-serif", size=12, color=t["plot_text"]),
        hoverlabel=dict(font_family="Inter"), autosize=True,
    )
    return fig


def show(fig, key=None):
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False, "responsive": True}, key=key)


def gauge_chart(risk_pct, level, height=250):
    t = tokens()
    color = RISK_COLORS[level]
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(risk_pct, 1), number=dict(suffix="%", font=dict(size=44, color=color, family="Plus Jakarta Sans")),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=0, tickcolor=t["muted"], tickvals=[0, 30, 60, 100],
                      tickfont=dict(size=11, color=t["muted"])),
            bar=dict(color=color, thickness=0.28), bgcolor="rgba(0,0,0,0)", borderwidth=0,
            steps=[dict(range=[0, 30], color="rgba(16,185,129,.18)"), dict(range=[30, 60], color="rgba(245,158,11,.2)"),
                   dict(range=[60, 100], color="rgba(239,68,68,.2)")],
        )))
    return _layout(fig, height, dict(l=44, r=44, t=30, b=0))


def factors_chart(factors, top_n=8):
    """Horizontal SHAP-style bars: red pushes risk up, green pushes it down (percentage points)."""
    t = tokens()
    rows = [f for f in factors if abs(f["contribution"]) >= 0.05][:top_n] or factors[:top_n]
    rows = list(reversed(rows))  # plotly draws bottom-up
    ys = [f"{r['label']}<br><span style='font-size:10px;color:{t['muted']}'>{r['display']}</span>" for r in rows]
    xs = [r["contribution"] for r in rows]
    colors = ["#ef4444" if x > 0 else "#10b981" for x in xs]
    fig = go.Figure(go.Bar(
        x=xs, y=ys, orientation="h", marker=dict(color=colors),
        text=[f"{x:+.1f}" for x in xs], textposition="outside", cliponaxis=False,
        hovertemplate="<b>%{y}</b><br>Effect on risk: %{x:+.1f} percentage points<extra></extra>"))
    m = max(abs(x) for x in xs) if xs else 1
    fig.update_xaxes(range=[-m * 1.35, m * 1.35], zeroline=True, zerolinecolor=t["muted"], zerolinewidth=1,
                     gridcolor=t["grid"], title=dict(text="← lowers · raises risk → (pts)",
                                                    font=dict(size=11, color=t["muted"])))
    fig.update_yaxes(automargin=True, tickfont=dict(size=12))
    return _layout(fig, 70 + 46 * len(rows), dict(l=8, r=30, t=10, b=8))


def waterfall_chart(base, factors, risk, top_n=7):
    t = tokens()
    top = [f for f in factors if abs(f["contribution"]) >= 0.05][:top_n]
    rest = sum(f["contribution"] for f in factors if f not in top)
    labels = ["Average patient"] + [f["label"] for f in top] + (["Other factors"] if abs(rest) >= 0.05 else []) + ["Your risk"]
    vals = [base] + [f["contribution"] for f in top] + ([rest] if abs(rest) >= 0.05 else []) + [risk]
    measure = ["absolute"] + ["relative"] * (len(vals) - 2) + ["total"]
    fig = go.Figure(go.Waterfall(
        orientation="h", y=labels, x=vals, measure=measure, text=[f"{v:+.1f}" if m == "relative" else f"{v:.1f}%" for v, m in zip(vals, measure)],
        textposition="outside", cliponaxis=False, connector=dict(line=dict(color=t["grid"], width=1)),
        increasing=dict(marker=dict(color="#ef4444")), decreasing=dict(marker=dict(color="#10b981")),
        totals=dict(marker=dict(color="#4f46e5")),
        hovertemplate="%{y}: %{x:.1f}<extra></extra>"))
    fig.update_yaxes(autorange="reversed", automargin=True)
    fig.update_xaxes(gridcolor=t["grid"], title=dict(text="Predicted risk (%)", font=dict(size=11, color=t["muted"])), range=[0, 108])
    return _layout(fig, 90 + 40 * len(labels), dict(l=8, r=30, t=10, b=8))


def impact_chart(rows, top_n=8):
    """Symptom leave-one-out impact bars (percentage points on the leading diagnosis)."""
    t = tokens()
    rows = rows[:top_n][::-1]
    xs = [r[1] for r in rows]
    fig = go.Figure(go.Bar(x=xs, y=[r[0] for r in rows], orientation="h", marker=dict(color=["#0d9488" if x >= 0 else "#f59e0b" for x in xs]),
                           text=[f"{x:+.1f}" for x in xs], textposition="outside", cliponaxis=False,
                           hovertemplate="%{y}: %{x:+.1f} pts<extra></extra>"))
    m = max([abs(x) for x in xs] + [1])
    fig.update_xaxes(range=[-m * 0.2 if min(xs) >= 0 else -m * 1.3, m * 1.3], gridcolor=t["grid"], zeroline=True, zerolinecolor=t["muted"],
                     title=dict(text="Contribution to the top prediction (percentage points)", font=dict(size=11, color=t["muted"])))
    fig.update_yaxes(automargin=True)
    return _layout(fig, 70 + 38 * len(rows), dict(l=8, r=30, t=10, b=8))


def prob_bars(labels, probs, height=None):
    t = tokens()
    labels, probs = labels[::-1], probs[::-1]
    cols = ["#4f46e5" if i == len(labels) - 1 else "#94a3b8" for i in range(len(labels))]
    fig = go.Figure(go.Bar(x=[p * 100 for p in probs], y=labels, orientation="h", marker=dict(color=cols),
                           text=[f"{p * 100:.1f}%" for p in probs], textposition="outside", cliponaxis=False))
    fig.update_xaxes(range=[0, 118], gridcolor=t["grid"], title=None, showticklabels=False)
    fig.update_yaxes(automargin=True)
    return _layout(fig, height or 60 + 52 * len(labels), dict(l=8, r=30, t=6, b=6))


def trend_chart(df, x="created_at", y="risk_score", color="disease", height=330):
    import plotly.express as px
    t = tokens()
    fig = px.line(df.sort_values(x), x=x, y=y, color=color, markers=True,
                  color_discrete_sequence=["#0d9488", "#4f46e5", "#f59e0b", "#ef4444", "#8b5cf6", "#0ea5e9"])
    fig.update_traces(line=dict(width=3), marker=dict(size=8))
    fig.add_hrect(y0=60, y1=100, fillcolor="rgba(239,68,68,.07)", line_width=0)
    fig.add_hrect(y0=30, y1=60, fillcolor="rgba(245,158,11,.07)", line_width=0)
    fig.update_yaxes(range=[0, 100], gridcolor=t["grid"], title="Risk / confidence (%)")
    fig.update_xaxes(gridcolor=t["grid"], title=None)
    fig.update_layout(legend=dict(orientation="h", y=-0.22, title=None))
    return _layout(fig, height, dict(l=8, r=8, t=10, b=8))


def donut(labels, values, colors=None, height=260, center_text=""):
    t = tokens()
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.66, sort=False, textinfo="percent",
                           marker=dict(colors=colors or ["#0d9488", "#4f46e5", "#f59e0b", "#ef4444", "#8b5cf6", "#0ea5e9"],
                                       line=dict(color=t["surface"], width=3))))
    fig.update_layout(legend=dict(orientation="h", y=-0.1), annotations=[dict(text=center_text, x=0.5, y=0.5, showarrow=False,
                                                                              font=dict(size=22, family="Plus Jakarta Sans", color=t["text"]))])
    return _layout(fig, height, dict(l=8, r=8, t=8, b=8))


def mini_gauge(value, label, color, height=170):
    t = tokens()
    fig = go.Figure(go.Indicator(mode="gauge+number", value=value, number=dict(suffix="%", font=dict(size=26, color=color)),
                                 title=dict(text=label, font=dict(size=13, color=t["muted"])),
                                 gauge=dict(axis=dict(range=[0, 100], visible=False), bar=dict(color=color, thickness=0.35),
                                            bgcolor="rgba(148,163,184,.18)", borderwidth=0)))
    return _layout(fig, height, dict(l=14, r=14, t=40, b=0))
