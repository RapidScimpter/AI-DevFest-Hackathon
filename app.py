import json
import joblib
import streamlit as st
from src.core import ROOT, score

st.set_page_config(page_title='AccountGuard AI', page_icon='🛡️', layout='wide')
st.title('🛡️ AccountGuard AI')
st.caption('Behavioral account takeover prototype • Synthetic data • No connection to upay')
if not (ROOT / 'models/model.joblib').exists():
    st.error('First run: python src/generate_data.py and python src/train.py')
    st.stop()
@st.cache_resource
def load_model(): return joblib.load(ROOT / 'models/model.joblib')
profiles = json.loads((ROOT / 'data/profiles.json').read_text())
uid = st.sidebar.selectbox('Synthetic customer', list(profiles))
p = profiles[uid]
st.subheader('Trusted customer profile')
st.json(p)
scenario = st.radio('Demo scenario', ['Normal transfer', 'Suspicious transfer', 'Legitimate new phone / travel'], horizontal=True)
suspicious = scenario == 'Suspicious transfer'
changed = scenario != 'Normal transfer'
with st.form('transaction'):
    a, b = st.columns(2)
    amount = a.number_input('Amount (BDT)', min_value=1.0, value=float(p['median_amount'] * (8 if suspicious else 1)))
    balance = b.number_input('Balance before (BDT)', min_value=1.0, value=30000.0)
    device = a.text_input('Device ID', value='NEW_DEVICE' if changed else p['known_devices'][0])
    recipient = b.text_input('Recipient ID', value='NEW_RECIPIENT' if suspicious else p['known_recipients'][0])
    district = a.text_input('District', value='Other' if changed else p['district'])
    hour = b.number_input('Hour (0–23)', 0, 23, 2 if suspicious else 14)
    count = a.number_input('Previous transactions in 10 minutes', 0, 100, 4 if suspicious else 0)
    failed = b.number_input('Recent failed PIN attempts', 0, 20, 3 if suspicious else 0)
    submitted = st.form_submit_button('Score transaction')
if submitted:
    try:
        result = score(load_model(), {'amount': amount, 'balance_before': balance, 'device_id': device,
            'recipient_id': recipient, 'district': district, 'hour': hour,
            'transactions_10min': count, 'failed_pin_attempts': failed}, p)
        st.metric('Model risk score', f"{result['score']} / 100", result['band'] + ' risk')
        st.write('Recommended action:', result['action'])
        st.subheader('Observed behavioral signals')
        for reason in result['signals']: st.write('• ' + reason)
        st.caption('These are factual feature flags, not SHAP contributions or causal explanations. The score is an uncalibrated model output, not a verified fraud probability.')
        if result['band'] != 'Low': st.info('Demo: extra verification would be requested. No real OTP is sent and no account is blocked.')
        with st.expander('Model input'): st.json(result['features'])
    except ValueError as exc: st.error(str(exc))
with st.expander('Evaluation on held-out synthetic users'):
    st.json(json.loads((ROOT / 'models/metrics.json').read_text()))
