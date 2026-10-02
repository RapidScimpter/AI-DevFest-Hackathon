import html
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

st.set_page_config(page_title='সুরক্ষা Wallet | Security workspace', page_icon='🛡️', layout='wide', initial_sidebar_state='expanded')
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

</style>''', unsafe_allow_html=True)
if not (ROOT / 'models/model.joblib').exists() or not (ROOT / 'data/transactions.csv').exists():
    st.title('Welcome to সুরক্ষা Wallet')
    st.info('Complete these two setup commands, then refresh this page.')
    st.code('python src/generate_data.py\npython src/train.py', language='bash')
    st.stop()

@st.cache_resource
def load_model(): return joblib.load(ROOT / 'models/model.joblib')
@st.cache_data
def load_profiles(): return json.loads((ROOT / 'data/profiles.json').read_text())
profiles = load_profiles()
@st.cache_data
def load_history():
    data = pd.read_csv(ROOT / 'data/transactions.csv')
    if 'timestamp' not in data: return None
    data['timestamp'] = pd.to_datetime(data['timestamp'])
    return data
history = load_history()
if history is None:
    st.error('This update needs timestamped data. Stop the app, regenerate data and retrain, then restart.')
    st.code('python src/generate_data.py\npython src/train.py')
    st.stop()
if 'cases' not in st.session_state: st.session_state.cases = []
if 'audit' not in st.session_state: st.session_state.audit = []
def log_action(case_id, action):
    st.session_state.audit.append({'time_utc':datetime.now(timezone.utc).isoformat(timespec='seconds'), 'case_id':case_id, 'action':action})
with st.sidebar:
    st.markdown('## 🛡️ সুরক্ষা Wallet')
    st.caption('Behavior. Context. Confidence.')
    st.markdown('<p class="local-brand">আপনার লেনদেন, আপনার নিয়ন্ত্রণ।</p>', unsafe_allow_html=True)
    st.markdown('**Workspace**')
    navigation = {'Transaction review':'↗  Transaction review', 'Investigation cases':'▣  Investigation cases', 'Activity log':'≡  Activity log', 'Call & text check':'☎  Call & text check', 'Report call / text':'＋  Report call / text', 'Model performance':'◷  Model performance'}
    if 'active_page' not in st.session_state: st.session_state.active_page = 'Transaction review'
    for destination, label in navigation.items():
        if st.button(label, key='nav_'+destination, type='primary' if st.session_state.active_page == destination else 'secondary', use_container_width=True):
            st.session_state.active_page = destination
            st.rerun()
    page = st.session_state.active_page
    st.divider()
    uid = st.selectbox('Customer account', list(profiles), help='All accounts in this demo are synthetic.')
    st.caption('Demo environment · BDT')
    st.divider()
    st.markdown('**Choose what to check**')
    st.caption('Transaction review compares customer behavior. Call & text check screens scam warning signs. Model performance explains our evaluation.')
customer_history = history[history.user_id == uid].sort_values('timestamp')
reference_time = customer_history.timestamp.max() + pd.Timedelta(minutes=30)
_, p, _ = prepare({'user_id':uid, 'timestamp':reference_time.isoformat()}, history)
if st.session_state.get('active_user') != uid:
    st.session_state.active_user = uid
    st.session_state.pop('result', None)

st.markdown('<div class="hero"><div><div class="eyebrow">সুরক্ষা Wallet · Behavioral account protection</div><h1>A little context. A smarter guard.</h1><p>Understand the behavior behind every transaction.</p><p class="local-note"><span aria-hidden="true">৳</span>লেনদেন বুঝুন, তারপর সিদ্ধান্ত নিন।</p></div><span class="pill">SYNTHETIC DEMO</span></div>', unsafe_allow_html=True)
if page == 'Activity log':
    st.subheader('Activity log')
    st.markdown('**Follow the investigation trail:** analyses, simulated verification and case decisions are recorded here.')
    st.caption('This log belongs to this browser session. Download it before refreshing or restarting; it is not a persistent audit service.')
    if st.session_state.audit:
        st.dataframe(pd.DataFrame(st.session_state.audit), use_container_width=True, hide_index=True)
        st.download_button('Download session log', json.dumps(st.session_state.audit,indent=2), file_name='accountguard_activity.json')
    else: st.info('No activity yet. Analyze a transaction to start the log.')
    st.stop()
if page == 'Investigation cases':
    st.subheader('Investigation cases')
    st.markdown('**Review → verify → resolve.** Open a case to record a simulated customer response and a reviewer decision.')
    st.caption('Cases are retained only for this browser session. Customer responses are simulated, not identity verification.')
    if not st.session_state.cases:
        st.info('No cases yet. Analyze a transaction in Transaction review.')
    for case in reversed(st.session_state.cases):
        with st.expander(f"{case['id']} · {case['user_id']} · {case['status']}", expanded=case['status'] != 'Resolved'):
            st.markdown('**Investigation:** ' + case['review']['status'])
            st.write('Amount (BDT):', case['event']['amount'])
            for reason in case['review']['follow_up']: st.write('• ' + reason)
            if case['status'] != 'Resolved':
                response = st.selectbox('Simulated customer response', ['Not contacted', 'Customer confirms travel / device change and transaction', 'Customer denies transaction', 'Customer cannot be reached'], key='response_'+case['id'])
                if st.button('Record simulated response', key='verify_'+case['id']):
                    case['response'] = response
                    case['status'] = 'Awaiting verification' if response in ['Not contacted','Customer cannot be reached'] else 'Customer response recorded'
                    if response.startswith('Customer confirms'):
                        case['review'] = investigate(case['features'], {'travel_verified':True,'device_verified':True})
                    log_action(case['id'],response)
                    st.rerun()
                st.caption('Confirmation explains travel/device novelty; other concerning evidence still requires reviewer attention.')
                outcome = st.selectbox('Reviewer outcome', ['Keep investigating', 'Legitimate activity', 'Reported unauthorized — escalate'], key='outcome_'+case['id'])
                notes = st.text_input('Reviewer notes (required to resolve)', key='notes_'+case['id'])
                if st.button('Save reviewer decision', key='resolve_'+case['id']):
                    if outcome == 'Keep investigating':
                        log_action(case['id'],'Investigation continued'); st.info('Case stays open.')
                    elif not notes.strip(): st.error('Add notes explaining your decision.')
                    elif case.get('response','Not contacted') in ['Not contacted','Customer cannot be reached']:
                        st.error('Record a customer response before resolving this demo case.')
                    elif outcome == 'Legitimate activity' and case.get('response') == 'Customer denies transaction':
                        st.error('Customer denial conflicts with a legitimate outcome. Keep investigating or escalate.')
                    elif outcome.startswith('Reported unauthorized') and case.get('response') != 'Customer denies transaction':
                        st.error('This outcome needs a recorded customer denial. Otherwise keep investigating.')
                    else:
                        case.update(status='Resolved', outcome=outcome, notes=notes.strip())
                        log_action(case['id'],'Resolved: '+outcome)
                        st.rerun()
            else:
                st.success('**Outcome:** ' + case['outcome'])
                st.write(case['notes'])
                st.caption('Reviewer-recorded demo outcome; not a confirmed fraud determination.')
    if st.session_state.cases:
        st.download_button('Download cases',json.dumps(st.session_state.cases,indent=2,default=str),file_name='accountguard_cases.json')
    st.stop()

if page == 'Report call / text':
    st.subheader('Report a call or text')
    st.markdown('**Help the checker learn from reports.** Record an unwanted call, suspected scam or impersonation attempt. Reports are stored locally and shown as unverified community evidence.')
    st.info('**Before submitting:** remove OTPs, PINs, passwords, account details and other private information. A report is an allegation, not proof that the number owner committed fraud; caller numbers can be spoofed.')
    with st.form('submit_report', clear_on_submit=True):
        reported_number = st.text_input('Number to report',placeholder='01712345678 or +8801712345678')
        left,right = st.columns(2)
        channel = left.selectbox('Contact type',['Call','Text message'])
        category = right.selectbox('Reason',['Spam / unwanted contact','Suspected scam / fraud','Impersonation'])
        evidence = st.text_area('Message received or incident description',max_chars=4000,help='For a text report, paste the message after removing private details. For a call, describe what was requested. Minimum 10 characters.')
        confirmed = st.checkbox('I have removed private details and understand this is an unverified report.')
        submit_report = st.form_submit_button('Save report →',type='primary',use_container_width=True)
    if submit_report:
        try:
            if not confirmed: raise ValueError('Confirm that private details have been removed before saving.')
            saved_report=add_report(reported_number,channel,category,evidence)
            if saved_report['created']: st.success(f"**Report #{saved_report['id']} saved.** Check {saved_report['number']} in Call & text check to see it.")
            else: st.info(f"**Already saved as report #{saved_report['id']}.** An identical submission does not increase the count.")
        except ValueError as exc: st.error(str(exc))
    st.caption('Stored in data/contact_reports.sqlite3 on the computer running the app. Reports survive app restarts. Separate computers have separate databases; there is no global reputation feed or automatic model retraining.')
    st.stop()

if page == 'Call & text check':
    st.subheader('☎ Call & text safety check')
    st.markdown('**Unexpected call or text?** Enter the displayed number and optionally paste the message or describe what the caller requested.')
    st.info('**A number alone cannot establish fraud.** This tool searches locally submitted reports and message warning signs. Reports are unverified, and displayed numbers can be spoofed.')
    with st.form('contact_check'):
        number = st.text_input('Caller or sender number', placeholder='01712345678 or +8801712345678')
        message = st.text_area('Message or caller request (optional)', placeholder='Your account will be blocked. Send your OTP now.', help='Remove personal details. Never enter an actual OTP, PIN or password.')
        check = st.form_submit_button('Check warning signs →', type='primary', use_container_width=True)
    if check:
        try:
            report = screen_contact(number, message)
            if report['signals'] or report['number_reports'] or report['matching_text_reports']: st.warning('**' + report['status'] + '**')
            else: st.info('**' + report['status'] + '**')
            st.markdown('**Number entered:** ' + report['number'])
            st.caption('Format accepted. Number ownership and report allegations are unverified.')
            st.markdown('### Previously submitted reports')
            st.metric('Reports for this number',len(report['number_reports']))
            if report['number_reports']:
                st.dataframe(pd.DataFrame(report['number_reports']),hide_index=True,use_container_width=True)
                st.warning('**Reported does not mean confirmed fraud.** Counts are submissions, not verified independent victims.')
            else: st.info('No local reports for this number. This does not establish safety.')
            if report['matching_text_reports']:
                st.info(f"This text exactly matches {report['matching_text_reports']} stored text-message report(s), ignoring case and whitespace.")
            st.caption('Text matching requires at least 20 characters. Edited text may not match. Stored message contents are not displayed here.')
            if report['signals']:
                st.markdown('### What needs attention')
                for signal in report['signals']: st.write('• ' + signal)
            else: st.markdown('**No selected message warning patterns matched**, or no message was provided. Review any stored reports separately; neither result establishes safety.')
            st.markdown('### What to do next')
            st.markdown('**Verify independently:** contact the service through its official app or an independently trusted number. **Protect your credentials:** never share OTPs, PINs or passwords. **Pause before paying:** verify requests before sending money or installing software.')
            st.caption('Simple English/Bengali phrase screening only. Legitimate messages can match and scams can evade it. No warning signs does not mean safe.')
        except ValueError as exc: st.error(str(exc))
    st.caption('Checker queries are not saved. Reports are saved only through Report call / text. No external lookup is made.')
    st.stop()

if page == 'Model performance':
    metrics = json.loads((ROOT / 'models/metrics.json').read_text())
    st.subheader('Model performance')
    st.caption('Evaluation on held-out synthetic customers at a 40/100 review threshold.')
    cols = st.columns(4)
    for col, label, key in zip(cols, ['Precision', 'Attack recall', 'F1 score', 'False-positive rate'], ['precision', 'recall', 'f1', 'false_positive_rate']):
        col.metric(label, f"{metrics[key]:.1%}")
    left, right = st.columns(2)
    with left:
        st.markdown('### What the results mean')
        st.write('Precision: how many flagged events were simulated attacks. Recall: how many simulated attacks were found. False-positive rate: how often legitimate events were flagged.')
        st.metric('Average precision', f"{metrics['pr_auc_average_precision']:.3f}")
    with right:
        import pandas as pd
        st.markdown('### Confusion matrix')
        st.dataframe(pd.DataFrame(metrics['confusion_matrix'], index=['Actual normal', 'Actual attack'], columns=['Predicted normal', 'Flagged for review']), use_container_width=True)
        st.caption(f"{metrics['test_events']:,} test events · customers excluded from training")
    if 'rule_baseline' in metrics:
        st.markdown('### ML versus a basic security rule')
        baseline = metrics['rule_baseline']
        st.caption(baseline['rule'])
        st.dataframe(pd.DataFrame([{'Approach':'Random Forest', **{k:metrics[k] for k in ['precision','recall','false_positive_rate']}}, {'Approach':'Basic rule', **{k:baseline[k] for k in ['precision','recall','false_positive_rate']}}]), hide_index=True, use_container_width=True)
    st.info('These results measure the synthetic simulator. Real-world performance requires representative data, calibrated scores, and separate validation.')
    with st.expander('Technical evaluation details'): st.json(metrics)
    st.stop()

st.markdown('<div class="journey"><span><b>1</b>Choose a customer</span><span><b>2</b>Explore activity</span><span><b>3</b>Investigate with context</span></div>', unsafe_allow_html=True)
st.subheader('Customer at a glance')
st.caption('Calculated from the last 50 earlier synthetic transactions. Recent activity counts are calculated from timestamps, not manually entered.')
cols = st.columns(4)
cols[0].metric('Account', uid)
cols[1].metric('Usual district', p['district'])
cols[2].metric('Typical transfer', f"৳{p['median_amount']:,}")
cols[3].metric('Usual hours', f"{p['start_hour']:02d}:00–{p['end_hour']:02d}:59")

with st.expander('Recent transaction history — see the evidence', expanded=False):
    st.dataframe(customer_history[['timestamp','amount','recipient_id','device_id','district']].tail(15).sort_values('timestamp',ascending=False), hide_index=True, use_container_width=True)
    st.caption('Historical activity includes all earlier observations; attack labels are not used to build profiles.')
st.markdown('### Transaction playground')
st.markdown('**Choose an example, review the details, then click Analyze transaction.** Change any field to explore another situation.')
st.markdown('**Everyday payment:** familiar activity. **Possible account takeover:** several concerning signals. **New phone & travel:** legitimate changes, awaiting a simulated customer response.')
st.caption('ভ্রমণ মানেই ঝুঁকি নয় — আগে প্রেক্ষাপট যাচাই করুন।')
scenario = st.radio('Load a demo scenario', ['Everyday payment', 'Possible account takeover', 'New phone & travel'], horizontal=True,
    help='Scenarios prefill the form. You can edit any value before analysis.')
suspicious = scenario == 'Possible account takeover'
changed = scenario != 'Everyday payment'
form_signature = (uid, scenario)
if st.session_state.get('form_signature') != form_signature:
    st.session_state.form_signature = form_signature
    st.session_state.pop('result', None)
    defaults = {'amount': float(p['median_amount'] * (8 if suspicious else 1)), 'balance':30000.0,
        'device':'NEW_DEVICE' if changed else p['known_devices'][0],
        'recipient':'NEW_RECIPIENT' if suspicious else p['known_recipients'][0],
        'district':'Other' if changed else p['district'], 'hour':2 if suspicious else 14,
        'count':4 if suspicious else 0, 'failed':3 if suspicious else 0,
        'travel_verified': False, 'device_verified': False, 'date':reference_time.date(), 'time':reference_time.time()}
    for key, value in defaults.items(): st.session_state['input_' + key] = value
if scenario == 'New phone & travel':
    st.info('This scenario represents legitimate travel and a device change. Record a simulated customer confirmation in Investigation cases to verify the explanation.')
with st.form('transaction'):
    a, b = st.columns(2)
    amount = a.number_input('Transfer amount (BDT)', min_value=1.0, key='input_amount', step=100.0)
    balance = b.number_input('Available balance (BDT)', min_value=1.0, key='input_balance', step=100.0)
    recipient = a.text_input('Recipient ID', key='input_recipient', help='Compare against the customer’s known recipients.')
    district = b.text_input('Current district', key='input_district')
    with st.expander('Device and activity details', expanded=suspicious):
        c, d = st.columns(2)
        device = c.text_input('Device ID', key='input_device')
        event_date = d.date_input('Transaction date', key='input_date')
        event_time = c.time_input('Transaction time', key='input_time')
        failed = d.number_input('Recent failed PIN attempts', 0, 20, key='input_failed')
    st.caption('Travel and device changes are verified later in Investigation cases. The attack scenario adds three explicitly simulated prior transfers to demonstrate velocity detection.')
    submitted = st.form_submit_button('Analyze transaction →', type='primary', use_container_width=True)
if submitted:
    st.session_state.pop('result', None)
    try:
        if not all(str(v).strip() for v in [device, recipient, district]): raise ValueError('Enter a device ID, recipient ID and district.')
        event = {'amount':amount, 'balance_before':balance, 'device_id':device.strip(), 'recipient_id':recipient.strip(),
            'district':district.strip(), 'timestamp':datetime.combine(event_date,event_time).isoformat(), 'user_id':uid, 'failed_pin_attempts':failed}
        with st.spinner('Comparing behavior and checking investigation context…'):
            scoring_history = history.copy()
            if suspicious:
                burst = [{**event, 'timestamp':(pd.Timestamp(event['timestamp'])-pd.Timedelta(minutes=m)).isoformat(), 'transaction_id':f'DEMO-{m}'} for m in [8,5,2]]
                scoring_history = pd.concat([history,pd.DataFrame(burst)],ignore_index=True)
            analysis, actual_profile, prior = score_from_history(load_model(), event, scoring_history)
            review = investigate(analysis['features'], {})
            case_id = f'CASE-{len(st.session_state.cases)+1:04d}'
            case = {'id':case_id, 'user_id':uid, 'event':event, 'features':analysis['features'], 'review':review, 'status':'Awaiting verification', 'response':'Not contacted'}
            st.session_state.cases.append(case)
            log_action(case_id,'Transaction analyzed using strictly prior history')
            st.session_state.result = {'analysis':analysis, 'event':event, 'review':review, 'case_id':case_id, 'baseline':actual_profile, 'prior_count':len(prior), 'simulated_burst':suspicious}
    except ValueError as exc: st.error(str(exc))
if 'result' in st.session_state:
    saved = st.session_state.result
    r = saved['analysis']
    st.markdown('### Analysis result')
    st.info('**Case created:** ' + saved['case_id'] + '. Open **Investigation cases** in the sidebar to record a simulated customer response and resolve it.')
    st.caption(f"Based on {saved['prior_count']} strictly earlier events. Transfers in previous 10 minutes: {r['features']['transactions_10min']}.")
    if saved['simulated_burst']: st.caption('This scenario includes three simulated prior transfers at −8, −5 and −2 minutes.')
    st.markdown('**This is a review recommendation, not a fraud verdict.** Click Analyze transaction again after editing.')
    review = saved['review']
    color = '#063B00' if review['follow_up'] else '#266210'
    a, b = st.columns([1, 2])
    with a:
        st.markdown(f'<div class="card"><div class="eyebrow">Raw model signal</div><div class="risk-value" style="color:{color}">{r["score"]:.1f}<span style="font-size:20px;color:#60718a"> / 100</span></div><p style="color:{color};font-weight:700">Requires context · not a verdict</p></div>', unsafe_allow_html=True)
        st.progress(min(1.0, r['score']/100))
    with b:
        title = review['status']
        st.markdown(f'<div class="card"><div class="eyebrow">Suggested next action</div><h3>{title}</h3><p>৳{saved["event"]["amount"]:,.2f} → {html.escape(saved["event"]["recipient_id"])}</p></div>', unsafe_allow_html=True)
        st.markdown('**Next step:** ' + review['action'])
        if review['follow_up']:
            st.warning('Investigation pending. Unusual behavior alone does not establish fraud.')
            for item in review['follow_up']: st.write('• ' + item)
        else: st.success('No unresolved signals under the demo investigation policy.')
        for explanation in review['explanations']: st.info(explanation)
        st.caption('No transaction is approved, blocked, or labeled as confirmed fraud by this demo.')
    with st.container(border=True):
        st.markdown('**Observed behavior — evidence to interpret**')
        for reason in r['signals']: st.markdown(f'<div class="signal">{html.escape(reason)}</div>', unsafe_allow_html=True)
        st.caption('These signals describe the input features; they are not SHAP attributions or causal explanations.')
    with st.expander('Inspect the analyzed transaction and model input'):
        st.json(saved)
st.divider()
st.caption('সুরক্ষা Wallet · Independent hackathon prototype · No upay connection · Model scores are uncalibrated, not verified fraud probabilities.')
