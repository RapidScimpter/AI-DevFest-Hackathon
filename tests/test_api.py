from fastapi.testclient import TestClient
from sqlalchemy import text
from app import audit
from app.db import SessionLocal
from app.main import app
from tests.conftest import PASSWORD, PIN, session


def saved(c):
    return c.get('/api/wallet').json()['saved_recipients'][0]['id']


def small(c):
    """A routine amount for this wallet: sent to its most used saved contact."""
    return c.post('/api/transfers', json={'recipient': saved(c), 'amount': 300}).json()


# --- authentication and role-based access -------------------------------------------------
def test_requires_login():
    anon = TestClient(app)
    for path in ('/api/wallet', '/api/analyst/overview', '/api/analyst/audit', '/api/auth/me'):
        assert anon.get(path).status_code == 401


def test_wrong_password_and_lockout():
    anon = TestClient(app)
    for _ in range(5):
        assert anon.post('/api/auth/login', json={'login': '01700000006', 'password': 'nope'}).status_code == 401
    assert anon.post('/api/auth/login', json={'login': '01700000006', 'password': PASSWORD}).status_code == 429


def test_roles_are_separated(customer, analyst):
    assert customer.get('/api/analyst/overview').status_code == 403
    assert customer.get('/api/analyst/audit').status_code == 403
    assert customer.post('/api/analyst/transfers/1/decision', json={'action': 'approve', 'note': 'trying'}).status_code == 403
    assert analyst.get('/api/wallet').status_code == 403
    assert analyst.post('/api/admin/users', json={'login': 'eve', 'name': 'Eve', 'password': 'LongPassword1', 'role': 'admin'}).status_code == 403
    admin = session('admin', 'Admin#2026!')
    assert admin.post('/api/admin/users', json={'login': 'analyst2', 'name': 'Second Analyst', 'password': 'LongPassword1', 'role': 'analyst'}).status_code == 201


def test_customers_cannot_touch_each_other(customer):
    other = session('01700000001', PASSWORD)
    tid = small(other)['id']
    assert customer.post(f'/api/transfers/{tid}/confirm', json={'pin': PIN}).status_code == 404
    assert customer.post(f'/api/transfers/{tid}/cancel', json={}).status_code == 404


def test_registration_and_weak_password():
    anon = TestClient(app)
    body = {'name': 'New User', 'phone': '01811111111', 'password': 'short', 'pin': '1234'}
    assert anon.post('/api/auth/register', json=body).status_code == 422
    assert anon.post('/api/auth/register', json={**body, 'password': 'GoodPass123'}).status_code == 201
    wallet = anon.get('/api/wallet').json()
    assert wallet['summary']['balance'] == 50000 and not any(c['granted'] for c in wallet['consents'].values())
    # No history yet: basic checks only, no model probability.
    t = anon.post('/api/transfers', json={'recipient': '01700000002', 'amount': 100}).json()
    assert t['review']['probability'] is None


# --- wallet ledger ------------------------------------------------------------------------
def test_reserve_settle_and_duplicate(customer):
    before = customer.get('/api/wallet').json()['summary']
    t = small(customer)
    assert t['status'] == 'Awaiting confirmation' and not t['review']['requires_review'], t
    assert 0 <= t['review']['probability'] < .3
    assert customer.get('/api/wallet').json()['summary']['available'] == before['available'] - 300
    assert customer.post(f"/api/transfers/{t['id']}/confirm", json={'pin': PIN}).json()['status'] == 'Completed'
    assert customer.post(f"/api/transfers/{t['id']}/confirm", json={'pin': PIN}).status_code == 400
    assert customer.get('/api/wallet').json()['summary']['balance'] == before['balance'] - 300


def test_overspend_and_wrong_pin(customer):
    assert customer.post('/api/transfers', json={'recipient': saved(customer), 'amount': 9_999_999}).status_code == 400
    t = small(customer)
    assert customer.post(f"/api/transfers/{t['id']}/confirm", json={'pin': '0000'}).status_code == 403
    assert customer.post(f"/api/transfers/{t['id']}/cancel", json={}).json()['status'] == 'Cancelled'


def test_wallet_to_wallet_credit(customer):
    payee = session('01700000003', PASSWORD)
    before = payee.get('/api/wallet').json()['summary']['balance']
    t = customer.post('/api/transfers', json={'recipient': '01700000003', 'amount': 150}).json()
    done = customer.post(f"/api/transfers/{t['id']}/confirm", json={'pin': PIN}).json()
    if done['status'] == 'Completed':
        assert payee.get('/api/wallet').json()['summary']['balance'] == before + 150


