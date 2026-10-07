"""Synthetic scam / legitimate message corpus in English, Bangla and romanised Bangla.

Messages are composed from openers, class-specific bodies and closers, then noised
(typos, casing, digit swaps, spacing). The train/test split is made by *body*, so the
test set measures unseen phrasings rather than memorised templates.

Run:  python -m pipeline.generate_messages
"""
import numpy as np
import pandas as pd
from app.config import ROOT

SEED, PER_BODY = 7, 45
BRANDS = ['bKash', 'Nagad', 'Rocket', 'upay', 'your bank', 'the wallet']
NAMES = ['Rahim', 'Karim', 'Sadia', 'Nusrat', 'Tanvir', 'Mitu', 'Arif', 'Sumi']
LINKS = ['http://bit.ly/{r}', 'https://{b}-verify.{r}.top/login', 'www.{b}-bonus.{r}.xyz', 'http://tinyurl.com/{r}', 'https://secure-{b}.{r}.info']
SCAM = {
 'credential_request': {
  'en': ['an OTP has been sent to your phone, tell me the code to complete verification', 'please send the 6 digit code and your PIN so we can update your account',
         'we need your PIN to reverse the transaction, reply with it now', 'share the verification code you just received to keep your {brand} account active',
         'I am calling from {brand} head office, confirm your PIN and the OTP for KYC update'],
  'bn': ['আপনার ফোনে একটি ওটিপি গেছে, কোডটি আমাকে বলুন', 'আপনার একাউন্ট আপডেট করতে পিন নম্বর ও ৬ সংখ্যার কোডটি পাঠান', 'লেনদেন বাতিল করতে আপনার পিন দরকার, এখনই রিপ্লাই দিন',
         '{brand} অফিস থেকে বলছি, ভেরিফিকেশন কোডটি বলুন নাহলে একাউন্ট বন্ধ হবে', 'কেওয়াইসি আপডেটের জন্য আপনার গোপন পিন ও কোডটি জানান'],
  'bl': ['apnar phone e ekta otp gese, code ta amake bolun', 'account update korte pin number r 6 digit er code ta pathan', 'transaction cancel korte apnar pin lagbe, ekhoni reply din',
         '{brand} office theke bolchi, verification code ta bolun nahole account bondho hobe', 'kyc update er jonno apnar gopon pin ar code ta janan']},
 'account_block_support': {
  'en': ['your {brand} account has been suspended due to unusual activity, call {num} immediately', 'your wallet will be blocked within 24 hours, contact our agent at {num}',
         'your account is temporarily locked, to unlock call customer care {num} now', 'NID verification failed and your account will be closed today, call {num}'],
  'bn': ['আপনার {brand} একাউন্ট সাময়িকভাবে বন্ধ করা হয়েছে, এখনই {num} নম্বরে কল করুন', 'আপনার একাউন্ট ২৪ ঘণ্টার মধ্যে ব্লক হয়ে যাবে, এজেন্টের সাথে যোগাযোগ করুন {num}',
         'আপনার একাউন্ট লক হয়েছে, চালু করতে কাস্টমার কেয়ার {num} এ ফোন দিন', 'এনআইডি যাচাই ব্যর্থ, আজই একাউন্ট বন্ধ হবে, জরুরি কল করুন {num}'],
  'bl': ['apnar {brand} account samoyik bondho kora hoyeche, ekhoni {num} e call korun', 'apnar account 24 ghontar moddhe block hoye jabe, agent er sathe jogajog korun {num}',
         'apnar account lock hoyeche, chalu korte customer care {num} e phone din', 'nid jachai bertho, aj e account bondho hobe, joruri call korun {num}']},
 'prize_lottery': {
  'en': ['congratulations you have won {amt} taka in the {brand} lucky draw, claim your prize today', 'you are selected as the winner of a new smartphone and {amt} tk bonus',
         'your number won the lottery, to receive {amt} taka contact {num}', 'dear customer you got a free gift of {amt} tk, claim before it expires'],
  'bn': ['অভিনন্দন আপনি {brand} লাকি ড্রতে {amt} টাকা জিতেছেন, আজই পুরস্কার নিন', 'আপনি একটি স্মার্টফোন ও {amt} টাকা বোনাস বিজয়ী নির্বাচিত হয়েছেন',
         'আপনার নম্বর লটারি জিতেছে, {amt} টাকা পেতে যোগাযোগ করুন {num}', 'প্রিয় গ্রাহক আপনি {amt} টাকার ফ্রি উপহার পেয়েছেন, মেয়াদ শেষের আগে নিন'],
  'bl': ['ovinondon apni {brand} lucky draw te {amt} taka jitechen, aj e puroskar nin', 'apni ekta smartphone r {amt} taka bonus bijoyi nirbachito hoyechen',
         'apnar number lottery jiteche, {amt} taka pete jogajog korun {num}', 'priyo grahok apni {amt} takar free upohar peyechen, meyad shesher age nin']},
 'advance_fee': {
  'en': ['your loan of {amt} taka is approved, pay a processing fee of 1500 tk to {num} to receive it', 'work from home and earn {amt} tk daily, registration fee only 500 tk',
         'your parcel is held at customs, send {amt} taka clearance charge to release it', 'government grant of {amt} tk is ready for you, send the tax fee first to {num}'],
  'bn': ['আপনার {amt} টাকার লোন অনুমোদিত হয়েছে, পেতে হলে ১৫০০ টাকা প্রসেসিং ফি {num} নম্বরে পাঠান', 'ঘরে বসে প্রতিদিন {amt} টাকা আয় করুন, রেজিস্ট্রেশন ফি মাত্র ৫০০ টাকা',
         'আপনার পার্সেল কাস্টমসে আটকে আছে, ছাড়াতে {amt} টাকা চার্জ পাঠান', 'সরকারি অনুদানের {amt} টাকা প্রস্তুত, আগে ট্যাক্স ফি দিন {num} নম্বরে'],
  'bl': ['apnar {amt} takar loan onumodito hoyeche, pete hole 1500 taka processing fee {num} e pathan', 'ghore boshe protidin {amt} taka ay korun, registration fee matro 500 taka',
         'apnar parcel customs e atke ache, charate {amt} taka charge pathan', 'sorkari onudaner {amt} taka prostut, age tax fee din {num} e']},
 'phishing_link': {
  'en': ['your account needs re-verification, log in here {link}', 'click {link} to receive your pending cashback of {amt} tk', 'update your {brand} app from this link {link} or the service will stop',
         'you have an unclaimed refund, verify your details at {link}'],
  'bn': ['আপনার একাউন্ট পুনরায় যাচাই করতে হবে, এখানে লগইন করুন {link}', 'আপনার {amt} টাকা ক্যাশব্যাক পেতে ক্লিক করুন {link}', 'এই লিংক থেকে {brand} অ্যাপ আপডেট করুন {link} নাহলে সেবা বন্ধ হবে',
         'আপনার একটি রিফান্ড বাকি আছে, তথ্য যাচাই করুন {link}'],
  'bl': ['apnar account abar jachai korte hobe, ekhane login korun {link}', 'apnar {amt} taka cashback pete click korun {link}', 'ei link theke {brand} app update korun {link} nahole sheba bondho hobe',
         'apnar ekta refund baki ache, tottho jachai korun {link}']},
 'refund_wrong_transfer': {
  'en': ['I sent {amt} taka to your number by mistake, please send it back to {num}', 'brother wrong number, {amt} tk went to your account, return it quickly my mother is in hospital',
         'you received {amt} tk from me by mistake, kindly refund to this number', 'sorry I typed the wrong digit and {amt} taka went to you, send back please'],
  'bn': ['ভুল করে আপনার নম্বরে {amt} টাকা চলে গেছে, দয়া করে {num} নম্বরে ফেরত দিন', 'ভাই ভুল নম্বরে {amt} টাকা চলে গেছে, তাড়াতাড়ি ফেরত দিন মা হাসপাতালে',
         'আমার কাছ থেকে ভুলে {amt} টাকা পেয়েছেন, এই নম্বরে ফেরত পাঠান', 'দুঃখিত একটা ডিজিট ভুল হয়েছে, {amt} টাকা আপনার কাছে গেছে, ফেরত দিন'],
  'bl': ['vul kore apnar number e {amt} taka chole gese, doya kore {num} e ferot din', 'vai vul number e {amt} taka chole gese, taratari ferot din ma hospital e',
         'amar kach theke vule {amt} taka peyechen, ei number e ferot pathan', 'dukkhito ekta digit vul hoyeche, {amt} taka apnar kache gese, ferot din']},
 'remote_access': {
  'en': ['install AnyDesk so our engineer can fix your {brand} app', 'please share your screen so I can solve the problem for you', 'download TeamViewer and give me the access number to restore your wallet',
         'to get the refund install this support app and allow screen sharing'],
  'bn': ['আপনার {brand} অ্যাপ ঠিক করতে এনিডেস্ক ইনস্টল করুন', 'সমস্যা সমাধানের জন্য আপনার স্ক্রিন শেয়ার করুন', 'টিমভিউয়ার ডাউনলোড করে অ্যাক্সেস নম্বরটি দিন',
         'রিফান্ড পেতে এই সাপোর্ট অ্যাপ ইনস্টল করে স্ক্রিন শেয়ার চালু করুন'],
  'bl': ['apnar {brand} app thik korte anydesk install korun', 'somossa somadhaner jonno apnar screen share korun', 'teamviewer download kore access number ta din',
         'refund pete ei support app install kore screen share chalu korun']},
 'investment_betting': {
  'en': ['invest {amt} tk today and get double in 7 days, guaranteed profit', 'join our trading group, deposit {amt} taka and earn 30 percent daily', 'online betting bonus, deposit to {num} and get {amt} tk free credit',
         'crypto mining package, send {amt} taka and withdraw profit every day'],
  'bn': ['আজ {amt} টাকা বিনিয়োগ করুন, ৭ দিনে দ্বিগুণ, লাভ নিশ্চিত', 'আমাদের ট্রেডিং গ্রুপে যোগ দিন, {amt} টাকা জমা দিয়ে প্রতিদিন ৩০ শতাংশ আয়', 'অনলাইন বেটিং বোনাস, {num} নম্বরে ডিপোজিট করলে {amt} টাকা ফ্রি',
         'ক্রিপ্টো মাইনিং প্যাকেজ, {amt} টাকা পাঠিয়ে প্রতিদিন লাভ তুলুন'],
  'bl': ['aj {amt} taka biniyog korun, 7 dine digun, lav nishchit', 'amader trading group e jog din, {amt} taka joma diye protidin 30 percent ay', 'online betting bonus, {num} e deposit korle {amt} taka free',
         'crypto mining package, {amt} taka pathiye protidin lav tulun']},
}
LEGIT = {
 'otp_notice': {
  'en': ['your {brand} verification code is {code}. Never share this code with anyone', '{code} is your OTP for login. {brand} staff will never ask for your PIN or OTP',
         'use {code} to confirm your transaction. Do not share it, valid for 3 minutes', 'your one time password is {code}. If you did not request this, ignore this message'],
  'bn': ['আপনার {brand} ভেরিফিকেশন কোড {code}। এই কোড কাউকে দেবেন না', 'লগইনের জন্য আপনার ওটিপি {code}। {brand} কখনো পিন বা ওটিপি চায় না',
         'লেনদেন নিশ্চিত করতে {code} ব্যবহার করুন। কারো সাথে শেয়ার করবেন না', 'আপনার ওয়ান টাইম পাসওয়ার্ড {code}। আপনি অনুরোধ না করলে উপেক্ষা করুন'],
  'bl': ['apnar {brand} verification code {code}. ei code kauke deben na', 'login er jonno apnar otp {code}. {brand} kokhono pin ba otp chay na',
         'lenden nishchit korte {code} bebohar korun. karo sathe share korben na', 'apnar one time password {code}. apni request na korle ignore korun']},
 'transaction_alert': {
  'en': ['you have received Tk {amt} from {num}. Balance Tk {amt2}. TrxID {trx}', 'Send Money Tk {amt} to {num} successful. Fee Tk 5. TrxID {trx}', 'Cash Out Tk {amt} from agent {num} successful. Balance Tk {amt2}',
         'payment of Tk {amt} to merchant successful. TrxID {trx}'],
  'bn': ['আপনি {num} থেকে {amt} টাকা পেয়েছেন। ব্যালেন্স {amt2} টাকা। TrxID {trx}', '{num} নম্বরে {amt} টাকা সেন্ড মানি সফল হয়েছে। ফি ৫ টাকা। TrxID {trx}', 'এজেন্ট {num} থেকে {amt} টাকা ক্যাশ আউট সফল। ব্যালেন্স {amt2} টাকা',
         'মার্চেন্টকে {amt} টাকা পেমেন্ট সফল হয়েছে। TrxID {trx}'],
  'bl': ['apni {num} theke {amt} taka peyechen. balance {amt2} taka. TrxID {trx}', '{num} e {amt} taka send money sofol hoyeche. fee 5 taka. TrxID {trx}', 'agent {num} theke {amt} taka cash out sofol. balance {amt2} taka',
         'merchant ke {amt} taka payment sofol hoyeche. TrxID {trx}']},
 'provider_promo': {
  'en': ['get 10 percent cashback on mobile recharge this week with {brand}. Terms apply', 'pay your electricity bill from the {brand} app and enjoy zero charge this month', 'Eid offer: up to 200 tk discount at selected shops when you pay with {brand}',
         'new feature: you can now save money in the {brand} app. Open the app to learn more'],
  'bn': ['এই সপ্তাহে {brand} দিয়ে মোবাইল রিচার্জে ১০ শতাংশ ক্যাশব্যাক। শর্ত প্রযোজ্য', '{brand} অ্যাপ থেকে বিদ্যুৎ বিল দিন, এই মাসে কোনো চার্জ নেই', 'ঈদ অফার: {brand} দিয়ে পেমেন্টে নির্বাচিত দোকানে ২০০ টাকা পর্যন্ত ছাড়',
         'নতুন ফিচার: এখন {brand} অ্যাপে টাকা জমাতে পারবেন। বিস্তারিত অ্যাপে দেখুন'],
  'bl': ['ei soptahe {brand} diye mobile recharge e 10 percent cashback. shorto projojjo', '{brand} app theke biddut bill din, ei mase kono charge nei', 'eid offer: {brand} diye payment e nirbachito dokane 200 taka porjonto char',
         'notun feature: ekhon {brand} app e taka jomate parben. bistarito app e dekhun']},
 'personal': {
  'en': ['hi {name}, are you coming to dinner tonight? bring the notes please', 'I sent you the {amt} taka for the tuition fee, check when you can', 'meeting moved to 4 pm, call me when you are free',
         'happy birthday {name}! see you on friday', 'did you receive the money I sent yesterday? let me know'],
  'bn': ['{name}, আজ রাতে খেতে আসবে তো? নোটগুলো নিয়ে এসো', 'টিউশন ফির {amt} টাকা পাঠিয়ে দিয়েছি, সময় পেলে দেখে নিও', 'মিটিং বিকাল ৪টায় হবে, ফ্রি হলে কল দিও',
         'শুভ জন্মদিন {name}! শুক্রবার দেখা হবে', 'গতকাল যে টাকা পাঠিয়েছি পেয়েছ? জানিও'],
  'bl': ['{name}, aj rate khete asbe to? note gula niye esho', 'tuition fee r {amt} taka pathiye diyechi, somoy pele dekhe nio', 'meeting bikal 4 tay hobe, free hole call dio',
         'shuvo jonmodin {name}! shukrobar dekha hobe', 'gotokal je taka pathiyechi peyecho? janio']},
 'bill_reminder': {
  'en': ['your electricity bill of Tk {amt} is due on the 25th. Pay from any authorised channel', 'internet bill Tk {amt} for this month has been generated. Thank you for staying with us',
         'your gas bill payment of Tk {amt} was received. Thank you', 'reminder: your installment of Tk {amt} is due next week'],
  'bn': ['আপনার {amt} টাকার বিদ্যুৎ বিল ২৫ তারিখের মধ্যে পরিশোধ করুন', 'এই মাসের ইন্টারনেট বিল {amt} টাকা তৈরি হয়েছে। আমাদের সাথে থাকার জন্য ধন্যবাদ',
         'আপনার {amt} টাকা গ্যাস বিল পরিশোধ গৃহীত হয়েছে। ধন্যবাদ', 'স্মরণ করিয়ে দিচ্ছি: আপনার {amt} টাকার কিস্তি আগামী সপ্তাহে'],
  'bl': ['apnar {amt} takar biddut bill 25 tarikher moddhe porishodh korun', 'ei maser internet bill {amt} taka toiri hoyeche. amader sathe thakar jonno dhonnobad',
         'apnar {amt} taka gas bill porishodh grihito hoyeche. dhonnobad', 'reminder: apnar {amt} takar kisti agami soptahe']},
 'delivery_service': {
  'en': ['your order has been shipped and will arrive tomorrow. Cash on delivery Tk {amt}', 'our rider is on the way with your parcel, please keep Tk {amt} ready', 'your appointment is confirmed for Sunday at 11 am',
         'your ticket is booked. Seat B4, departure 9:30 pm. Have a safe journey'],
  'bn': ['আপনার অর্ডার পাঠানো হয়েছে, আগামীকাল পৌঁছাবে। ক্যাশ অন ডেলিভারি {amt} টাকা', 'আমাদের রাইডার পার্সেল নিয়ে আসছে, {amt} টাকা প্রস্তুত রাখুন', 'রবিবার সকাল ১১টায় আপনার অ্যাপয়েন্টমেন্ট নিশ্চিত হয়েছে',
         'আপনার টিকিট বুক হয়েছে। সিট B4, ছাড়বে রাত ৯:৩০। যাত্রা শুভ হোক'],
  'bl': ['apnar order pathano hoyeche, agamikal pouchabe. cash on delivery {amt} taka', 'amader rider parcel niye asche, {amt} taka prostut rakhun', 'robibar sokal 11 tay apnar appointment nishchit hoyeche',
         'apnar ticket book hoyeche. seat B4, charbe rat 9:30. jatra shuvo hok']},
}
OPEN = {'en': ['', '', 'Dear customer, ', 'Hello, ', 'Sir, ', 'Notice: ', 'Dear user, '], 'bn': ['', '', 'প্রিয় গ্রাহক, ', 'আসসালামু আলাইকুম, ', 'স্যার, ', 'বিজ্ঞপ্তি: '],
        'bl': ['', '', 'priyo grahok, ', 'assalamu alaikum, ', 'sir, ', 'vai, ']}
