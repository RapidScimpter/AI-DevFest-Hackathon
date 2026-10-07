import { useCallback, useEffect, useState } from 'react'
import { api, duration, pct, taka, when } from './api.js'
import Meter from './Meter.jsx'
import { Icon, useCountUp } from './ui.jsx'

const PAGES = [['overview', 'Overview'], ['queue', 'Review queue'], ['model', 'Model quality'], ['drift', 'Changing scam methods'], ['audit', 'Audit log'], ['customers', 'Customers']]
const LABEL = (s) => s.replaceAll('_', ' ')
// Plain names for the model's inputs.
const INPUTS = {
  amount_ratio: 'Amount compared with their usual', log_amount_z: 'How unusual the amount is', balance_drain_ratio: 'Share of balance being sent',
  amount_trend: 'Amount compared with last three', new_device: 'Unknown device (1 = yes)', device_age: 'Times this device was used before',
  new_recipient: 'New recipient (1 = yes)', recipient_count: 'Times they paid this recipient before', location_change: 'Unusual location (1 = yes)',
  unusual_hour: 'Unusual time of day (1 = yes)', hour_rarity: 'Share of past activity near this hour', failed_pin_attempts: 'Wrong PIN tries just now',
  recent_failed_pins: 'Wrong PIN tries recently', transactions_1min: 'Transfers in the last minute', transactions_10min: 'Transfers in the last 10 minutes',
  transactions_60min: 'Transfers in the last hour', amount_60min_ratio: 'Money moved in the last hour, compared with usual', new_recipients_60min: 'New recipients in the last hour',
  small_run: 'Payments in a row to new recipients', gap_ratio: 'Time since last transfer, compared with usual', is_cash_out: 'Cash out (1 = yes)',
  seq_nll: 'How unusual the order of recent actions is',
}
const INPUT = (k) => INPUTS[k] || LABEL(k)

function useData(path) {
  const [data, setData] = useState(null); const [error, setError] = useState('')
  const load = useCallback(() => api(path).then(setData).catch((e) => setError(e.message)), [path])
  useEffect(() => { load() }, [load])
  return [data, load, error]
}

export default function Analyst({ user, onSignOut }) {
  const [page, setPage] = useState('overview')
  const [waiting, setWaiting] = useState(0)
  useEffect(() => { api('/analyst/overview').then((o) => setWaiting(o.queue.waiting)).catch(() => {}) }, [page])
  const View = { overview: Overview, queue: Queue, model: Model, drift: Drift, audit: Audit, customers: Customers }[page]
  return (
    <div className="desk">
      <aside>
        <div className="who"><img src="/logo.jpg" alt="" /><div><strong>সুরক্ষা Wallet</strong><span>{user.name}, {user.role}</span></div></div>
        <nav aria-label="Sections">{PAGES.map(([id, label]) => <button key={id} className={page === id ? 'on' : ''} onClick={() => setPage(id)}><Icon name={id === "queue" ? "held" : id === "audit" ? "lock" : "safe"} size={19}/>{label}{id === 'queue' && waiting > 0 && <b className="badge">{waiting}</b>}</button>)}</nav>
        <button className="ghost" onClick={onSignOut}>Sign out</button>
      </aside>
      <main key={page}><View onChange={() => api('/analyst/overview').then((o) => setWaiting(o.queue.waiting)).catch(() => {})} /></main>
    </div>
  )
}

const Stat = ({ label, value, hint }) => <div className="stat"><p>{label}</p><strong>{value}</strong>{hint && <span>{hint}</span>}</div>
const State = ({ data, error }) => (error ? <p className="error" role="alert">{error}</p> : !data ? <p className="loading">Loading…</p> : null)

function Overview() {
  const [o, , error] = useData('/analyst/overview')
  if (!o) return <State data={o} error={error} />
  return <OverviewBody o={o} />
}

