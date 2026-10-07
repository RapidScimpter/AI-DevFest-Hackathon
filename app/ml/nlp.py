"""Scam-message screening: trained classifier plus readable warning signals."""
import re
import unicodedata
from functools import lru_cache
import joblib
from ..config import ROOT

_LOOKALIKE = str.maketrans({'0': 'o', '1': 'i', '@': 'a', '3': 'e', '$': 's'})
_BN_DIGITS = str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789')
SIGNALS = [
    (r'\b(otp|pin|password|verification code|code)\b|ওটিপি|পিন|পাসওয়ার্ড|কোড', 'Security credentials mentioned. Never share an OTP, PIN or password.'),
    (r'\b(urgent|immediately|blocked|suspended|locked|joruri|ekhoni|bondho)\b|এখনই|জরুরি|বন্ধ|ব্লক', 'Urgency or account-blocking language. Verify independently.'),
    (r'\b(prize|lottery|winner|won|free gift|puroskar|jitechen)\b|পুরস্কার|লটারি|জিতেছ', 'Prize or free-money claim. Verify the offer independently.'),
    (r'\b(send money|processing fee|advance payment|registration fee|ferot|pathan)\b|টাকা পাঠান|ফি দিন|ফেরত', 'Payment or refund request. Verify the recipient and reason.'),
    (r'https?://|www\.', 'Link included. Open the official app instead of following an unexpected link.'),
    (r'\b(anydesk|teamviewer|screen.?share|remote access)\b|স্ক্রিন শেয়ার|এনিডেস্ক|টিমভিউয়ার', 'Remote access request. Do not give unknown callers access to your device.'),
]
LABELS = {'credential_request': 'Request for OTP / PIN', 'account_block_support': 'Fake account-block or support call', 'prize_lottery': 'Prize or lottery claim',
          'advance_fee': 'Advance fee (loan, job, parcel)', 'phishing_link': 'Phishing link', 'refund_wrong_transfer': '"Sent by mistake" refund request',
          'remote_access': 'Remote access request', 'investment_betting': 'Investment or betting offer', 'otp_notice': 'Genuine OTP notice',
          'transaction_alert': 'Transaction alert', 'provider_promo': 'Provider promotion', 'personal': 'Personal message',
          'bill_reminder': 'Bill reminder', 'delivery_service': 'Delivery or service notice'}


def normalise(text: str) -> str:
    """Lower-case, fold look-alike characters, mask long digit runs so numbers do not leak."""
    text = unicodedata.normalize('NFKC', text).casefold().translate(_BN_DIGITS)
    text = re.sub(r'https?://\S+|www\.\S+', ' <url> ', text)
    text = re.sub(r'\+?\d[\d,]{4,}', ' <num> ', text)
    text = re.sub(r'(?<=[a-z@$])[013](?=[a-z@$])|[@$]', lambda m: m.group().translate(_LOOKALIKE), text)
    return re.sub(r'\s+', ' ', text).strip()


@lru_cache
def _load():
    return joblib.load(ROOT / 'models/nlp.joblib')


def screen_message(message: str) -> dict:
    message = (message or '').strip()
    signals = [text for pattern, text in SIGNALS if re.search(pattern, message.casefold())]
    if len(message) < 8:
        return {'scam_probability': None, 'category': None, 'signals': signals}
    art = _load()
    prob = float(art['scam'].predict_proba([message])[0, 1])
    cat = art['category'].predict([message])[0]
    return {'scam_probability': round(prob, 3), 'category': LABELS.get(cat, cat), 'flagged': prob >= art['threshold'], 'signals': signals}
