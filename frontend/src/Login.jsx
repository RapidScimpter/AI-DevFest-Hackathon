import { useState } from 'react'
import { api } from './api.js'
import { Busy, Icon } from './ui.jsx'

export default function Login({ onSignedIn }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ login: '', password: '', name: '', pin: '' })
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const set = (key) => (event) => setForm({ ...form, [key]: event.target.value })
  async function submit(event) {
    event.preventDefault(); setError(''); setBusy(true)
    const body = mode === 'login' ? { login: form.login, password: form.password } : { name: form.name, phone: form.login, password: form.password, pin: form.pin }
    try { onSignedIn(await api(mode === 'login' ? '/auth/login' : '/auth/register', { method: 'POST', body })) }
    catch (err) { setError(err.message) } finally { setBusy(false) }
  }
  return <main className="login">
    <section className="login-brand">
      <div className="brand-lockup"><img src="/logo.jpg" alt="সুরক্ষা Wallet logo"/><span>সুরক্ষা Wallet</span></div>
      <span className="eyebrow bangla" lang="bn">আপনার অর্থ, আপনার নিয়ন্ত্রণে</span>
      <h1>A little more<br/>peace of mind.</h1>
      <p className="brand-tagline" lang="bn">নিশ্চিন্তে লেনদেন, সচেতন প্রতিটি পদক্ষেপে।</p>
      <p className="brand-description">Understand concerns before you pay. Stay in control when something feels unusual.</p>
      <ul className="promise">
        <li><Icon name="safe" size={23}/><div><strong>Check before you send</strong><span>Clear concerns before you confirm a transfer.</span></div></li>
        <li><Icon name="phone" size={23}/><div><strong>Know who is contacting you</strong><span>Check a caller or message, and report concerns.</span></div></li>
        <li><Icon name="held" size={23}/><div><strong>Pause when it matters</strong><span>Requests needing investigation stay under review.</span></div></li>
      </ul>
      <div className="brand-signoff"><Icon name="lock" size={18}/><span lang="bn">একটু সচেতনতা, আরও সুরক্ষা।</span></div>
    </section>
    <section className="login-side">
      <div className="login-heading"><span className="eyebrow" lang="bn">স্বাগতম</span><h2>{mode === 'login' ? 'Welcome back' : 'Your wallet starts here'}</h2><p>{mode === 'login' ? 'Sign in to continue to your wallet.' : 'Create your account in a few simple steps.'}</p></div>
      <form className="login-form" onSubmit={submit}>
        {mode === 'register' && <label>Full name<input value={form.name} onChange={set('name')} required minLength={2} autoComplete="name" placeholder="Your full name"/></label>}
        <label>Mobile number or username<input value={form.login} onChange={set('login')} required autoComplete="username" placeholder="01XXXXXXXXX" autoCapitalize="none" spellCheck={false}/></label>
        <label>Password<div className="password-field"><input type={showPassword ? 'text' : 'password'} value={form.password} onChange={set('password')} required minLength={mode === 'register' ? 8 : 1} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} placeholder="Enter your password"/><button type="button" className="password-toggle" aria-label={showPassword ? 'Hide password' : 'Show password'} aria-pressed={showPassword} onClick={() => setShowPassword(!showPassword)}><Icon name="eye" size={20}/></button></div>{mode === 'register' && <small>At least 8 characters, including a letter and a number.</small>}</label>
        {mode === 'register' && <label>Wallet PIN<input type="password" inputMode="numeric" pattern="\d{4,6}" value={form.pin} onChange={set('pin')} required autoComplete="new-password" placeholder="Choose 4–6 digits"/><small>Use your PIN to confirm transfers.</small></label>}
        {error && <p className="error" role="alert">{error}</p>}
        <button className="primary login-submit" disabled={busy}><Busy on={busy}>{mode === 'login' ? 'Sign in' : 'Create wallet'}<Icon name="arrow" size={20}/></Busy></button>
        <p className="account-switch">{mode === 'login' ? 'New to সুরক্ষা Wallet?' : 'Already have an account?'} <button type="button" className="link" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setError(''); setShowPassword(false) }}>{mode === 'login' ? 'Create an account' : 'Sign in'}</button></p>
      </form>
      <div className="login-footer"><Icon name="lock" size={17}/><span>Account access is protected. This version uses virtual money.</span></div>
    </section>
  </main>
}