function OverviewBody({ o }) {
  const p = o.prevented_value, r = o.review_time
  const total = useCountUp(p.total, 900)
  return (
    <>
      <h1>Overview</h1>
      <p className="lede">How much risky money was stopped, and how quickly held transfers get a decision.</p>
      <section className="lead">
        <p>Value of flagged transfers stopped</p>
        <strong>{taka(Math.round(total))}</strong>
        <span>{taka(p.stopped_by_analyst)} stopped by reviewers in {p.analyst_cases} case{p.analyst_cases === 1 ? '' : 's'}; {taka(p.cancelled_by_customer_after_warning)} cancelled by customers after a warning in {p.customer_cases}. Virtual money.</span>
      </section>
      <div className="stats">
        <Stat label="Median review time" value={duration(r.median_seconds)} hint={r.decisions ? `Mean ${duration(r.mean_seconds)}, 90th percentile ${duration(r.p90_seconds)}, ${r.decisions} decision${r.decisions === 1 ? '' : 's'}` : 'No decisions recorded yet'} />
        <Stat label="Waiting for review" value={o.queue.waiting} hint={o.queue.waiting ? `${taka(o.queue.value_on_hold)} on hold, oldest waiting ${duration(o.queue.oldest_waiting_seconds)}` : 'Queue is clear'} />
        <Stat label="Transfers flagged" value={`${o.flagged} of ${o.transfers}`} hint={`Review at ${pct(o.thresholds.review)} probability, high at ${pct(o.thresholds.high)}`} />
        <Stat label="Review outcomes" value={`${o.alert_outcomes.stopped} stopped`} hint={`${o.alert_outcomes.approved_as_legitimate} approved as legitimate, ${o.alert_outcomes.confirmed_fraud} confirmed fraud`} />
      </div>
    </>
  )
}

function Queue({ onChange }) {
  const [status, setStatus] = useState('Under review')
  const [rows, load, error] = useData('/analyst/transfers' + (status ? '?status=' + encodeURIComponent(status) : ''))
  const [open, setOpen] = useState(null)
  const current = rows?.find((t) => t.id === open)
  return (
    <>
      <h1>Review queue</h1>
      <p className="lede">Transfers the wallet held because they looked risky. Pick one, read why it was held, then stop it or approve it.</p>
      <label className="inline">Show<select value={status} onChange={(e) => { setStatus(e.target.value); setOpen(null) }}>
        <option>Under review</option><option>Awaiting confirmation</option><option>Completed</option><option>Cancelled</option><option value="">All transfers</option></select></label>
      <State data={rows} error={error} />
      {rows && rows.length === 0 && <p className="empty">Nothing here. Transfers appear when a customer confirms a flagged request.</p>}
      <div className="split-view">
        <ul className="cases">{rows?.map((t) => (
          <li key={t.id}><button className={open === t.id ? 'on' : ''} onClick={() => setOpen(t.id)}>
            <strong>{taka(t.amount)}</strong><span className={'risk ' + t.review.level}>{t.review.probability == null ? 'no score' : pct(t.review.probability)}</span>
            <span>{t.customer.name}</span><span>{t.type} to {t.recipient}, {when(t.created_at)}</span></button></li>))}</ul>
        {current ? <Case t={current} reload={() => { load(); onChange?.() }} /> : rows?.length > 0 && <p className="empty case">Choose a transfer on the left to see why it was held.</p>}
      </div>
    </>
  )
}

