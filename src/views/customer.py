import html
from datetime import datetime
import pandas as pd
import streamlit as st
from src.core import ROOT
from src.history import prepare,score_from_history
from src.review import investigate
from src.decision import assess
from src.wallet_store import summary,list_transfers,request_transfer,transition
from src.contact_check import screen_contact
from src.reports import add_report,normalize_number

def money(value):
    whole,decimal=f'{value:.2f}'.split('.')
    tail=whole[-3:];head=whole[:-3];groups=[]
    while head:
        groups.insert(0,head[-2:]);head=head[:-2]
    return (','.join(groups+[tail]) if groups else tail)+'.'+decimal

def render_customer(model,profiles):
    # A fixed preview identity, not authentication or a role selector.
    uid='U0000'
    history=pd.read_csv(ROOT/'data/transactions.csv')
    if 'timestamp' not in history:
        st.error('Update timestamped data before opening the wallet.');st.stop()
    history['timestamp']=pd.to_datetime(history.timestamp)
    own=history[history.user_id==uid].sort_values('timestamp')
    stored=list_transfers(uid)
    prior_requests=[{**t['event'],'transaction_id':f"W-{t['id']}"} for t in stored if t['status']!='Cancelled']
    scoring_history=pd.concat([history,pd.DataFrame(prior_requests)],ignore_index=True) if prior_requests else history
    now=max(pd.Timestamp.now().floor('s'),own.timestamp.max()+pd.Timedelta(minutes=30))
    _,profile,_=prepare({'user_id':uid,'timestamp':now.isoformat()},scoring_history)
    wallet=summary(uid)
    if 'customer_page' not in st.session_state:st.session_state.customer_page='Home'
    with st.sidebar:
        logo=ROOT/'assets/surokkha-wallet-logo.jpg'
        if logo.exists():st.image(str(logo),use_container_width=True)
        st.markdown('**Your wallet. Your peace of mind.**')
        for page,label in [('Home','⌂  Home'),('Send money','↗  Send money'),('Activity','≡  Activity'),('Security','◇  Security'),('Check a contact','☎  Check a contact'),('Report a contact','＋  Report a contact')]:
            if st.button(label,key='customer_nav_'+page,type='primary' if st.session_state.customer_page==page else 'secondary',use_container_width=True):
                st.session_state.customer_page=page;st.rerun()
        st.divider()
        st.caption('Preview account · No real money or identity verification. Balance and requests are stored on this computer.')
    page=st.session_state.customer_page
    if logo.exists():st.image(str(logo),width=230)
    st.caption('PREVIEW WALLET · Payments are simulated; no money is sent.')
    if 'wallet_notice' in st.session_state:st.info(st.session_state.pop('wallet_notice'))
    if page=='Home':
        st.markdown(f'<div class="hero"><div><div class="eyebrow">সুরক্ষা Wallet</div><h1>Your money. A little more peace of mind.</h1><p>Available preview balance</p><h1>৳{money(wallet["available"])}</h1><p class="local-note">নিশ্চিন্তে এগিয়ে চলুন।</p></div><span class="pill">PREVIEW</span></div>',unsafe_allow_html=True)
        if wallet['reserved']:st.caption(f"৳{money(wallet['reserved'])} reserved for pending requests · Total balance ৳{money(wallet['balance'])}")
        st.markdown('### What would you like to do?')
        a,b,c=st.columns(3)
        for col,dest,label in [(a,'Send money','↗ Send money'),(b,'Check a contact','☎ Check a caller'),(c,'Security','◇ Security center')]:
            if col.button(label,use_container_width=True):st.session_state.customer_page=dest;st.rerun()
        pending=[t for t in stored if t['status'] in ['Awaiting confirmation','Under review']]
        if pending:st.info(f"**{len(pending)} request(s) need attention.** Open Security to confirm or review them.")
        st.markdown('### Recent activity')
        if stored:
            show_activity(stored[:5])
        else:st.info('Your new preview wallet has no transfers yet. Send money to try your first request.')
        with st.expander('Earlier account activity'):
            st.caption('Synthetic history used to establish this preview customer’s behavior. These amounts are not part of the current preview balance.')
            st.dataframe(own[['timestamp','amount','recipient_id','district']].tail(8).sort_values('timestamp',ascending=False),hide_index=True,use_container_width=True)
    elif page=='Send money':
        st.subheader('Send money')
        st.markdown('**Choose a recipient and an amount.** We will ask you to review the details before completing the preview transfer.')
        st.metric('Available preview balance',f"৳{money(wallet['available'])}")
        contacts=profile['known_recipients'][:4]
        contact=st.selectbox('Recipient',contacts+['Enter a new number'],format_func=lambda v:'New recipient' if v=='Enter a new number' else f'Saved contact · {v}')
        with st.form('customer_send'):
            phone=st.text_input('Recipient number',placeholder='01712345678',disabled=contact!='Enter a new number')
            amount=st.number_input('Amount (BDT)',min_value=1.0,step=100.0,value=500.0)
            st.caption('৳0 preview fee · No real transfer will occur. Device, time and recent activity are read automatically.')
            send=st.form_submit_button('Review transfer →',type='primary',use_container_width=True)
        if send:
            try:
                recipient=normalize_number(phone) if contact=='Enter a new number' else contact
                event={'user_id':uid,'timestamp':now.isoformat(),'amount':round(amount,2),'balance_before':wallet['available'],
                    'recipient_id':recipient,'device_id':profile['known_devices'][0],'district':profile['district'],'failed_pin_attempts':0}
                analysis,_,_=score_from_history(model,event,scoring_history)
                review=assess(analysis,recipient)
                tid=request_transfer(uid,event,analysis,review)
                st.session_state.wallet_notice=f'Transfer #{tid} needs additional review. Open the concern details below.' if review['requires_review'] else f'Transfer #{tid} is ready for you to review.'
                st.session_state.customer_page='Security';st.rerun()
            except ValueError as exc:st.error(str(exc))
    elif page=='Activity':
        st.subheader('Your activity')
        st.caption('Your preview requests and their current status. Completed requests reduce your preview balance; cancelled requests release reserved funds.')
        if stored:
            show_activity(stored)
            export=pd.DataFrame([{'reference':t['id'],'date':t['timestamp'],'recipient':t['recipient'],'amount_bdt':t['amount'],'status':t['status']} for t in stored])
            st.download_button('Download statement',export.to_csv(index=False),file_name='surokkha_statement.csv',mime='text/csv')
        else:st.info('Your activity will appear here after your first transfer request.')
    elif page=='Security':
        st.subheader('Security center')
        st.markdown('**Stay in control of your transfers.** Confirm requests you recognize. Cancel anything you did not authorize.')
        active=[t for t in stored if t['status'] in ['Awaiting confirmation','Under review']]
        if not active:st.success('**You’re all caught up.** No transfer requests need attention.')
        for t in active:
            with st.container(border=True):
                st.markdown(f"### Transfer #{t['id']} · ৳{money(t['amount'])}")
                st.write('To:',t['recipient']);st.write('Status:',t['status'])
                current_review=assess(t['analysis'],t['recipient'])
                if current_review['requires_review']: st.warning('**Additional checks needed.** This request cannot complete through customer confirmation alone.')
                elif current_review['observations']: st.info('**Please check these details before continuing.**')
                else: st.success('No elevated concern detected by the current checks. Review recipient and amount before confirming.')
                for reason in current_review['follow_up']+current_review['observations']:st.write('• '+reason)
                if current_review['report_count']:st.caption('Reports are unverified local submissions. They raise concerns; they do not establish fraud.')
                level='Review needed' if current_review['requires_review'] else ('Use caution' if current_review['observations'] else 'Routine checks')
                position=85 if current_review['requires_review'] else (50 if current_review['observations'] else 15)
                st.markdown('**Transfer risk zone: '+level+'**')
                st.markdown(f"""<div role="img" aria-label="Transfer concern meter: {level}" style="margin:12px 0 8px">
                <div style="position:relative;height:18px;border-radius:20px;background:linear-gradient(90deg,#15803d 0%,#65a30d 30%,#eab308 50%,#ea580c 70%,#dc2626 100%);border:1px solid #cbd5c1">
                <div style="position:absolute;left:{position}%;top:-5px;transform:translateX(-50%);width:6px;height:28px;border-radius:4px;background:#172b19;box-shadow:0 0 0 2px white"></div>
                </div><div style="display:flex;justify-content:space-between;align-items:center;margin-top:10px;font-size:14px;font-weight:700">
                <span style="color:#15803d">Safe</span><span style="color:#655000">Use caution</span><span style="color:#b91c1c">Dangerous</span></div></div>""",unsafe_allow_html=True)
                st.caption('“Safe” means lower concern in these checks, not guaranteed safety. “Dangerous” means elevated concern requiring review, not confirmed fraud.')
                st.caption('This zone combines unusual activity and reported concerns. It is a review guide, not a percentage chance of fraud.')
                with st.expander('What influenced this check?'):
                    st.write('Local reports for the recipient:',current_review['report_count'])
                    st.caption('Earlier activity, automated analysis and unverified reports inform the recommendation. No warning does not guarantee safety.')
                if t['status']=='Awaiting confirmation':
                    st.markdown('**Was this transfer yours?** Check the recipient and amount before confirming.')
                    a,b=st.columns(2)
                    if a.button('This was me — request review' if current_review['requires_review'] else 'Confirm preview transfer',key=f"confirm_{t['id']}",type='primary',use_container_width=True):
                        try:
                            status=transition(t['id'],uid,'confirm')
                            st.session_state.wallet_notice='Preview transfer completed.' if status=='Completed' else 'Your confirmation is recorded. This request needs further review; no money has been sent.'
                            st.rerun()
                        except ValueError as exc:st.error(str(exc))
                    if b.button('No, I don’t recognize this',key=f"deny_{t['id']}",use_container_width=True):
                        transition(t['id'],uid,'deny');st.session_state.wallet_notice='Request cancelled and reserved preview funds released.';st.rerun()
                else:
                    st.info('**Your confirmation is recorded.** A reviewer still needs to check the activity. An unusual transfer does not automatically mean fraud.')
                    if st.button('Cancel this request',key=f"cancel_{t['id']}"):
                        transition(t['id'],uid,'cancel');st.rerun()
        st.caption('Confirmation records your response in this preview. Production use requires a verified login and trusted authentication channel.')
    elif page=='Check a contact':
        st.subheader('Check a call or message')
        st.markdown('**Something doesn’t feel right?** Check local reports and common warning signs before responding.')
        with st.form('customer_contact'):
            number=st.text_input('Caller or sender number',placeholder='01712345678')
            message=st.text_area('Message or caller request (optional)',help='Never paste actual OTPs, passwords or account details.')
            check=st.form_submit_button('Check contact →',type='primary',use_container_width=True)
        if check:
            try:
                r=screen_contact(number,message)
                st.warning(r['status']) if r['signals'] or r['number_reports'] or r['matching_text_reports'] else st.info(r['status'])
                count=len(r['number_reports'])
                st.metric('Local reports for this number',count)
                if count>=2: st.warning('**Repeated reports — elevated concern.** Independently verify this caller or recipient before responding or paying.')
                elif count==1: st.info('**One report — use caution.** This allegation has not been verified.')
                for signal in r['signals']:st.write('• '+signal)
                if r['matching_text_reports']:st.write('This message matches a previously reported text.')
                st.markdown('**Verify through the official service. Never share an OTP, PIN or password.**')
            except ValueError as exc:st.error(str(exc))
        st.caption('Reports are unverified allegations. No reports does not mean safe. A displayed number can be spoofed.')
    elif page=='Report a contact':
        st.subheader('Report a call or message')
        st.markdown('**Tell us what happened.** Your report will be available to the checker on this installation.')
        with st.form('customer_report',clear_on_submit=True):
            number=st.text_input('Number to report')
            channel=st.selectbox('Contact type',['Call','Text message'])
            category=st.selectbox('Reason',['Spam / unwanted contact','Suspected scam / fraud','Impersonation'])
            text=st.text_area('Message or incident description',max_chars=4000)
            consent=st.checkbox('I removed private details and understand this report is unverified.')
            submit=st.form_submit_button('Submit report →',type='primary',use_container_width=True)
        if submit:
            try:
                if not consent:raise ValueError('Please confirm that private details have been removed.')
                r=add_report(number,channel,category,text)
                st.success('Report saved. Thank you for helping others check suspicious contacts.') if r['created'] else st.info('This identical report is already saved.')
            except ValueError as exc:st.error(str(exc))
        st.caption('Never include actual OTPs, PINs, passwords or financial account details. Reports are stored locally and do not establish guilt.')
    st.divider()
    st.caption('সুরক্ষা Wallet · Preview service · No real payments · Local preview account; no authentication or identity verification')

def show_activity(transfers):
    for t in transfers:
        with st.container(border=True):
            a,b=st.columns([3,1])
            a.markdown('**Sent to '+html.escape(t['recipient'])+'**')
            a.caption(t['timestamp'].replace('T',' ')[:19]+' · '+t['status'])
            b.markdown(f"**৳{money(t['amount'])}**")