CLOSE_SCAM = {'en': ['', '', ' Hurry up.', ' This is urgent.', ' Do it immediately.', ' Do not tell anyone.', ' Offer ends today.'],
              'bn': ['', '', ' দেরি করবেন না।', ' এটি জরুরি।', ' এখনই করুন।', ' কাউকে বলবেন না।'], 'bl': ['', '', ' deri korben na.', ' eta joruri.', ' ekhoni korun.', ' kauke bolben na.']}
CLOSE_LEGIT = {'en': ['', '', '', ' Thank you.', ' Helpline 16xxx.', ' Thanks for being with us.'], 'bn': ['', '', '', ' ধন্যবাদ।', ' হেল্পলাইন ১৬xxx।'], 'bl': ['', '', '', ' dhonnobad.', ' helpline 16xxx.']}
SWAP = {'o': '0', 'i': '1', 'a': '@', 'e': '3', 's': '$'}


def noise(text, rng):
    if rng.random() < .15: text = text.upper()
    elif rng.random() < .35: text = text.lower()
    chars = list(text)
    if rng.random() < .30:                                   # typos: swap or drop characters
        for _ in range(int(rng.integers(1, 4))):
            i = int(rng.integers(0, max(len(chars) - 1, 1)))
            if chars[i].isalpha() and i + 1 < len(chars):
                if rng.random() < .5: chars[i], chars[i + 1] = chars[i + 1], chars[i]
                else: chars[i] = ''
    if rng.random() < .12:                                   # look-alike substitutions
        chars = [SWAP.get(c, c) if rng.random() < .25 else c for c in chars]
    text = ''.join(chars)
    if rng.random() < .15: text = text.replace('.', '').replace(',', '')
    if rng.random() < .10: text = text.replace(' ', '  ', 2)
    if rng.random() < .10: text += str(rng.choice([' 🎉', ' 🙏', ' ⚠️', ' ✅', '!!']))
    return text.strip()