function Case({ t, reload }) {
  const [note, setNote] = useState(''); const [fraud, setFraud] = useState(true); const [error, setError] = useState('')
  useEffect(() => { setNote(''); setError('') }, [t.id])
  const a = t.analysis, f = a.features || {}
  async function decide(action) {
    setError('')
    try { await api(`/analyst/transfers/${t.id}/decision`, { method: 'POST', body: { action, note, confirmed_fraud: action === 'reject' && fraud } }); reload() }
    catch (err) { setError(err.message) }
  }
  return (
    <section className="case">
      <h2>{taka(t.amount)} {t.type.toLowerCase()} to {t.recipient}</h2>
      <p>{t.customer.name} ({t.customer.login}, {t.customer.segment || 'new customer'}). Status: {t.status}. {t.response}</p>
      <Meter review={t.review} staff />
      {a.pattern && <p>Most resembles <strong>{a.pattern.name}</strong> ({pct(a.pattern.share)} of the known-pattern model).</p>}
      <h3>Why it was held</h3>
      <ul className="reasons strong">{t.review.follow_up.map((r) => <li key={r}>{r}</li>)}</ul>
      <ul className="reasons">{(a.signals || []).map((r) => <li key={r}>{r}</li>)}</ul>
      {t.evidence.photo_check && <p>Customer added a live photo at {when(t.evidence.photo_check.at)}. No face matching is performed.</p>}
      <details><summary>All the numbers the model looked at</summary>
        <table><tbody>{Object.entries(f).map(([k, v]) => <tr key={k}><th scope="row">{INPUT(k)}</th><td>{v}</td></tr>)}</tbody></table></details>
      {t.status === 'Under review' ? <>
        <label>Your notes (required)<textarea rows="3" value={note} onChange={(e) => setNote(e.target.value)} placeholder="What you checked and why you decided" /></label>
        <label className="check"><input type="checkbox" checked={fraud} onChange={(e) => setFraud(e.target.checked)} />If stopping, record as confirmed fraud</label>
        {error && <p className="error" role="alert">{error}</p>}
        <div className="row"><button className="primary danger" onClick={() => decide('reject')}>Stop transfer</button>
          <button className="primary" onClick={() => decide('approve')}>Approve transfer</button></div>
      </> : t.note && <p className="note">Decision note: {t.note} ({LABEL(t.outcome)})</p>}
    </section>
  )
}

const Bar = ({ value, max = 1, tone = '' }) => <span className={'bar ' + tone}><i style={{ width: Math.max(1, (value / max) * 100) + '%' }} /></span>

