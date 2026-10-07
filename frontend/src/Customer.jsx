import { useCallback, useEffect, useRef, useState } from 'react'
import { api, locate, setShareDevice, taka, when } from './api.js'
import Meter from './Meter.jsx'
import { Busy, Icon, Steps, useCountUp } from './ui.jsx'

const TABS = [['home', 'Wallet'], ['check', 'Is this a scam?'], ['privacy', 'Permissions']]
const CONSENT_TEXT = {
  device: 'Lets the wallet recognise this phone or browser, so a sign-in from an unknown device can be questioned.',
  location: 'Shares your rough area (division only) when you send money, so a transfer from an unusual place can be questioned.',
  camera: 'Lets you add a live photo when a transfer is held for review. Only a fingerprint of the photo is kept.',
}

const STEPS = ['Details', 'Safety check', 'Done']
const nameOf = (id, wallet) => { const i = wallet.saved_recipients.findIndex((r) => r.id === id); return i < 0 ? id : `Contact ${i + 1}` }

export default function Customer({ user, onSignOut }) {
  const [tab, setTab] = useState('home')
  const [wallet, setWallet] = useState(null)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    try {
      let w = await api('/wallet')
      if (w.consents.device.granted && !w.device.shared) { setShareDevice(true); w = await api('/wallet') }
      setShareDevice(w.consents.device.granted)
      setWallet(w)
    } catch (e) { setError(e.message) }
  }, [])
  useEffect(() => { load() }, [load])
  const shown = useCountUp(wallet?.summary.available)

  return (
    <div className="phone">
      <header className="wallet-head">
        <div className="who"><img src="/logo.jpg" alt="" /><div><strong>{user.name}</strong><span>{user.login}</span></div>
          <button className="ghost" onClick={onSignOut}>Sign out</button></div>
        <p className="balance-label">Money you can use</p>
        <p className="balance" aria-live="polite">{wallet ? taka(Math.round(shown)) : '…'}</p>
        {wallet?.summary.reserved > 0 && <p className="reserved">{taka(wallet.summary.reserved)} is set aside for a transfer that is not finished</p>}
      </header>
      <nav className="tabs" aria-label="Sections">
        {TABS.map(([id, label]) => <button key={id} className={tab === id ? 'on' : ''} onClick={() => setTab(id)}>{label}</button>)}
      </nav>
      {error && <p className="error" role="alert">{error}</p>}
      {!wallet && !error && <div className="panel skeleton" aria-hidden="true"><i /><i /><i /></div>}
      {wallet && tab === 'home' && <Home wallet={wallet} demo={user.demo_mode} reload={load} />}
      {tab === 'check' && <ContactCheck />}
      {wallet && tab === 'privacy' && <Privacy wallet={wallet} reload={load} />}
      <p className="fine centre">Preview with virtual money and synthetic history.</p>
    </div>
  )
}

function Home({ wallet, demo, reload }) {
  const [result, setResult] = useState(null)
  const pending = wallet.transfers.find((t) => t.status === 'Awaiting confirmation')
  const finish = (t) => { setResult(t); reload() }
  return (
    <>
      {wallet.device.shared && !wallet.device.trusted && <TrustDevice reload={reload} />}
      {result ? <Result transfer={result} wallet={wallet} onDone={() => setResult(null)} />
        : pending ? <Confirm transfer={pending} wallet={wallet} onFinish={finish} />
          : <Send wallet={wallet} demo={demo} reload={reload} />}
      <Activity wallet={wallet} reload={reload} />
    </>
  )
}

function TrustDevice({ reload }) {
  const [pin, setPin] = useState(''); const [error, setError] = useState('')
  async function submit(e) {
    e.preventDefault(); setError('')
    try { await api('/devices/trust', { method: 'POST', body: { pin } }); reload() } catch (err) { setError(err.message) }
  }
  return (
    <form className="panel notice" onSubmit={submit}>
      <h2>First time on this device?</h2>
      <p>Your wallet has not seen this phone or browser before, so it will be extra careful. If it is yours, enter your wallet PIN once to mark it as trusted.</p>
      <div className="row"><input type="password" inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value)} placeholder="Wallet PIN" aria-label="Wallet PIN" required />
        <button className="primary">Trust this device</button></div>
      {error && <p className="error" role="alert">{error}</p>}
    </form>
  )
}

