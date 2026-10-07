import { useEffect, useState } from 'react'
import { pct } from './api.js'
import { Icon } from './ui.jsx'

const HEADLINE = {
  safe: ['This looks normal for you', 'Nothing unusual was found. Check the details, then confirm.'],
  caution: ['Take a moment to check', 'Something is a little different from your usual payments.'],
  danger: ['Stop and check: this looks risky', 'Several warning signs match how fraud usually happens.'],
}

// The verdict in plain words, then a safe-to-dangerous scale whose marker slides to the estimated risk.
export default function Meter({ review, staff = false }) {
  const p = review.probability
  const target = p == null ? { safe: 12, caution: 50, danger: 88 }[review.level] : Math.min(96, Math.max(4, Math.sqrt(p) * 100))
  const [left, setLeft] = useState(4)
  useEffect(() => { const t = setTimeout(() => setLeft(target), 60); return () => clearTimeout(t) }, [target])
  const [title, sub] = HEADLINE[review.level]
  return (
    <div className={'meter ' + review.level}>
      <div className="verdict"><Icon name={review.level} size={40} /><div><strong>{staff ? review.status : title}</strong>{!staff && <p>{sub}</p>}</div></div>
      <div className="meter-track" role="img" aria-label={`Risk level: ${title}`}><span className="meter-pin" style={{ left: left + '%' }} /></div>
      <div className="meter-scale"><span>Safe</span><span>Be careful</span><span>Dangerous</span></div>
      {p != null && <p className="meter-read">Estimated chance this is fraud: <strong>{p < 0.01 ? 'under 1%' : p > 0.99 ? 'over 99%' : pct(p)}</strong></p>}
    </div>
  )
}
