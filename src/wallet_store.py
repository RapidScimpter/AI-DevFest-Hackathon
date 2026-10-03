import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from .core import ROOT
from .decision import assess
DB=ROOT/'data/wallet.sqlite3'
@contextmanager
def connection(db=DB):
    conn=sqlite3.connect(db,timeout=10)
    conn.row_factory=sqlite3.Row
    conn.execute('CREATE TABLE IF NOT EXISTS wallets(user_id TEXT PRIMARY KEY,balance INTEGER NOT NULL)')
    conn.execute('CREATE TABLE IF NOT EXISTS wallet_updates(name TEXT PRIMARY KEY)')
    # One-time preview opening-balance adjustment; preserves prior debits and reservations.
    update=conn.execute("INSERT OR IGNORE INTO wallet_updates(name) VALUES('opening_balance_10_lakh')")
    if update.rowcount:
        conn.execute('UPDATE wallets SET balance=balance+97000000')
    conn.execute('''CREATE TABLE IF NOT EXISTS transfers(id INTEGER PRIMARY KEY,user_id TEXT NOT NULL,amount INTEGER NOT NULL,recipient TEXT NOT NULL,timestamp TEXT NOT NULL,status TEXT NOT NULL,event TEXT NOT NULL,analysis TEXT NOT NULL,review TEXT NOT NULL,response TEXT DEFAULT '',note TEXT DEFAULT '')''')
    conn.execute('CREATE TABLE IF NOT EXISTS actions(id INTEGER PRIMARY KEY,transfer_id INTEGER,created_at TEXT,action TEXT)')
    conn.commit()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback();raise
    finally:conn.close()

def ensure_wallet(user_id,db=DB):
    with connection(db) as c:c.execute('INSERT OR IGNORE INTO wallets VALUES(?,?)',(user_id,100000000))

def summary(user_id,db=DB):
    ensure_wallet(user_id,db)
    with connection(db) as c:
        balance=c.execute('SELECT balance FROM wallets WHERE user_id=?',(user_id,)).fetchone()[0]
        reserved=c.execute("SELECT COALESCE(SUM(amount),0) FROM transfers WHERE user_id=? AND status IN ('Awaiting confirmation','Under review')",(user_id,)).fetchone()[0]
    return {'balance':balance/100,'reserved':reserved/100,'available':(balance-reserved)/100}

def list_transfers(user_id=None,db=DB):
    with connection(db) as c:
        rows=c.execute('SELECT * FROM transfers'+(' WHERE user_id=?' if user_id else '')+' ORDER BY id DESC',(user_id,) if user_id else ()).fetchall()
    result=[{**dict(r),'amount':r['amount']/100,'event':json.loads(r['event']),'analysis':json.loads(r['analysis']),'review':json.loads(r['review'])} for r in rows]
    for item in result:
        if item['analysis'].get('features') and item['status'] in ['Awaiting confirmation','Under review']:
            item['review']=assess(item['analysis'],item['recipient'])
    return result

def request_transfer(user_id,event,analysis,review,db=DB):
    ensure_wallet(user_id,db)
    review=assess(analysis,event['recipient_id']) if analysis.get('features') else review
    cents=round(event['amount']*100)
    if cents<=0:raise ValueError('Enter a positive amount.')
    with connection(db) as c:
        c.execute('BEGIN IMMEDIATE')
        balance=c.execute('SELECT balance FROM wallets WHERE user_id=?',(user_id,)).fetchone()[0]
        held=c.execute("SELECT COALESCE(SUM(amount),0) FROM transfers WHERE user_id=? AND status IN ('Awaiting confirmation','Under review')",(user_id,)).fetchone()[0]
        if cents>balance-held:raise ValueError('Amount exceeds your available preview balance.')
        cur=c.execute('INSERT INTO transfers(user_id,amount,recipient,timestamp,status,event,analysis,review) VALUES(?,?,?,?,?,?,?,?)',(user_id,cents,event['recipient_id'],event['timestamp'],'Awaiting confirmation',json.dumps(event),json.dumps(analysis),json.dumps(review)))
        tid=cur.lastrowid
        c.execute('INSERT INTO actions(transfer_id,created_at,action) VALUES(?,?,?)',(tid,datetime.now(timezone.utc).isoformat(),'Transfer requested'))
        return tid

def transition(tid,user_id,action,note='',db=DB):
    with connection(db) as c:
        c.execute('BEGIN IMMEDIATE')
        row=c.execute('SELECT * FROM transfers WHERE id=? AND user_id=?',(tid,user_id)).fetchone()
        if not row:raise ValueError('Transfer not found.')
        status=row['status'];review=json.loads(row['review'])
        analysis=json.loads(row['analysis'])
        if analysis.get('features'):
            review=assess(analysis,row['recipient'])
            c.execute('UPDATE transfers SET review=? WHERE id=?',(json.dumps(review),tid))
        if status not in ['Awaiting confirmation','Under review']:raise ValueError('This transfer has already been finalized.')
        if action=='confirm' and status=='Awaiting confirmation':
            target='Under review' if review['follow_up'] else 'Completed'
            response='Customer confirms transaction'
        elif action=='deny':target='Cancelled';response='Customer denies transaction'
        elif action=='cancel':target='Cancelled';response='Customer cancelled request'
        elif action in ['approve','reject'] and status=='Under review':
            if not note.strip():raise ValueError('Reviewer notes are required.')
            target='Completed' if action=='approve' else 'Cancelled';response=row['response']
        else:raise ValueError('This action is not available for the current transfer state.')
        if target=='Completed':
            changed=c.execute('UPDATE wallets SET balance=balance-? WHERE user_id=? AND balance>=?',(row['amount'],user_id,row['amount'])).rowcount
            if not changed:raise ValueError('Insufficient preview balance.')
        c.execute('UPDATE transfers SET status=?,response=?,note=? WHERE id=?',(target,response,note,tid))
        c.execute('INSERT INTO actions(transfer_id,created_at,action) VALUES(?,?,?)',(tid,datetime.now(timezone.utc).isoformat(),action+': '+target))
        return target