function Send({ wallet, demo, reload }) {
  const blank = { recipient: '', amount: '', txn_type: 'send' }, calm = { new_device: false, district: '', failed_pins: 0 }
  const [form, setForm] = useState(blank)
  const [sim, setSim] = useState(calm)
  const [scenario, setScenario] = useState('')
  const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  const first = wallet.saved_recipients[0]?.id || ''
  const SCENARIOS = [
    ['A normal payment', 'A small amount to someone you often pay.', { recipient: first, amount: '500', txn_type: 'send' }, calm],
    ['Someone took over the account', 'Unknown device, another city, wrong PINs, then almost all the money is cashed out.',
      { recipient: '01999999999', amount: String(Math.floor(wallet.summary.available * 0.9)), txn_type: 'cash_out' }, { new_device: true, district: 'Sylhet', failed_pins: 3 }],
    ['Paying a reported scam number', 'A number that other people have already reported.', { recipient: '00000000002', amount: '2000', txn_type: 'send' }, calm],
  ]
  async function submit(e) {
    e.preventDefault(); setError(''); setBusy(true)
    try {
      const coords = wallet.consents.location.granted ? await locate() : null
      const body = { ...form, amount: Number(form.amount), ...(coords || {}) }
      if (demo && (sim.new_device || sim.district || sim.failed_pins)) body.demo = sim
      await api('/transfers', { method: 'POST', body })
      await reload()
    } catch (err) { setError(err.message); setBusy(false) }
  }
  return (
    <form className="panel" onSubmit={submit}>
      <Steps labels={STEPS} current={0} />
      <h2>Send money</h2>
      {wallet.saved_recipients.length > 0 && <div className="people" role="group" aria-label="People you pay often">
        {wallet.saved_recipients.slice(0, 4).map((r, i) => (
          <button type="button" key={r.id} className={form.recipient === r.id ? 'on' : ''} aria-pressed={form.recipient === r.id} onClick={() => setForm({ ...form, recipient: r.id })}>
            <span>{i + 1}</span>Contact {i + 1}</button>))}</div>}
      <label>{wallet.saved_recipients.length > 0 ? 'Or type a mobile number' : 'Mobile number'}
        <input value={wallet.saved_recipients.some((r) => r.id === form.recipient) ? '' : form.recipient} onChange={(e) => setForm({ ...form, recipient: e.target.value })}
          placeholder="01XXXXXXXXX" inputMode="tel" required={!form.recipient} /></label>
      <div className="row">
        <label>Amount (BDT)<input type="number" min="1" step="0.01" value={form.amount} onChange={(e) => setForm({ ...form, amount: e.target.value })} required /></label>
        <label>What for<select value={form.txn_type} onChange={(e) => setForm({ ...form, txn_type: e.target.value })}>
          {Object.entries(wallet.types).map(([k, v]) => <option key={k} value={k}>{v}</option>)}</select></label>
      </div>
      {demo && <details className="demo"><summary>Try an example (demo mode)</summary>
        <p>Pick a story. The form fills itself; press "Check this transfer" to see how the wallet reacts.</p>
        <div className="stories">{SCENARIOS.map(([title, text, f, s]) => (
          <button type="button" key={title} className={scenario === title ? 'on' : ''} onClick={() => { setForm(f); setSim(s); setScenario(title) }}><strong>{title}</strong><span>{text}</span></button>))}</div>
        <details><summary>Set the signals yourself</summary>
          <label className="check"><input type="checkbox" checked={sim.new_device} onChange={(e) => setSim({ ...sim, new_device: e.target.checked })} />Request comes from an unknown device</label>
          <div className="row"><label>Location<select value={sim.district} onChange={(e) => setSim({ ...sim, district: e.target.value })}>
            <option value="">Usual area</option>{wallet.districts.map((d) => <option key={d}>{d}</option>)}</select></label>
            <label>Wrong PIN tries<select value={sim.failed_pins} onChange={(e) => setSim({ ...sim, failed_pins: Number(e.target.value) })}>
              {[0, 1, 2, 3].map((n) => <option key={n}>{n}</option>)}</select></label></div></details></details>}
      {error && <p className="error" role="alert">{error}</p>}
      <button className="primary big" disabled={busy}><Busy on={busy}>Check this transfer</Busy></button>
      <p className="fine">Nothing is sent yet. You will see a safety check first.</p>
    </form>
  )
}

function Reasons({ review }) {
  const all = [...review.follow_up.map((r) => [r, true]), ...review.observations.map((r) => [r, false])]
  if (all.length === 0) return null
  return <ul className="reasons reveal">{all.map(([r, strong], i) => <li key={r} className={strong ? 'strong' : ''} style={{ '--i': i }}>{r}</li>)}</ul>
}