def fill(body, rng):
    r = ''.join(rng.choice(list('abcdefghkmnpqrstuvwxyz23456789'), size=6))
    brand = str(rng.choice(BRANDS))
    return body.format(
        brand=brand, name=str(rng.choice(NAMES)), amt=f'{int(rng.choice([500, 1200, 2500, 5000, 10000, 25000, 50000]) * rng.uniform(.6, 1.6)):,}'.replace(',', '' if rng.random() < .5 else ','),
        amt2=f'{int(rng.uniform(100, 60000))}', code=f'{rng.integers(100000, 999999)}', num=f'01{rng.integers(3, 10)}{rng.integers(10**7, 10**8)}' if rng.random() < .7 else f'+8801{rng.integers(3, 10)}{rng.integers(10**7, 10**8)}',
        trx=''.join(rng.choice(list('ABCDEFGHJKLMNPQRSTUVWXYZ0123456789'), size=10)),
        link=str(rng.choice(LINKS)).format(r=r, b=brand.lower().replace(' ', '')))


def main():
    rng = np.random.default_rng(SEED)
    rows = []
    for label, bank, closers in [(1, SCAM, CLOSE_SCAM), (0, LEGIT, CLOSE_LEGIT)]:
        for cat, langs in bank.items():
            for lang, bodies in langs.items():
                for b, body in enumerate(bodies):
                    for _ in range(PER_BODY):
                        text = str(rng.choice(OPEN[lang])) + fill(body, rng)
                        text = text[0].upper() + text[1:] + str(rng.choice(closers[lang]))
                        rows.append({'text': noise(text, rng), 'is_scam': label, 'category': cat, 'language': lang, 'body_id': f'{cat}-{lang}-{b}'})
    df = pd.DataFrame(rows).drop_duplicates('text').sample(frac=1, random_state=SEED)
    df.to_csv(ROOT / 'data/messages.csv', index=False)
    print(f'{len(df):,} messages, {df.body_id.nunique()} distinct bodies, scam share {df.is_scam.mean():.1%}')
    print(df.groupby(['language', 'is_scam']).size().unstack().to_string())


if __name__ == '__main__':
    main()
