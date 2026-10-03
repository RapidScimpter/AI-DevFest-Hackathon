import html
import base64
import json
import joblib
import pandas as pd
from datetime import datetime, timezone
from src.history import prepare, score_from_history
import streamlit as st
from src.core import ROOT, score
from src.review import investigate
from src.contact_check import screen_contact
from src.reports import add_report

LOGO = ROOT / 'assets/surokkha-wallet-logo.jpg'
st.set_page_config(page_title='সুরক্ষা Wallet | Security workspace', page_icon=str(LOGO) if LOGO.exists() else '🛡️', layout='wide', initial_sidebar_state='expanded')
st.markdown('''<style>
.stApp {background:#f5f7fb;color:#16243b;color-scheme:light}
[data-testid="stAppViewContainer"], [data-testid="stHeader"] {background:#f5f7fb}
[data-testid="stMarkdownContainer"], [data-testid="stWidgetLabel"], [data-testid="stMetricLabel"], [data-testid="stMetricValue"], h1,h2,h3,p,label {color:#16243b}
[data-testid="stCaptionContainer"] p {color:#465873 !important}
input {background:#fff !important;color:#16243b !important;-webkit-text-fill-color:#16243b !important}
[data-baseweb="input"], [data-baseweb="base-input"], [data-baseweb="select"] > div {background:#fff !important;color:#16243b !important;border-color:#8191a8 !important}
[data-testid="stExpander"] {background:#fff;color:#16243b;border-color:#b8c4d5}
[data-testid="stExpander"] summary {color:#16243b !important}
[data-testid="stAlert"] {color:#16243b}
button {transition:transform .18s ease,box-shadow .18s ease}
button:hover {transform:translateY(-1px);box-shadow:0 4px 12px #16243b15}
@keyframes reveal {from {opacity:0;transform:translateY(8px)} to {opacity:1;transform:translateY(0)}}
.card,.hero,[data-testid="stMetric"] {animation:reveal .4s ease both}
@media(prefers-reduced-motion:reduce){*{animation:none !important;transition:none !important}}
.block-container {max-width:1250px;padding-top:2rem;padding-bottom:3rem}
h1,h2,h3 {letter-spacing:-.04em}
[data-testid="stSidebar"] {background:#fff;border-right:1px solid #e3e8f0}
[data-testid="stMetric"] {background:white;border:1px solid #e3e8f0;border-radius:16px;padding:18px}
[data-testid="stForm"] {background:white;border:1px solid #e3e8f0;border-radius:18px;padding:24px}
div.stButton > button[kind="primary"], div.stFormSubmitButton > button[kind="primary"] {background:#255ce7;border:0;border-radius:10px}
.card {background:white;border:1px solid #e3e8f0;border-radius:18px;padding:24px;margin:12px 0 20px}
.eyebrow {font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.12em;color:#60718a}
.hero {display:flex;align-items:center;justify-content:space-between;margin-bottom:20px}
.hero h1 {margin:6px 0;font-size:36px}.hero p {color:#60718a;margin:0}
.pill {display:inline-block;padding:7px 12px;background:#eaf0ff;color:#255ce7;border-radius:30px;font-size:12px;font-weight:700}
.risk-value {font-size:58px;font-weight:750;letter-spacing:-.06em;line-height:1.2}
.signal {padding:10px 0;border-bottom:1px solid #edf0f5;font-size:15px}
@media(max-width:700px){.hero{display:block}.hero h1{font-size:28px}}

/* Brand layer: local fonts stay fast and work offline. */
html,body,.stApp,input,button,[data-testid="stMarkdownContainer"] {
 font-family:"Aptos","Segoe UI Variable","Segoe UI",system-ui,sans-serif;
}
h1,h2,h3,.risk-value {font-family:"Segoe UI Variable Display","Aptos Display","Segoe UI",system-ui,sans-serif;font-weight:750;letter-spacing:-.035em}
.stApp,[data-testid="stAppViewContainer"] {background:radial-gradient(ellipse at 95% 0%,#e6f5f3 0,transparent 35%),radial-gradient(ellipse at 5% 30%,#eef0ff 0,transparent 35%),#f6f8fc}
[data-testid="stSidebar"] {background:#152441;border-right:0}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stWidgetLabel"],
[data-testid="stSidebar"] h2,[data-testid="stSidebar"] p,[data-testid="stSidebar"] label {color:#f3f6ff !important}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#c6d2e9 !important}
[data-testid="stSidebar"] [data-baseweb="select"] span {color:#16243b !important}
[data-testid="stSidebar"] hr {border-color:#3b4d6c}
.hero {position:relative;overflow:hidden;min-height:180px;padding:30px 32px;border-radius:24px;
 background:linear-gradient(115deg,#192e57 0%,#294b93 60%,#166d77 100%);box-shadow:0 12px 35px #19335c15;gap:20px}
.hero:after {content:"";position:absolute;right:48px;top:-90px;width:270px;height:270px;border:36px solid #ffffff09;border-radius:50%;pointer-events:none}
.hero h1 {color:#fff;font-size:40px;position:relative;z-index:1}
.hero .eyebrow {color:#acebe3}.hero p {color:#e0eafa;font-size:17px;position:relative;z-index:1;max-width:620px}
.hero .pill {background:#ffffff18;color:#fff;border:1px solid #ffffff40;white-space:nowrap;z-index:1}
[data-testid="stMetric"] {border:1px solid #dfe6f0;border-top:4px solid #456bed;box-shadow:0 4px 15px #15244106;transition:transform .2s ease}
[data-testid="stMetric"]:hover {transform:translateY(-3px)}
[data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] {border-top-color:#159589}
[data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] {border-top-color:#8454cb}
[data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] {border-top-color:#d88a16}
[data-testid="stMetricValue"] {font-size:28px;font-variant-numeric:tabular-nums}
[data-testid="stForm"] {box-shadow:0 8px 30px #182c4b06;border-color:#dce4ef}
div.stFormSubmitButton > button[kind="primary"] {background:linear-gradient(105deg,#315edb,#5842c7);min-height:48px;font-weight:650;box-shadow:0 4px 12px #315edb25}
div.stFormSubmitButton > button[kind="primary"] p {color:#fff !important}
.card {box-shadow:0 6px 24px #182c4b08;border-color:#dce4ef}
.signal {border-bottom-color:#e2e9f2}.signal:before {content:"●";color:#586bd1;margin-right:10px;font-size:10px}
.journey {display:flex;gap:12px;flex-wrap:wrap;margin:8px 0 24px}
.journey span {background:#fff;border:1px solid #dce4ef;border-radius:100px;padding:9px 15px;color:#41526d;font-size:13px;font-weight:600}
.journey b {display:inline-flex;align-items:center;justify-content:center;border-radius:50%;width:22px;height:22px;background:#eaf0ff;color:#315edb;margin-right:7px}
@media(max-width:700px){.hero{padding:24px}.hero h1{font-size:30px}.hero .pill{margin-top:15px;display:inline-block}}


/* Smooth motion with a quiet local-language accent. */
@keyframes softArrival {from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}
@keyframes bannerArrival {from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.hero {animation:bannerArrival .65s cubic-bezier(.22,1,.36,1) both}
.card,[data-testid="stMetric"] {animation:softArrival .55s cubic-bezier(.22,1,.36,1) both}
[data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] {animation-delay:.05s}
[data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] {animation-delay:.10s}
[data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] {animation-delay:.15s}
button,[data-testid="stMetric"] {transition:transform .28s cubic-bezier(.22,1,.36,1),box-shadow .28s ease,background-color .28s ease}
button:active {transform:translateY(0) scale(.99)}
.local-note {font-family:"Nirmala UI","Vrinda","Noto Sans Bengali","Segoe UI",sans-serif;font-size:14px;line-height:1.8;color:#daf3ee !important;margin-top:12px !important}
.local-note span {display:inline-block;margin-right:8px;color:#91e5d5;font-size:17px}
[data-testid="stSidebar"] .local-brand {font-family:"Nirmala UI","Vrinda","Noto Sans Bengali",sans-serif;color:#bfe6e4 !important;font-size:13px;line-height:1.8}
@media(prefers-reduced-motion:reduce){.hero,.card,[data-testid="stMetric"]{animation:none !important;transform:none !important}button,[data-testid="stMetric"]{transition:none !important}}


/* User-selected palette: forest, leaf, lime and yellow. */
.stApp,[data-testid="stAppViewContainer"] {background:radial-gradient(ellipse at 95% 0%,#90b80012 0,transparent 40%),#f7faf2}
[data-testid="stHeader"] {background:#f7faf2}
[data-testid="stSidebar"] {background:#063B00}
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p {color:#e5efd5 !important}
[data-testid="stSidebar"] .local-brand {color:#E1E100 !important}
[data-testid="stSidebar"] hr {border-color:#266210}
.hero {background:linear-gradient(115deg,#063B00 0%,#266210 75%,#466d0e 100%);box-shadow:0 12px 35px #063b0014}
.hero:after {border-color:#E1E10018}
.hero .eyebrow {color:#E1E100}.hero p {color:#f0f7e5}
.hero .pill {background:#E1E100;color:#063B00;border-color:#E1E100}
.local-note {color:#f0f7e5 !important}.local-note span {color:#E1E100}
[data-testid="stMetric"] {border-color:#d9e4cf;border-top-color:#063B00;box-shadow:0 4px 15px #063b0006}
[data-testid="stHorizontalBlock"] > div:nth-child(2) [data-testid="stMetric"] {border-top-color:#266210}
[data-testid="stHorizontalBlock"] > div:nth-child(3) [data-testid="stMetric"] {border-top-color:#90B800}
[data-testid="stHorizontalBlock"] > div:nth-child(4) [data-testid="stMetric"] {border-top-color:#E1E100}
[data-testid="stForm"],.card {border-color:#d9e4cf;box-shadow:0 6px 24px #063b0008}
div.stFormSubmitButton > button[kind="primary"],div.stButton > button[kind="primary"] {background:#266210;border:1px solid #266210;box-shadow:0 4px 12px #063b0018}
div.stFormSubmitButton > button[kind="primary"]:hover,div.stButton > button[kind="primary"]:hover {background:#063B00;border-color:#063B00}
div.stFormSubmitButton > button[kind="primary"] p,div.stButton > button[kind="primary"] p {color:#fff !important}
.journey span {border-color:#d9e4cf;color:#063B00}.journey b {background:#E1E100;color:#063B00}
.signal:before {color:#266210}.signal {border-bottom-color:#e3ecd9}
[data-testid="stMetricValue"] {color:#063B00}
[data-testid="stProgress"] [role="progressbar"] > div {background:#90B800}


/* Native sidebar toggle remains functional at desktop and mobile widths. */
[data-testid="stSidebarCollapsedControl"] button,
[data-testid="stSidebarCollapseButton"] button {position:relative;min-width:40px;min-height:40px;color:transparent !important;background:#E1E100 !important;border:1px solid #90B800 !important;border-radius:10px}
[data-testid="stSidebarCollapsedControl"] button svg,
[data-testid="stSidebarCollapseButton"] button svg {opacity:0}
[data-testid="stSidebarCollapsedControl"] button:after,
[data-testid="stSidebarCollapseButton"] button:after {content:"☰";position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#063B00;font-size:23px;line-height:1;pointer-events:none}
[data-testid="stSidebar"] div.stButton > button {justify-content:flex-start;min-height:49px;padding:12px 16px;border-radius:9px;border:1px solid #528246;background:#154c0b;box-shadow:none}
[data-testid="stSidebar"] div.stButton > button p {color:#f5faef !important;font-size:15px;font-weight:600}
[data-testid="stSidebar"] div.stButton > button:hover {background:#266210;border-color:#90B800;transform:translateX(2px)}
[data-testid="stSidebar"] div.stButton > button[kind="primary"] {background:#E1E100;border-color:#E1E100;box-shadow:0 3px 10px #00000012}
[data-testid="stSidebar"] div.stButton > button[kind="primary"] p {color:#063B00 !important;font-weight:750}
[data-testid="stSidebar"] h2 {font-family:"Nirmala UI","Vrinda","Segoe UI",sans-serif !important;font-size:26px}
@media(prefers-reduced-motion:reduce){[data-testid="stSidebar"] div.stButton > button:hover {transform:none}}

[data-testid="stImage"] img {border-radius:14px;border:1px solid #d9e4cf;background:#fff}
[data-testid="stSidebar"] [data-testid="stImage"] {margin-bottom:8px}
</style>''', unsafe_allow_html=True)
if LOGO.exists():
    logo_data = base64.b64encode(LOGO.read_bytes()).decode('ascii')
    st.markdown(f"""<style>
    [data-testid="stMain"] {{position:relative;isolation:isolate;}}
    [data-testid="stMain"]::before {{
        content:"";position:fixed;inset:0;z-index:-1;pointer-events:none;
        background-image:url("data:image/jpeg;base64,{logo_data}");
        background-position:65% 55%;background-repeat:no-repeat;
        background-size:min(68vw,850px) auto;opacity:.045;
        mix-blend-mode:multiply;
    }}
    [data-testid="stMainBlockContainer"] {{position:relative;z-index:1;}}
    @media(max-width:700px){{[data-testid="stMain"]::before{{background-size:95vw auto;background-position:center 45%;}}}}
    </style>""",unsafe_allow_html=True)

if not (ROOT / 'models/model.joblib').exists() or not (ROOT / 'data/transactions.csv').exists():
    st.title('Welcome to সুরক্ষা Wallet')
    st.info('Complete these two setup commands, then refresh this page.')
    st.code('python src/generate_data.py\npython src/train.py', language='bash')
    st.stop()

@st.cache_resource
def load_model(): return joblib.load(ROOT / 'models/model.joblib')
@st.cache_data
def load_profiles(): return json.loads((ROOT / 'data/profiles.json').read_text())
from src.views.customer import render_customer
render_customer(load_model(), load_profiles())
