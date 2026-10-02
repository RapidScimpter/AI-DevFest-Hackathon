import re
from .reports import normalize_number, lookup_reports

def screen_contact(number, message=''):
    normalized = normalize_number(number)
    patterns = [
        (r'\b(otp|pin|password|verification code)\b|ওটিপি|পিন|পাসওয়ার্ড', 'Security credentials mentioned. Never share an OTP, PIN or password.'),
        (r'\b(urgent|immediately|blocked|suspended)\b|এখনই|জরুরি', 'Urgency or account-blocking language. Verify independently.'),
        (r'\b(prize|lottery|winner|free money)\b|পুরস্কার|লটারি', 'Prize or free-money claim. Verify the offer independently.'),
        (r'\b(send money|processing fee|advance payment)\b|টাকা পাঠান|ফি দিন', 'Payment request. Verify the recipient and reason.'),
        (r'https?://|www\.', 'Link included. Open the official app instead of following an unexpected link.'),
        (r'\b(anydesk|teamviewer|screen.?share|remote access)\b|স্ক্রিন শেয়ার', 'Remote access request. Do not give unknown callers access to your device.')]
    signals = [description for pattern, description in patterns if re.search(pattern, message.casefold())]
    reports = lookup_reports(normalized, message)
    reported = bool(reports['number_reports'] or reports['matching_text_reports'])
    return {'number':normalized, 'status':'Community reports found — unverified' if reported else ('Warning signs found — investigate' if signals else 'Unverified — insufficient evidence'), 'signals':signals, **reports}
