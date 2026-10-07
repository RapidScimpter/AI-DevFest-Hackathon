import { useEffect, useRef, useState } from 'react'

const still = () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches

// Counts from the previous value to the new one, so a changed balance is seen changing.
export function useCountUp(target, ms = 700) {
  const [value, setValue] = useState(target ?? 0)
  const from = useRef(target ?? 0)
  useEffect(() => {
    if (target == null) return
    if (still()) { setValue(target); from.current = target; return }
    const start = performance.now(), a = from.current
    let frame
    const tick = (now) => {
      const t = Math.min(1, (now - start) / ms), eased = 1 - Math.pow(1 - t, 3)
      setValue(a + (target - a) * eased)
      if (t < 1) frame = requestAnimationFrame(tick); else from.current = target
    }
    frame = requestAnimationFrame(tick)
    return () => cancelAnimationFrame(frame)
  }, [target, ms])
  return value
}

const PATHS = {
  safe: <><path d="M12 3l7 3v5c0 4.6-3 8.3-7 10-4-1.700-7-5.400-7-10V6l7-3z" /><path className="draw" d="M8.500 12l2.500 2.500 4.500-5" /></>,
  caution: <><path d="M12 4l9 16H3L12 4z" /><path className="draw" d="M12 10v4.500M12 17.300v.2" /></>,
  danger: <><path d="M8.200 3h7.600L21 8.200v7.600L15.800 21H8.200L3 15.800V8.200L8.200 3z" /><path className="draw" d="M9 9l6 6M15 9l-6 6" /></>,
  done: <><circle cx="12" cy="12" r="9" /><path className="draw" d="M7.500 12.300l3 3 6-6.500" /></>,
  held: <><circle cx="12" cy="12" r="9" /><path className="draw" d="M12 7v5.200l3.200 2" /></>,
  stopped: <><circle cx="12" cy="12" r="9" /><path className="draw" d="M8 12h8" /></>,
}
export const Icon = ({ name, size = 28 }) => (
  <svg className={'icon ' + name} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{PATHS[name]}</svg>
)

export const Steps = ({ labels, current }) => (
  <ol className="steps" aria-label="Progress">{labels.map((l, i) => (
    <li key={l} className={i < current ? 'past' : i === current ? 'now' : ''} aria-current={i === current ? 'step' : undefined}><span>{i + 1}</span>{l}</li>))}</ol>
)

export const Busy = ({ on, children }) => (on ? <><span className="spinner" aria-hidden="true" />Working…</> : children)