function Confirm({ transfer: t, wallet, onFinish }) {
  const [pin, setPin] = useState(''); const [error, setError] = useState(''); const [busy, setBusy] = useState(false)
  const act = async (path, body) => {
    setError(''); setBusy(true)
    try { onFinish(await api(`/transfers/${t.id}/${path}`, { method: 'POST', body })) } catch (err) { setError(err.message); setPin(''); setBusy(false) }
  }
  const risky = t.review.requires_review
  return (
    <section className={'panel confirm ' + t.review.level}>
      <Steps labels={STEPS} current={1} />
      <p className="sum">{taka(t.amount)} <span>{t.type} to {nameOf(t.recipient, wallet)}</span></p>
      <Meter review={t.review} />
      {(t.review.follow_up.length > 0 || t.review.observations.length > 0) && <h3>What we noticed</h3>}
      <Reasons review={t.review} />
      {risky && <div className="hold"><strong>What happens if you confirm</strong>
        <p>The transfer waits for a person to check it. Your money stays in your wallet until then. If someone is rushing you or asked for your PIN, cancel.</p></div>}
      <form className="row" onSubmit={(e) => { e.preventDefault(); act('confirm', { pin }) }}>
        <input type="password" inputMode="numeric" value={pin} onChange={(e) => setPin(e.target.value)} placeholder="Wallet PIN" aria-label="Wallet PIN" required />
        <button className={'primary' + (risky ? '' : ' go')} disabled={busy}><Busy on={busy}>{risky ? 'Confirm anyway' : 'Confirm and send'}</Busy></button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
      <div className="row split">
        <button className="ghost" disabled={busy} onClick={() => act('cancel', {})}>Cancel transfer</button>
        <button className="ghost danger" disabled={busy} onClick={() => act('cancel', { not_me: true })}>This was not me</button>
      </div>
    </section>
  )
}

function Result({ transfer: t, wallet, onDone }) {
  const who = nameOf(t.recipient, wallet)
  const view = t.status === 'Completed' ? ['done', 'Sent', `${taka(t.amount)} went to ${who}.`]
    : t.status === 'Under review' ? ['held', 'Held for a safety check', `${taka(t.amount)} to ${who} is waiting for a reviewer. Your money is still in your wallet. You can cancel from the list below.`]
      : ['stopped', 'Cancelled', t.response.includes('not my') ? 'Thank you for telling us. Nothing was sent, and the attempt has been recorded.' : 'Nothing was sent. Your money stayed in your wallet.']
  return (
    <section className={'panel outcome ' + view[0]} role="status">
      <Steps labels={STEPS} current={2} />
      <Icon name={view[0]} size={84} />
      <h2>{view[1]}</h2>
      <p>{view[2]}</p>
      <button className="primary" onClick={onDone}>Send another</button>
    </section>
  )
}

function PhotoCheck({ transfer, reload }) {
  const video = useRef(null); const [stream, setStream] = useState(null); const [error, setError] = useState('')
  useEffect(() => () => stream?.getTracks().forEach((t) => t.stop()), [stream])
  async function start() {
    try {
      const s = await navigator.mediaDevices.getUserMedia({ video: { width: 320, height: 240 } })
      setStream(s); video.current.srcObject = s
    } catch { setError('The camera could not be opened. Check the browser permission.') }
  }
  async function capture() {
    const canvas = document.createElement('canvas'); canvas.width = 320; canvas.height = 240
    canvas.getContext('2d').drawImage(video.current, 0, 0, 320, 240)
    try { await api(`/transfers/${transfer.id}/photo-check`, { method: 'POST', body: { image: canvas.toDataURL('image/jpeg', 0.6) } }); setStream(null); reload() }
    catch (err) { setError(err.message) }
  }
  if (transfer.photo_check) return <p className="fine">Live photo added for the reviewer.</p>
  return (
    <div className="photo">
      <video ref={video} autoPlay playsInline muted hidden={!stream} />
      {stream ? <button className="ghost" onClick={capture}>Send photo to reviewer</button> : <button className="ghost" onClick={start}>Add a live photo</button>}
      {error && <p className="error" role="alert">{error}</p>}
    </div>
  )
}

function Activity({ wallet, reload }) {
  const rows = wallet.transfers.filter((t) => t.status !== 'Awaiting confirmation')
  return (
    <section className="panel">
      <div className="row split"><h2>Activity</h2><a className="link" href="/api/statement.csv">Download statement</a></div>
      {rows.length === 0 && <p className="empty">No transfers yet. Your sent, held and cancelled transfers will appear here.</p>}
      <ul className="activity">{rows.map((t) => (
        <li key={t.id}>
          <div className="row split"><strong>{taka(t.amount)}</strong><span className={'status ' + t.status.replace(' ', '-').toLowerCase()}>{{ Completed: 'Sent', 'Under review': 'Held for check', Cancelled: 'Cancelled' }[t.status] || t.status}</span></div>
          <p>{t.type} to {nameOf(t.recipient, wallet)}, {when(t.created_at)}</p>
          {t.status === 'Under review' && <>
            <Reasons review={t.review} />
            {wallet.consents.camera.granted && <PhotoCheck transfer={t} reload={reload} />}
            <button className="ghost" onClick={async () => { await api(`/transfers/${t.id}/cancel`, { method: 'POST', body: {} }); reload() }}>Cancel transfer</button>
          </>}
          {t.note && <p className="note">Reviewer: {t.note}</p>}
        </li>))}</ul>
    </section>
  )
}

