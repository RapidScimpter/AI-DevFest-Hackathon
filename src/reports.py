import hashlib
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from .core import ROOT

DB = ROOT / 'data/contact_reports.sqlite3'

def normalize_number(number):
    value = re.sub(r'[\s()\-]', '', number.strip())
    if not re.fullmatch(r'\+?\d{5,15}', value): raise ValueError('Enter 5–15 digits, with an optional + country code.')
    if re.fullmatch(r'01[3-9]\d{8}', value): value='+880'+value[1:]
    elif re.fullmatch(r'8801[3-9]\d{8}',value): value='+'+value
    elif re.fullmatch(r'008801[3-9]\d{8}',value): value='+'+value[2:]
    return value

def text_key(text): return re.sub(r'\s+', ' ', text.strip().casefold())

def connect(db=DB):
    Path(db).parent.mkdir(parents=True,exist_ok=True)
    conn=sqlite3.connect(db, timeout=10)
    conn.execute('''CREATE TABLE IF NOT EXISTS reports (
        id INTEGER PRIMARY KEY, number TEXT NOT NULL, channel TEXT NOT NULL,
        category TEXT NOT NULL, evidence TEXT NOT NULL, message_key TEXT NOT NULL,
        created_at TEXT NOT NULL, fingerprint TEXT UNIQUE NOT NULL)''')
    return conn

def add_report(number, channel, category, evidence, db=DB):
    number=normalize_number(number)
    if channel not in ['Call','Text message']: raise ValueError('Choose Call or Text message.')
    if category not in ['Spam / unwanted contact','Suspected scam / fraud','Impersonation']: raise ValueError('Choose a report category.')
    evidence=evidence.strip()
    if not 10<=len(evidence)<=4000: raise ValueError('Provide 10–4,000 characters describing the incident or message.')
    key=text_key(evidence)
    fingerprint=hashlib.sha256('\0'.join([number,channel,category,key]).encode()).hexdigest()
    with connect(db) as conn:
        existing=conn.execute('SELECT id FROM reports WHERE fingerprint=?',(fingerprint,)).fetchone()
        if existing:return {'id':existing[0], 'created':False, 'number':number}
        cur=conn.execute('INSERT INTO reports(number,channel,category,evidence,message_key,created_at,fingerprint) VALUES(?,?,?,?,?,?,?)',
            (number,channel,category,evidence,key,datetime.now(timezone.utc).isoformat(timespec='seconds'),fingerprint))
        return {'id':cur.lastrowid,'created':True,'number':number}

def lookup_reports(number,message='',db=DB):
    number=normalize_number(number)
    with connect(db) as conn:
        conn.row_factory=sqlite3.Row
        rows=[dict(r) for r in conn.execute('SELECT id,channel,category,created_at FROM reports WHERE number=? ORDER BY id DESC',(number,))]
        key=text_key(message)
        # Exact matching only for actual text-message reports, not call descriptions.
        matches=conn.execute("SELECT COUNT(*) FROM reports WHERE channel='Text message' AND message_key=?",(key,)).fetchone()[0] if len(key)>=20 else 0
    return {'number_reports':rows,'matching_text_reports':matches}
