import html
import json
import joblib
import streamlit as st
from src.core import ROOT, score
from src.review import investigate

st.set_page_config(page_title='AccountGuard | Security workspace', page_icon='🛡️', layout='wide')
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
</style>''', unsafe_allow_html=True)
if not (ROOT / 'models/model.joblib').exists():
    st.title('Welcome to AccountGuard')
    st.info('Complete these two setup commands, then refresh this page.')
    st.code('python src/generate_data.py\npython src/train.py', language='bash')
    st.stop()

@st.cache_resource
def load_model(): return joblib.load(ROOT / 'models/model.joblib')
@st.cache_data
def load_profiles(): return json.loads((ROOT / 'data/profiles.json').read_text())
profiles = load_profiles()
with st.sidebar:
    st.markdown('## 🛡️ AccountGuard')
    st.caption('Customer security workspace')
    page = st.radio('Workspace', ['Transaction review', 'Model performance'], label_visibility='collapsed')
    st.divider()
    uid = st.selectbox('Customer account', list(profiles), help='All accounts in this demo are synthetic.')
    st.caption('Demo environment · BDT')
    st.divider()
    st.markdown('**How to use this demo**')
    st.caption('Choose a scenario, review the transaction, then select Analyze transaction. Compare a normal payment with a simulated attack.')
p = profiles[uid]
if st.session_state.get('active_user') != uid:
    st.session_state.active_user = uid
    st.session_state.pop('result', None)

st.markdown('<div class="hero"><div><div class="eyebrow">Behavioral account protection</div><h1>Security workspace</h1><p>Review activity. Understand risk. Choose the next action.</p></div><span class="pill">SYNTHETIC DEMO</span></div>', unsafe_allow_html=True)
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
    st.info('These results measure the synthetic simulator. Real-world performance requires representative data, calibrated scores, and separate validation.')
    with st.expander('Technical evaluation details'): st.json(metrics)
    st.stop()

st.subheader('Customer overview')
cols = st.columns(4)
cols[0].metric('Account', uid)
cols[1].metric('Usual district', p['district'])
cols[2].metric('Typical transfer', f"৳{p['median_amount']:,}")
cols[3].metric('Usual hours', f"{p['start_hour']:02d}:00–{p['end_hour']:02d}:59")

st.markdown('### Review a transaction')
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
        'travel_verified': scenario == 'New phone & travel', 'device_verified': scenario == 'New phone & travel'}
    for key, value in defaults.items(): st.session_state['input_' + key] = value
if scenario == 'New phone & travel':
    st.info('Legitimate customers can change devices and travel. Unfamiliar activity is a signal to review, not proof of fraud.')
with st.form('transaction'):
    a, b = st.columns(2)
    amount = a.number_input('Transfer amount (BDT)', min_value=1.0, key='input_amount', step=100.0)
    balance = b.number_input('Available balance (BDT)', min_value=1.0, key='input_balance', step=100.0)
    recipient = a.text_input('Recipient ID', key='input_recipient', help='Compare against the customer’s known recipients.')
    district = b.text_input('Current district', key='input_district')
    with st.expander('Device and activity details', expanded=suspicious):
        c, d = st.columns(2)
        device = c.text_input('Device ID', key='input_device')
        hour = d.number_input('Transaction hour (24-hour clock)', 0, 23, key='input_hour')
        count = c.number_input('Earlier transactions in the last 10 minutes', 0, 100, key='input_count')
        failed = d.number_input('Recent failed PIN attempts', 0, 20, key='input_failed')
    st.markdown('**Investigation context · simulated checks**')
    st.caption('A travel claim is an explanation, not proof. Mark these only to simulate a trusted-channel verification. Verified travel never clears other concerning evidence.')
    travel_verified = st.checkbox('Travel confirmed through a trusted channel (demo)', key='input_travel_verified')
    device_verified = st.checkbox('Device change confirmed through a trusted channel (demo)', key='input_device_verified')
    submitted = st.form_submit_button('Analyze transaction →', type='primary', use_container_width=True)
if submitted:
    st.session_state.pop('result', None)
    try:
        if not all(str(v).strip() for v in [device, recipient, district]): raise ValueError('Enter a device ID, recipient ID and district.')
        event = {'amount':amount, 'balance_before':balance, 'device_id':device.strip(), 'recipient_id':recipient.strip(),
            'district':district.strip(), 'hour':hour, 'transactions_10min':count, 'failed_pin_attempts':failed}
        with st.spinner('Comparing behavior and checking investigation context…'):
            analysis = score(load_model(), event, p)
            review = investigate(analysis['features'], {'travel_verified':travel_verified, 'device_verified':device_verified})
            st.session_state.result = {'analysis':analysis, 'event':event, 'review':review}
    except ValueError as exc: st.error(str(exc))
if 'result' in st.session_state:
    saved = st.session_state.result
    r = saved['analysis']
    st.markdown('### Analysis result')
    st.caption('Result for the last analyzed transaction. Submit again after editing the form.')
    review = saved['review']
    color = '#946000' if review['follow_up'] else '#15724f'
    a, b = st.columns([1, 2])
    with a:
        st.markdown(f'<div class="card"><div class="eyebrow">Raw model signal</div><div class="risk-value" style="color:{color}">{r["score"]:.1f}<span style="font-size:20px;color:#60718a"> / 100</span></div><p style="color:{color};font-weight:700">Requires context · not a verdict</p></div>', unsafe_allow_html=True)
        st.progress(min(1.0, r['score']/100))
    with b:
        title = review['status']
        st.markdown(f'<div class="card"><div class="eyebrow">Suggested next action</div><h3>{title}</h3><p>৳{saved["event"]["amount"]:,.2f} → {html.escape(saved["event"]["recipient_id"])}</p></div>', unsafe_allow_html=True)
        st.write('Next step:', review['action'])
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
st.caption('AccountGuard AI · Independent hackathon prototype · No upay connection · Model scores are uncalibrated, not verified fraud probabilities.')
