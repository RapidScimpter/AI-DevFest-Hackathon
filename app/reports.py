import hashlib
import re
from sqlalchemy import func, select
from .models import Report

CHANNELS = ['Call', 'Text message']
CATEGORIES = ['Spam / unwanted contact', 'Suspected scam / fraud', 'Impersonation']


def normalize_number(number: str) -> str:
    value = re.sub(r'[\s()\-]', '', number.strip())
    if not re.fullmatch(r'\+?\d{5,15}', value):
        raise ValueError('Enter 5–15 digits, with an optional + country code.')
    if re.fullmatch(r'01[3-9]\d{8}', value): value = '+880' + value[1:]
    elif re.fullmatch(r'8801[3-9]\d{8}', value): value = '+' + value
    elif re.fullmatch(r'008801[3-9]\d{8}', value): value = '+' + value[2:]
    return value


def text_key(text: str) -> str:
    return re.sub(r'\s+', ' ', text.strip().casefold())


def add_report(db, number, channel, category, evidence, reporter_id=None):
    number = normalize_number(number)
    if channel not in CHANNELS: raise ValueError('Choose Call or Text message.')
    if category not in CATEGORIES: raise ValueError('Choose a report category.')
    evidence = evidence.strip()
    if not 10 <= len(evidence) <= 4000: raise ValueError('Provide 10–4,000 characters describing the incident or message.')
    key = text_key(evidence)
    fingerprint = hashlib.sha256('\0'.join([number, channel, category, key]).encode()).hexdigest()
    existing = db.scalar(select(Report).where(Report.fingerprint == fingerprint))
    if existing:
        return existing, False
    report = Report(number=number, channel=channel, category=category, evidence=evidence, message_key=key, fingerprint=fingerprint, reporter_id=reporter_id)
    db.add(report); db.flush()
    return report, True


def report_count(db, recipient: str) -> int:
    try:
        number = normalize_number(recipient)
    except ValueError:          # saved-contact identifiers are not phone numbers
        return 0
    return db.scalar(select(func.count()).select_from(Report).where(Report.number == number)) or 0


def lookup(db, number: str, message: str = '') -> dict:
    number = normalize_number(number)
    rows = db.scalars(select(Report).where(Report.number == number).order_by(Report.id.desc())).all()
    key = text_key(message)
    matches = db.scalar(select(func.count()).select_from(Report).where(Report.channel == 'Text message', Report.message_key == key)) if len(key) >= 20 else 0
    return {'number': number, 'matching_text_reports': matches or 0,
            'number_reports': [{'id': r.id, 'channel': r.channel, 'category': r.category, 'created_at': r.created_at.isoformat(timespec='seconds')} for r in rows]}