function Model() {
  const [m, , error] = useData('/analyst/model')
  if (!m) return <State data={m} error={error} />
  const f = m.fraud, c = f.calibration, n = m.messages, rf = f.baselines.random_forest, rule = f.baselines.rule
  return (
    <>
      <h1>Model quality</h1>
      <p className="lede">How well the fraud model works. {f.model}. Measured on {f.events.test.toLocaleString()} held-out synthetic events ({f.events.test_fraud.toLocaleString()} fraud) from customers the model never saw. These are not real-world accuracy figures.</p>
      <h2>Can the probability be trusted?</h2>
      <p>When the model says "40%", about 40 in 100 such transfers should really be fraud. The two bars in each row should be the same length. Expected calibration error: {(c.ece_calibrated * 100).toFixed(3)} points; Brier score {c.brier_calibrated.toFixed(4)}.</p>
      <table className="grid"><thead><tr><th>Predicted band</th><th>Events</th><th>Mean predicted</th><th>Observed fraud rate</th></tr></thead>
        <tbody>{c.reliability.map((r) => <tr key={r.bin}><th scope="row">{r.bin}</th><td>{r.events.toLocaleString()}</td>
          <td><Bar value={r.mean_predicted} />{pct(r.mean_predicted, 1)}</td><td><Bar value={r.observed_fraud_rate} tone="alt" />{pct(r.observed_fraud_rate, 1)}</td></tr>)}</tbody></table>
      <h2>Against the earlier approaches</h2>
      <table className="grid"><thead><tr><th>Approach</th><th>Precision</th><th>Fraud caught</th><th>False alerts</th><th>Average precision</th></tr></thead>
        <tbody>
          <tr><th scope="row">LightGBM, calibrated</th><td>{pct(f.review.precision, 1)}</td><td>{pct(f.review.recall, 1)}</td><td>{pct(f.review.false_positive_rate, 2)}</td><td>{f.average_precision.toFixed(3)}</td></tr>
          <tr><th scope="row">Random Forest</th><td>{pct(rf.precision, 1)}</td><td>{pct(rf.recall, 1)}</td><td>{pct(rf.false_positive_rate, 2)}</td><td>{rf.average_precision.toFixed(3)}</td></tr>
          <tr><th scope="row">Rule: new device and 3x amount</th><td>{pct(rule.precision, 1)}</td><td>{pct(rule.recall, 1)}</td><td>{pct(rule.false_positive_rate, 2)}</td><td>n/a</td></tr>
        </tbody></table>
      <h2>Fraud caught, by attack pattern</h2>
      <table className="grid"><tbody>{Object.entries(f.recall_by_attack).map(([k, v]) =>
        <tr key={k}><th scope="row">{LABEL(k)}</th><td>{v.events} events</td><td><Bar value={v.recall} />{pct(v.recall)}</td></tr>)}</tbody></table>
      <p>Social-engineering fraud is the weak spot: the customer sends the money themselves from their own device, so behaviour looks normal. Number reports and message screening are the main defence there.</p>
      <h2>False alerts, by customer type</h2>
      <table className="grid"><tbody>{Object.entries(f.false_positive_rate_by_segment).map(([k, v]) =>
        <tr key={k}><th scope="row">{k}</th><td><Bar value={v} max={0.005} tone="alt" />{pct(v, 2)}</td></tr>)}</tbody></table>
      <h2>Behavioural sequence signal</h2>
      <p>The sequence feature scores how unusual the order of recent actions is. Average precision with it: {f.sequence_ablation.average_precision_with_seq_nll.toFixed(4)}; without it: {f.sequence_ablation.average_precision_without_seq_nll.toFixed(4)}.</p>
      <h2>Scam message model</h2>
      <p className="lede">{n.model}. Tested on {n.test_messages.toLocaleString()} synthetic messages built from {n.held_out_bodies} phrasings that were kept out of training.</p>
      <table className="grid"><thead><tr><th>Language</th><th>Messages</th><th>Precision</th><th>Scams caught</th><th>False alerts</th></tr></thead>
        <tbody>{[['All', n.overall], ['English', n.by_language.en], ['Bangla', n.by_language.bn], ['Romanised Bangla', n.by_language.bl]].map(([k, v]) =>
          <tr key={k}><th scope="row">{k}</th><td>{v.messages}</td><td>{pct(v.precision, 1)}</td><td>{pct(v.recall, 1)}</td><td>{pct(v.false_positive_rate, 1)}</td></tr>)}</tbody></table>
    </>
  )
}

function PsiTable({ block, title }) {
  return (
    <>
      <h2>{title}</h2>
      {block.status === 'not enough data'
        ? <p className="empty">{block.events} scored so far; at least {block.minimum} are needed before this comparison is meaningful.</p>
        : <><p>Overall: <strong>{block.status}</strong> (mean PSI {block.mean_psi}, {block.events} events).</p>
          <table className="grid"><tbody>{block.features.map((x) => <tr key={x.feature}><th scope="row">{INPUT(x.feature)}</th><td><Bar value={Math.min(x.psi, 1)} tone={x.psi >= 0.25 ? 'bad' : ''} />{x.psi}</td><td>{x.status}</td></tr>)}</tbody></table></>}
    </>
  )
}

