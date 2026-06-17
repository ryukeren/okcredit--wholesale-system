"""
styles.py — Premium CSS Design System v3
==========================================
Complete dark-mode design system with:
  - Animated sidebar navigation (instant visual feedback)
  - Glassmorphism sidebar with glowing active state
  - Smooth micro-animations on every interactive element
  - Gradient KPI cards with hover lift effect
  - Premium typography via Google Fonts (Inter + JetBrains Mono)
  - Responsive mobile-first layout
  - Custom scrollbars, transitions, pulsing accents
"""

import streamlit as st


# ── Design tokens ─────────────────────────────────────────────────────────────
COLORS = {
    "bg":          "#080b14",
    "bg2":         "#0d1117",
    "surface":     "#111827",
    "surface2":    "#1a2235",
    "surface3":    "#1f2a3c",
    "accent":      "#4f8ef7",
    "accent2":     "#7c5cbf",
    "accent_glow": "rgba(79,142,247,0.25)",
    "success":     "#22c55e",
    "warning":     "#f59e0b",
    "danger":      "#ef4444",
    "text":        "#e2e8f0",
    "text_muted":  "#94a3b8",
    "border":      "#1e293b",
    "border2":     "#2d3a4f",
}


def inject_custom_css():
    """Call once from app.py to inject all custom styles."""
    st.markdown(f"""
    <style>
    /* ── Google Fonts ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600&display=swap');

    /* ── Global base ── */
    html, body, [class*="css"] {{
        font-family: 'Inter', system-ui, sans-serif !important;
        background-color: {COLORS['bg']} !important;
        color: {COLORS['text']} !important;
        -webkit-font-smoothing: antialiased;
    }}

    /* ── Hide Streamlit chrome ── */
    #MainMenu, footer, header {{ visibility: hidden; }}
    .stDeployButton {{ display: none !important; }}

    /* ── Main container ── */
    .block-container {{
        padding: 2rem 2.5rem 3rem 2.5rem !important;
        max-width: 1500px !important;
        margin: 0 auto;
    }}

    /* ══════════════════════════════════════════════
       SIDEBAR — Premium animated navigation
    ══════════════════════════════════════════════ */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #0d1117 0%, #111827 100%) !important;
        border-right: 1px solid {COLORS['border2']} !important;
        padding-top: 0 !important;
        box-shadow: 4px 0 24px rgba(0,0,0,0.4) !important;
        min-width: 320px !important;
        max-width: 320px !important;
        width: 320px !important;

        transform: translateX(0%) !important;
        margin-left: 0px !important;  
    }}
    section[data-testid="stSidebar"] {{
        left: 0 !important;    
    }}

    /* Sidebar collapse button */
    [data-testid="stSidebarCollapsedControl"] {{
        background: {COLORS['surface']} !important;
        border-radius: 0 8px 8px 0 !important;
        border: 1px solid {COLORS['border2']} !important;
        border-left: none !important;
    }}

    /* ── Radio nav items — key to instant feel ── */
    [data-testid="stSidebar"] .stRadio > div {{
        gap: 0.2rem !important;
        flex-direction: column !important;
    }}
    [data-testid="stSidebar"] .stRadio label {{
        display: flex !important;
        align-items: center !important;
        padding: 0.65rem 1rem !important;
        border-radius: 10px !important;
        cursor: pointer !important;
        transition: all 0.15s ease !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        color: {COLORS['text_muted']} !important;
        background: transparent !important;
        border: 1px solid transparent !important;
        margin: 0.05rem 0.5rem !important;
        user-select: none !important;
    }}
    [data-testid="stSidebar"] .stRadio label:hover {{
        background: rgba(79,142,247,0.08) !important;
        color: {COLORS['text']} !important;
        border-color: rgba(79,142,247,0.2) !important;
        transform: translateX(3px) !important;
    }}
    /* Active nav item — glowing selected state */
    [data-testid="stSidebar"] .stRadio label[data-checked="true"],
    [data-testid="stSidebar"] .stRadio input:checked + div {{
        background: linear-gradient(135deg, rgba(79,142,247,0.15), rgba(124,92,191,0.15)) !important;
        color: #fff !important;
        border-color: rgba(79,142,247,0.35) !important;
        box-shadow: 0 0 12px rgba(79,142,247,0.15), inset 0 0 0 1px rgba(79,142,247,0.2) !important;
    }}
    /* Hide the raw radio circle */
    [data-testid="stSidebar"] .stRadio input[type="radio"] {{
        display: none !important;
    }}
    [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] {{
        pointer-events: none;
    }}
    /* Full-width label so entire row is clickable */
    [data-testid="stSidebar"] .stRadio > div > label {{
        width: 100% !important;
    }}

    /* ── Sidebar logout button override ── */
    [data-testid="stSidebar"] .stButton > button {{
        background: rgba(239,68,68,0.1) !important;
        color: #ef4444 !important;
        border: 1px solid rgba(239,68,68,0.25) !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        padding: 0.5rem 1rem !important;
        margin: 0 0.5rem !important;
        transition: all 0.15s ease !important;
        width: calc(100% - 1rem) !important;
        box-shadow: none !important;
    }}
    [data-testid="stSidebar"] .stButton > button:hover {{
        background: rgba(239,68,68,0.2) !important;
        border-color: rgba(239,68,68,0.5) !important;
        transform: none !important;
        opacity: 1 !important;
    }}
    /* Confirmation Yes button — solid red */
    [data-testid="stSidebar"] [data-testid="column"]:first-child .stButton > button {{
        background: rgba(239,68,68,0.85) !important;
        color: #fff !important;
        border-color: transparent !important;
        margin: 0 !important;
        width: 100% !important;
    }}
    [data-testid="stSidebar"] [data-testid="column"]:first-child .stButton > button:hover {{
        background: #ef4444 !important;
        opacity: 1 !important;
    }}
    /* Confirmation No button — neutral */
    [data-testid="stSidebar"] [data-testid="column"]:last-child .stButton > button {{
        background: rgba(148,163,184,0.1) !important;
        color: #94a3b8 !important;
        border-color: rgba(148,163,184,0.2) !important;
        margin: 0 !important;
        width: 100% !important;
    }}
    [data-testid="stSidebar"] [data-testid="column"]:last-child .stButton > button:hover {{
        background: rgba(148,163,184,0.2) !important;
        color: #e2e8f0 !important;
        opacity: 1 !important;
    }}

    /* ══════════════════════════════════════════════
       PAGE HEADER
    ══════════════════════════════════════════════ */
    .app-header {{
        background: linear-gradient(135deg, {COLORS['accent']}, {COLORS['accent2']});
        padding: 1rem 1.5rem;
        border-radius: 14px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 0.85rem;
        box-shadow: 0 4px 20px rgba(79,142,247,0.2);
        animation: slideDown 0.3s ease;
    }}
    @keyframes slideDown {{
        from {{ opacity: 0; transform: translateY(-8px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .app-header h1 {{
        font-size: 1.4rem;
        font-weight: 800;
        color: #fff;
        margin: 0;
        letter-spacing: -0.02em;
    }}
    .app-header p {{
        font-size: 0.78rem;
        color: rgba(255,255,255,0.72);
        margin: 0;
        margin-top: 0.1rem;
    }}

    /* ══════════════════════════════════════════════
       KPI CARDS — animated, glowing
    ══════════════════════════════════════════════ */
    .kpi-grid {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1.25rem;
        margin-bottom: 2rem;
    }}
    @media (max-width: 1200px) {{
        .kpi-grid {{ grid-template-columns: repeat(2, 1fr); }}
    }}
    @media (max-width: 768px) {{
        .kpi-grid {{ grid-template-columns: 1fr; }}
    }}
    .kpi-card {{
        background: {COLORS['surface']};
        border: 1px solid {COLORS['border2']};
        border-radius: 14px;
        padding: 1.5rem;
        position: relative;
        overflow: hidden;
        cursor: default;
        transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        animation: fadeUp 0.4s ease both;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    }}
    @keyframes fadeUp {{
        from {{ opacity: 0; transform: translateY(12px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .kpi-card:hover {{
        transform: translateY(-4px) !important;
        box-shadow: 0 12px 32px rgba(0,0,0,0.4) !important;
        border-color: {COLORS['border2']} !important;
    }}
    /* Top accent bar */
    .kpi-card::before {{
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 14px 14px 0 0;
        transition: height 0.2s ease;
    }}
    .kpi-card:hover::before {{ height: 4px; }}
    .kpi-card.blue::before   {{ background: linear-gradient(90deg, {COLORS['accent']}, {COLORS['accent2']}); }}
    .kpi-card.purple::before {{ background: linear-gradient(90deg, {COLORS['accent2']}, #a855f7); }}
    .kpi-card.green::before  {{ background: linear-gradient(90deg, {COLORS['success']}, #16a34a); }}
    .kpi-card.yellow::before {{ background: linear-gradient(90deg, {COLORS['warning']}, #d97706); }}
    .kpi-card.red::before    {{ background: linear-gradient(90deg, {COLORS['danger']}, #dc2626); }}

    /* Background glow blob */
    .kpi-card::after {{
        content: '';
        position: absolute;
        bottom: -20px; right: -20px;
        width: 80px; height: 80px;
        border-radius: 50%;
        opacity: 0.06;
        transition: opacity 0.2s;
    }}
    .kpi-card:hover::after {{ opacity: 0.12; }}
    .kpi-card.blue::after   {{ background: {COLORS['accent']}; }}
    .kpi-card.green::after  {{ background: {COLORS['success']}; }}
    .kpi-card.yellow::after {{ background: {COLORS['warning']}; }}
    .kpi-card.red::after    {{ background: {COLORS['danger']}; }}
    .kpi-card.purple::after {{ background: {COLORS['accent2']}; }}

    .kpi-icon {{ font-size: 1.5rem; margin-bottom: 0.5rem; }}
    .kpi-label {{
        font-size: 0.68rem;
        font-weight: 600;
        color: {COLORS['text_muted']};
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.35rem;
    }}
    .kpi-value {{
        font-size: 1.6rem;
        font-weight: 800;
        color: {COLORS['text']};
        line-height: 1;
        letter-spacing: -0.02em;
    }}
    .kpi-sub {{
        font-size: 0.7rem;
        color: {COLORS['text_muted']};
        margin-top: 0.35rem;
    }}

    /* ══════════════════════════════════════════════
       SECTION HEADINGS
    ══════════════════════════════════════════════ */
    .section-title {{
        font-size: 1rem;
        font-weight: 700;
        color: {COLORS['text']};
        margin: 1.5rem 0 0.85rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid {COLORS['border2']};
        letter-spacing: -0.01em;
        display: flex;
        align-items: center;
        gap: 0.4rem;
    }}

    /* ══════════════════════════════════════════════
       STATUS BADGES
    ══════════════════════════════════════════════ */
    .badge {{
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 20px;
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }}
    .badge-green  {{ background: rgba(34,197,94,0.15);  color: {COLORS['success']}; border: 1px solid rgba(34,197,94,0.3); }}
    .badge-yellow {{ background: rgba(245,158,11,0.15); color: {COLORS['warning']}; border: 1px solid rgba(245,158,11,0.3); }}
    .badge-red    {{ background: rgba(239,68,68,0.15);  color: {COLORS['danger']};  border: 1px solid rgba(239,68,68,0.3); }}
    .badge-blue   {{ background: rgba(79,142,247,0.15); color: {COLORS['accent']};  border: 1px solid rgba(79,142,247,0.3); }}
    .badge-gray   {{ background: rgba(148,163,184,0.1); color: {COLORS['text_muted']}; border: 1px solid rgba(148,163,184,0.2); }}

    /* ══════════════════════════════════════════════
       LOW-STOCK BANNER
    ══════════════════════════════════════════════ */
    .low-stock-banner {{
        background: rgba(245,158,11,0.08);
        border: 1px solid rgba(245,158,11,0.35);
        border-left: 3px solid {COLORS['warning']};
        border-radius: 8px;
        padding: 0.65rem 1rem;
        display: flex;
        align-items: center;
        gap: 0.6rem;
        font-size: 0.82rem;
        color: {COLORS['warning']};
        margin-bottom: 1rem;
        animation: fadeIn 0.3s ease;
    }}
    @keyframes fadeIn {{
        from {{ opacity: 0; }}
        to   {{ opacity: 1; }}
    }}

    /* ══════════════════════════════════════════════
       DATAFRAMES / TABLES
    ══════════════════════════════════════════════ */
    .stDataFrame {{
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid {COLORS['border2']} !important;
    }}
    .stDataFrame thead tr th {{
        background: {COLORS['surface2']} !important;
        color: {COLORS['text_muted']} !important;
        font-size: 0.72rem !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        font-weight: 600 !important;
    }}
    .stDataFrame tbody tr:nth-child(even) td {{
        background: rgba(255,255,255,0.01) !important;
    }}
    .stDataFrame tbody tr:hover td {{
        background: rgba(79,142,247,0.06) !important;
    }}

    /* ══════════════════════════════════════════════
       MAIN BUTTONS — smooth gradient
    ══════════════════════════════════════════════ */
    .main .stButton > button {{
        background: linear-gradient(135deg, {COLORS['accent']}, {COLORS['accent2']}) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        font-size: 0.85rem !important;
        padding: 0.5rem 1.1rem !important;
        transition: all 0.15s ease !important;
        box-shadow: 0 2px 12px rgba(79,142,247,0.25) !important;
        letter-spacing: 0.01em !important;
    }}
    .main .stButton > button:hover {{
        opacity: 0.9 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(79,142,247,0.35) !important;
    }}
    .main .stButton > button:active {{
        transform: translateY(0) !important;
        box-shadow: 0 2px 8px rgba(79,142,247,0.2) !important;
    }}

    /* ══════════════════════════════════════════════
       FORM INPUTS
    ══════════════════════════════════════════════ */
    .stTextInput input,
    .stNumberInput input,
    .stTextArea textarea {{
        background: {COLORS['surface2']} !important;
        border: 1px solid {COLORS['border2']} !important;
        color: {COLORS['text']} !important;
        border-radius: 10px !important;
        font-size: 0.9rem !important;
        transition: border-color 0.15s, box-shadow 0.15s !important;
    }}
    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stTextArea textarea:focus {{
        border-color: {COLORS['accent']} !important;
        box-shadow: 0 0 0 3px rgba(79,142,247,0.15) !important;
        outline: none !important;
    }}
    div[data-baseweb="select"] > div {{
        background: {COLORS['surface2']} !important;
        border: 1px solid {COLORS['border2']} !important;
        border-radius: 10px !important;
        color: {COLORS['text']} !important;
        transition: border-color 0.15s !important;
    }}
    div[data-baseweb="select"] > div:hover {{
        border-color: {COLORS['accent']} !important;
    }}

    /* Labels */
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    .stTextArea label, .stRadio label, .stCheckbox label {{
        font-size: 0.82rem !important;
        font-weight: 500 !important;
        color: {COLORS['text_muted']} !important;
        margin-bottom: 0.25rem !important;
    }}

    /* ══════════════════════════════════════════════
       FORM CONTAINER
    ══════════════════════════════════════════════ */
    .stForm {{
        background: {COLORS['surface']} !important;
        border: 1px solid {COLORS['border2']} !important;
        border-radius: 14px !important;
        padding: 1.25rem !important;
        animation: fadeIn 0.25s ease;
    }}

    /* Form submit button */
    .stForm .stButton > button {{
        background: linear-gradient(135deg, {COLORS['accent']}, {COLORS['accent2']}) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        box-shadow: 0 2px 12px rgba(79,142,247,0.25) !important;
        transition: all 0.15s ease !important;
    }}
    .stForm .stButton > button:hover {{
        opacity: 0.9 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(79,142,247,0.35) !important;
    }}

    /* ══════════════════════════════════════════════
       ALERTS / MESSAGES
    ══════════════════════════════════════════════ */
    .stAlert {{
        border-radius: 10px !important;
        font-size: 0.84rem !important;
        border-left-width: 3px !important;
        animation: slideIn 0.2s ease !important;
    }}
    @keyframes slideIn {{
        from {{ opacity: 0; transform: translateX(-8px); }}
        to   {{ opacity: 1; transform: translateX(0); }}
    }}

    /* ══════════════════════════════════════════════
       EXPANDERS
    ══════════════════════════════════════════════ */
    details {{
        background: {COLORS['surface']} !important;
        border: 1px solid {COLORS['border2']} !important;
        border-radius: 12px !important;
        margin-bottom: 0.6rem !important;
        transition: box-shadow 0.15s !important;
        overflow: hidden !important;
    }}
    details:hover {{
        box-shadow: 0 4px 16px rgba(0,0,0,0.25) !important;
        border-color: rgba(79,142,247,0.25) !important;
    }}
    details[open] {{
        border-color: rgba(79,142,247,0.35) !important;
        box-shadow: 0 4px 20px rgba(79,142,247,0.1) !important;
    }}
    summary {{
        padding: 0.75rem 1rem !important;
        font-size: 0.88rem !important;
        font-weight: 600 !important;
        color: {COLORS['text']} !important;
        cursor: pointer !important;
        list-style: none !important;
        transition: color 0.15s !important;
    }}
    summary:hover {{ color: {COLORS['accent']} !important; }}

    /* ══════════════════════════════════════════════
       TABS
    ══════════════════════════════════════════════ */
    .stTabs [data-baseweb="tab-list"] {{
        background: {COLORS['surface']} !important;
        border-radius: 10px !important;
        padding: 0.3rem !important;
        gap: 0.25rem !important;
        border: 1px solid {COLORS['border2']} !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        background: transparent !important;
        border-radius: 8px !important;
        color: {COLORS['text_muted']} !important;
        font-size: 0.83rem !important;
        font-weight: 600 !important;
        padding: 0.45rem 0.85rem !important;
        transition: all 0.15s ease !important;
        border: none !important;
    }}
    .stTabs [data-baseweb="tab"]:hover {{
        background: rgba(79,142,247,0.08) !important;
        color: {COLORS['text']} !important;
    }}
    .stTabs [aria-selected="true"] {{
        background: linear-gradient(135deg, {COLORS['accent']}, {COLORS['accent2']}) !important;
        color: #fff !important;
        box-shadow: 0 2px 10px rgba(79,142,247,0.3) !important;
    }}
    .stTabs [data-baseweb="tab-highlight"] {{ display: none !important; }}

    /* ══════════════════════════════════════════════
       SIDEBAR BRANDING
    ══════════════════════════════════════════════ */
    .sidebar-logo {{
        padding: 1.5rem 1rem 1rem;
        border-bottom: 1px solid {COLORS['border2']};
        margin-bottom: 0.75rem;
        background: linear-gradient(180deg, rgba(79,142,247,0.05) 0%, transparent 100%);
    }}
    .sidebar-logo h3 {{
        font-size: 1.05rem;
        font-weight: 800;
        color: {COLORS['text']};
        margin: 0;
        letter-spacing: -0.02em;
    }}
    .sidebar-logo p {{
        font-size: 0.7rem;
        color: {COLORS['text_muted']};
        margin: 0.15rem 0 0;
    }}
    .role-pill {{
        display: inline-block;
        padding: 0.18rem 0.6rem;
        background: linear-gradient(135deg, rgba(79,142,247,0.2), rgba(124,92,191,0.2));
        color: {COLORS['accent']};
        border: 1px solid rgba(79,142,247,0.3);
        border-radius: 20px;
        font-size: 0.65rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-top: 0.4rem;
    }}

    /* ══════════════════════════════════════════════
       LOGIN PAGE
    ══════════════════════════════════════════════ */
    .login-card {{
        max-width: 400px;
        margin: 2rem auto;
        background: {COLORS['surface']};
        border: 1px solid {COLORS['border2']};
        border-radius: 18px;
        padding: 2.25rem 2rem;
        box-shadow: 0 20px 60px rgba(0,0,0,0.5), 0 0 0 1px rgba(79,142,247,0.05);
        animation: fadeUp 0.4s ease;
    }}
    .login-logo {{
        text-align: center;
        margin-bottom: 1.75rem;
    }}
    .login-logo .icon {{ font-size: 3rem; }}
    .login-logo h2 {{
        font-size: 1.5rem;
        font-weight: 800;
        color: {COLORS['text']};
        margin: 0.4rem 0 0;
        letter-spacing: -0.03em;
    }}
    .login-logo p {{
        font-size: 0.8rem;
        color: {COLORS['text_muted']};
        margin: 0.2rem 0 0;
    }}

    /* ══════════════════════════════════════════════
       MISC UTILITIES
    ══════════════════════════════════════════════ */
    hr {{ border-color: {COLORS['border2']} !important; margin: 1rem 0 !important; }}

    /* Custom scrollbar */
    ::-webkit-scrollbar {{ width: 4px; height: 4px; }}
    ::-webkit-scrollbar-track {{ background: transparent; }}
    ::-webkit-scrollbar-thumb {{ background: {COLORS['border2']}; border-radius: 4px; }}
    ::-webkit-scrollbar-thumb:hover {{ background: {COLORS['accent']}; }}

    /* Code blocks */
    code {{
        font-family: 'JetBrains Mono', monospace !important;
        background: {COLORS['surface2']} !important;
        border: 1px solid {COLORS['border2']} !important;
        border-radius: 5px !important;
        padding: 0.1rem 0.4rem !important;
        font-size: 0.82em !important;
        color: {COLORS['accent']} !important;
    }}

    /* Tooltip / help icons */
    .stTooltipIcon {{ color: {COLORS['text_muted']} !important; }}

    /* Progress bars */
    .stProgress > div > div {{
        background: linear-gradient(90deg, {COLORS['accent']}, {COLORS['accent2']}) !important;
        border-radius: 4px !important;
    }}

    /* ══════════════════════════════════════════════
       MOBILE RESPONSIVE
    ══════════════════════════════════════════════ */
    @media (max-width: 640px) {{
        .kpi-grid {{ grid-template-columns: repeat(2, 1fr); gap: 0.65rem; }}
        .kpi-value {{ font-size: 1.3rem; }}
        .kpi-card {{ padding: 0.85rem 0.75rem; border-radius: 12px; }}
        .app-header {{ padding: 0.85rem 1rem; border-radius: 12px; }}
        .app-header h1 {{ font-size: 1.15rem; }}
        .block-container {{ padding: 0.85rem 0.65rem 3rem !important; }}
        .stTabs [data-baseweb="tab"] {{ padding: 0.35rem 0.6rem !important; font-size: 0.78rem !important; }}
    }}
    </style>
    """, unsafe_allow_html=True)


