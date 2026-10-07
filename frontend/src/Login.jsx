import { useEffect, useState } from 'react'
import { api } from './api.js'
import { Busy } from './ui.jsx'

export default function Login({ onSignedIn }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ login: '', password: '', name: '', pin: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [demo, setDemo] = useState([])
  useEffect(() => { api('/auth/demo').then(setDemo).catch(() => {}) }, [])
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  async function signIn(body, path = '/auth/login') {
    setError(''); setBusy(true)
    try { onSignedIn(await api(path, { method: 'POST', body })) } catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  const submit = (e) => {
    e.preventDefault()
    if (mode === 'login') signIn({ login: form.login, password: form.password })
    else signIn({ name: form.name, phone: form.login, password: form.password, pin: form.pin }, '/auth/register')
  }

  return (
    <main className="login">
      <section className="login-brand">
        <img src="/logo.jpg" alt="" />
        <h1>সুরক্ষা Wallet</h1>
        <p>A little context. A smarter guard.</p>
        <ul className="promise">
          <li>Checks every transfer before your money moves</li>
          <li>Tells you in plain words when something looks wrong</li>
          <li>Holds risky transfers until a person reviews them</li>
        </ul>
      </section>
      <div className="login-side">
        <form className="login-form" onSubmit={submit}>
          <h2>{mode === 'login' ? 'Sign in' : 'Open a wallet'}</h2>
          {mode === 'register' && <label>Full name<input value={form.name} onChange={set('name')} required minLength={2} autoComplete="name" /></label>}
          <label>Mobile number
            <input value={form.login} onChange={set('login')} required autoComplete="username" placeholder="01XXXXXXXXX" />
            {mode === 'login' && <small>Staff: use your username.</small>}</label>
          <label>Password
            <input type="password" value={form.password} onChange={set('password')} required minLength={mode === 'register' ? 8 : 1}
              autoComplete={mode === 'login' ? 'current-password' : 'new-password'} />
            {mode === 'register' && <small>At least 8 characters, with a letter and a number.</small>}</label>
          {mode === 'register' && <label>Wallet PIN<input type="password" inputMode="numeric" pattern="\d{4,6}" value={form.pin} onChange={set('pin')} required />
            <small>4 to 6 digits. You enter it to confirm every transfer.</small></label>}
          {error && <p className="error" role="alert">{error}</p>}
          <button className="primary" disabled={busy}><Busy on={busy}>{mode === 'login' ? 'Sign in' : 'Open wallet'}</Busy></button>
          <button type="button" className="link" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError('') }}>
            {mode === 'login' ? 'New here? Open a wallet' : 'Already have a wallet? Sign in'}</button>
        </form>
        {mode === 'login' && demo.length > 0 && <section className="demo-accounts">
          <h3>Try a demo account</h3>
          <p>One tap signs you in. Wallet PIN for every demo customer: 2468.</p>
          <div>{demo.map((d) => <button key={d.login} disabled={busy} className={d.role} onClick={() => signIn({ login: d.login, password: d.password })}>
            <strong>{d.name}</strong><span>{d.role === 'analyst' ? 'Reviews held transfers' : d.login}</span></button>)}</div>
        </section>}
        <p className="fine">Preview with virtual money. No real payments are made.</p>
      </div>
    </main>
  )
}