function Drift() {
  const [d, , error] = useData('/analyst/drift')
  if (!d) return <State data={d} error={error} />
  const s = d.simulation
  return (
    <>
      <h1>Changing scam methods</h1>
      <p className="lede">Scammers change tactics. This page compares recent activity with what the model learned from, and warns when they stop matching.</p>
      <p>{d.guide}</p>
      <PsiTable block={d.population} title="All recent transfers against training data" />
      <PsiTable block={d.confirmed_fraud} title="Confirmed fraud against known fraud patterns" />
      <h2>Confirmed fraud the model scored low</h2>
      <p>{d.missed_by_model.confirmed_fraud === 0 ? 'No confirmed fraud recorded yet.' : `${d.missed_by_model.scored_below_threshold} of ${d.missed_by_model.confirmed_fraud} (${pct(d.missed_by_model.share)}).`}</p>
      <h2>Offline test with a new scam method</h2>
      <p>{s.scenario} The model was never trained on it ({s.events.toLocaleString()} events).</p>
      <div className="stats">
        <Stat label="Caught, known methods" value={pct(s.recall_known_patterns)} />
        <Stat label="Caught, new method" value={pct(s.recall_unseen_pattern)} hint="The model misses most of it, as expected" />
        <Stat label="Shift score, known fraud" value={s.mean_feature_psi_known.toFixed(2)} hint="Stable" />
        <Stat label="Shift score, new method" value={s.mean_feature_psi_unseen.toFixed(2)} hint="Major shift: the monitor raises the alarm" />
      </div>
      <table className="grid"><thead><tr><th>Most shifted inputs</th><th>PSI</th></tr></thead>
        <tbody>{Object.entries(s.top_shifted_features).map(([k, v]) => <tr key={k}><th scope="row">{INPUT(k)}</th><td>{v.toFixed(2)}</td></tr>)}</tbody></table>
    </>
  )
}

function Audit() {
  const [filter, setFilter] = useState('')
  const [log, , error] = useData('/analyst/audit' + (filter ? '?action=' + filter : ''))
  return (
    <>
      <h1>Audit log</h1>
      <p className="lede">Every sign-in, transfer, decision and permission change. Each entry is locked to the one before it, so edits or deletions are detected.</p>
      {log && <p className={log.chain.intact ? 'ok' : 'error'} role="status">{log.chain.intact
        ? `Record chain intact: ${log.chain.entries_checked.toLocaleString()} entries verified.`
        : `Record chain broken at entry ${log.chain.first_broken_id}. An entry was altered or removed.`}</p>}
      <label className="inline">Show<select value={filter} onChange={(e) => setFilter(e.target.value)}>
        <option value="">Everything</option><option value="auth">Sign-ins</option><option value="transfer">Transfers</option><option value="consent">Permissions</option>
        <option value="pin">Failed PINs</option><option value="device">Devices</option><option value="report">Reports</option><option value="admin">Admin</option></select></label>
      <State data={log} error={error} />
      {log && <div className="scroll"><table className="grid audit"><thead><tr><th>Time</th><th>Who</th><th>Action</th><th>On</th><th>Details</th><th>Hash</th></tr></thead>
        <tbody>{log.entries.map((e) => <tr key={e.id}><td>{when(e.ts)}</td><td>{e.actor} {e.role && `(${e.role})`}</td><td>{e.action}</td><td>{e.entity} {e.entity_id}</td>
          <td>{Object.entries(e.detail).map(([k, v]) => `${k}: ${Array.isArray(v) ? v.join(', ') || 'none' : v}`).join('; ')}</td><td><code>{e.hash}</code></td></tr>)}</tbody></table></div>}
    </>
  )
}

function Customers() {
  const [rows, , error] = useData('/analyst/customers')
  if (!rows) return <State data={rows} error={error} />
  return (
    <>
      <h1>Customers</h1>
      <p className="lede">Every wallet, its balance, and which permissions the customer has allowed.</p>
      <div className="scroll"><table className="grid"><thead><tr><th>Name</th><th>Number</th><th>Type</th><th>Balance</th><th>Reserved</th><th>Permissions granted</th></tr></thead>
        <tbody>{rows.map((c) => <tr key={c.id}><th scope="row">{c.name}</th><td>{c.login}</td><td>{c.segment || 'new'}</td><td>{taka(c.balance)}</td><td>{taka(c.reserved)}</td>
          <td>{Object.entries(c.consents).filter(([, v]) => v).map(([k]) => k).join(', ') || 'none'}</td></tr>)}</tbody></table></div>
    </>
  )
}