# ── Reusable HTML components ──────────────────────────────────────────────────
def kpi_card(icon: str, label: str, value: str, sub: str = "", color: str = "blue") -> str:
    """Return HTML for a single animated KPI card."""
    return f"""
    <div class="kpi-card {color}">
        <div class="kpi-icon">{icon}</div>
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {'<div class="kpi-sub">'+sub+'</div>' if sub else ''}
    </div>
    """


def status_badge(text: str) -> str:
    """Return a colored status badge based on text value."""
    mapping = {
        "delivered":    "green",
        "paid":         "green",
        "active":       "green",
        "processing":   "blue",
        "in transit":   "blue",
        "scheduled":    "blue",
        "out for delivery": "blue",
        "pending":      "yellow",
        "unpaid":       "red",
        "partial":      "yellow",
        "cancelled":    "gray",
        "failed":       "red",
        "inactive":     "gray",
        "low stock":    "red",
    }
    cls = mapping.get(text.lower(), "gray")
    return f'<span class="badge badge-{cls}">{text}</span>'


def low_stock_banner(count: int) -> str:
    """Return a warning banner HTML for low-stock items."""
    return f"""
    <div class="low-stock-banner">
        ⚠️ <strong>{count} item{'s' if count != 1 else ''}</strong>
        below minimum stock level — reorder required.
    </div>
    """