function ContactCheck() {
  const [form, setForm] = useState({ number: '', message: '' })
  const [result, setResult] = useState(null); const [error, setError] = useState('')
  const [report, setReport] = useState({ channel: 'Call', category: 'Suspected scam / fraud', evidence: '' }); const [sent, setSent] = useState('')
  async function check(e) {
    e.preventDefault(); setError(''); setSent('')
    try { setResult(await api('/contacts/check', { method: 'POST', body: form })) } catch (err) { setError(err.message); setResult(null) }
  }
  async function submitReport(e) {
    e.preventDefault(); setError('')
    try {
      const r = await api('/contacts/report', { method: 'POST', body: { number: form.number, ...report } })
      setSent(r.created ? 'Report saved. Thank you.' : 'This exact report was already saved.'); setReport({ ...report, evidence: '' })
    } catch (err) { setError(err.message) }
  }
  const m = result?.message
  return (
    <>
      <form className="panel" onSubmit={check}>
        <h2>Is this a scam?</h2>
        <p>Got a strange call or message? Enter the number and paste the text. Nothing you check here is saved.</p>
        <label>Number that contacted you<input value={form.number} onChange={(e) => setForm({ ...form, number: e.target.value })} placeholder="01XXXXXXXXX" required /></label>
        <label>Message text (optional)<textarea rows="4" value={form.message} onChange={(e) => setForm({ ...form, message: e.target.value })} placeholder="Paste the message in Bangla or English" /></label>
        <button className="primary big">Check now</button>
        {error && <p className="error" role="alert">{error}</p>}
      </form>
      {result && <section className={'panel result ' + result.level} role="status">
        <div className="verdict"><Icon name={result.level} size={40} /><h2>{result.status}</h2></div>
        {m?.scam_probability != null && <><p>Chance this message is a scam: <strong>{Math.round(m.scam_probability * 100)}%</strong>. It reads like: {m.category}.</p>
          <span className="gauge"><i style={{ width: Math.max(3, m.scam_probability * 100) + '%' }} /></span></>}
        <p>{result.number_reports.length} report{result.number_reports.length === 1 ? '' : 's'} for {result.number}. Reports are unverified, and caller numbers can be faked.</p>
        {m?.signals.length > 0 && <ul className="reasons">{m.signals.map((s) => <li key={s}>{s}</li>)}</ul>}
      </section>}
      <form className="panel" onSubmit={submitReport}>
        <h2>Report this number</h2>
        <div className="row"><label>How they contacted you<select value={report.channel} onChange={(e) => setReport({ ...report, channel: e.target.value })}><option>Call</option><option>Text message</option></select></label>
          <label>What it was<select value={report.category} onChange={(e) => setReport({ ...report, category: e.target.value })}>
            <option>Suspected scam / fraud</option><option>Impersonation</option><option>Spam / unwanted contact</option></select></label></div>
        <label>What happened<textarea rows="3" value={report.evidence} onChange={(e) => setReport({ ...report, evidence: e.target.value })} minLength={10} required
          placeholder="Describe the call or paste the message. Leave out your own PIN, OTP or password." /></label>
        <button className="primary" disabled={!form.number}>Save report</button>
        {sent && <p className="ok" role="status">{sent}</p>}
      </form>
    </>
  )
}

function Privacy({ wallet, reload }) {
  const [error, setError] = useState('')
  async function toggle(permission, granted) {
    setError('')
    try {
      if (granted && permission === 'location' && !(await locate())) throw new Error('Location is blocked in this browser. Allow it in the browser settings, then try again.')
      await api('/consents/' + permission, { method: 'PUT', body: { granted } })
      if (permission === 'device') setShareDevice(granted)
      reload()
    } catch (err) { setError(err.message) }
  }
  return (
    <section className="panel">
      <h2>Permissions</h2>
      <p>Each one is off until you turn it on, and you can turn it off again at any time. Without a permission the wallet still works; that signal is left out of safety checks.</p>
      <ul className="consents">{Object.entries(wallet.consents).map(([key, c]) => (
        <li key={key}>
          <div><strong>{c.label}</strong><p>{CONSENT_TEXT[key]}</p>
            {c.updated_at && <p className="fine">{c.granted ? 'Allowed' : 'Turned off'} {when(c.updated_at)}</p>}</div>
          <button role="switch" aria-checked={c.granted} aria-label={c.label} className={'switch' + (c.granted ? ' on' : '')} onClick={() => toggle(key, !c.granted)}><span /></button>
        </li>))}</ul>
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  )
}