# --- fraud flow, analyst metrics ----------------------------------------------------------
def test_takeover_is_held_then_stopped(customer, analyst):
    wallet = customer.get('/api/wallet').json()['summary']
    amount = round(wallet['available'] * .9)
    t = customer.post('/api/transfers', json={'recipient': '01999999999', 'amount': amount, 'txn_type': 'cash_out',
                                               'demo': {'new_device': True, 'district': 'Sylhet', 'failed_pins': 3}}).json()
    assert t['review']['requires_review'] and t['review']['probability'] >= .7, t
    held = customer.post(f"/api/transfers/{t['id']}/confirm", json={'pin': PIN}).json()
    assert held['status'] == 'Under review'
    assert customer.get('/api/wallet').json()['summary']['balance'] == wallet['balance']       # nothing debited
    queue = analyst.get('/api/analyst/transfers', params={'status': 'Under review'}).json()
    case = next(x for x in queue if x['id'] == t['id'])
    assert case['analysis']['pattern'] and case['customer']['login'].endswith('02')
    assert analyst.post(f"/api/analyst/transfers/{t['id']}/decision", json={'action': 'reject', 'note': ''}).status_code == 422
    done = analyst.post(f"/api/analyst/transfers/{t['id']}/decision", json={'action': 'reject', 'note': 'Customer unreachable; device unknown.', 'confirmed_fraud': True}).json()
    assert done['status'] == 'Cancelled' and done['outcome'] == 'confirmed_fraud'
    assert customer.get('/api/wallet').json()['summary']['available'] == wallet['available']    # reservation released
    o = analyst.get('/api/analyst/overview').json()
    assert o['prevented_value']['stopped_by_analyst'] >= amount and o['review_time']['decisions'] >= 1 and o['review_time']['median_seconds'] >= 0


def test_reports_are_rechecked_at_confirmation(customer):
    t = customer.post('/api/transfers', json={'recipient': '01888888888', 'amount': 200}).json()
    for i in range(2):
        r = customer.post('/api/contacts/report', json={'number': '01888888888', 'channel': 'Call', 'category': 'Impersonation', 'evidence': f'Pretended to be support, attempt {i}'})
        assert r.status_code == 201
    assert customer.post(f"/api/transfers/{t['id']}/confirm", json={'pin': PIN}).json()['status'] == 'Under review'
    customer.post(f"/api/transfers/{t['id']}/cancel", json={})


# --- consent ------------------------------------------------------------------------------
def test_consent_controls_signals(customer):
    assert customer.put('/api/consents/device', json={'granted': False}).json()['device']['granted'] is False
    t = small(customer)
    assert any('Device check skipped' in o for o in t['review']['observations'])
    customer.post(f"/api/transfers/{t['id']}/cancel", json={})
    customer.put('/api/consents/device', json={'granted': True})
    assert customer.put('/api/consents/microphone', json={'granted': True}).status_code == 404
    photo = {'image': 'data:image/jpeg;base64,' + 'A' * 200}
    assert customer.post('/api/transfers/1/photo-check', json=photo).status_code == 403          # camera not granted


def test_untrusted_device_is_noticed():
    fresh = session('01700000004', PASSWORD, device='brand-new-phone')
    w = fresh.get('/api/wallet').json()
    assert w['device'] == {'shared': True, 'trusted': False}
    t = fresh.post('/api/transfers', json={'recipient': w['saved_recipients'][0]['id'], 'amount': 500}).json()
    assert any('has not seen before' in o for o in t['review']['observations'])
    fresh.post(f"/api/transfers/{t['id']}/cancel", json={})
    assert fresh.post('/api/devices/trust', json={'pin': '9999'}).status_code == 403
    assert fresh.post('/api/devices/trust', json={'pin': PIN}).status_code == 200
    assert fresh.get('/api/wallet').json()['device']['trusted'] is True


# --- scam message screening ---------------------------------------------------------------
def test_message_screening(customer):
    scam = customer.post('/api/contacts/check', json={'number': '01712345678', 'message': 'আপনার একাউন্ট বন্ধ হয়ে যাবে, এখনই পিন ও ওটিপি কোডটি বলুন'}).json()
    legit = customer.post('/api/contacts/check', json={'number': '01712345678', 'message': 'Kal bikale meeting ache, free hole call dio'}).json()
    assert scam['message']['scam_probability'] > .5 > legit['message']['scam_probability']
    assert customer.post('/api/contacts/check', json={'number': '00000000002'}).json()['level'] == 'danger'


# --- audit log ----------------------------------------------------------------------------
def test_audit_chain_detects_tampering(customer, analyst):
    small(customer)
    log = analyst.get('/api/analyst/audit').json()
    assert log['chain']['intact'] and {'auth.login', 'transfer.requested'} <= {e['action'] for e in log['entries']}
    with SessionLocal() as db:
        first = db.execute(text("SELECT id, action FROM audit_log WHERE action='transfer.requested' LIMIT 1")).one()
        db.execute(text("UPDATE audit_log SET action='edited' WHERE id=:i"), {'i': first.id}); db.commit()
        ok, _, broken = audit.verify(db)
        assert not ok and broken == first.id
        db.execute(text('UPDATE audit_log SET action=:a WHERE id=:i'), {'a': first.action, 'i': first.id}); db.commit()
    with SessionLocal() as db:
        assert audit.verify(db)[0]


def test_staff_pages_load(analyst):
    for path in ('/api/analyst/model', '/api/analyst/drift', '/api/analyst/customers', '/api/analyst/reports'):
        assert analyst.get(path).status_code == 200, path
    assert len(analyst.get('/api/analyst/customers').json()) >= 6
