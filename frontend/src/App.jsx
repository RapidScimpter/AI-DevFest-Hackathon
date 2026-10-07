import { useEffect, useState } from 'react'
import { api } from './api.js'
import Login from './Login.jsx'
import Customer from './Customer.jsx'
import Analyst from './Analyst.jsx'

export default function App() {
  const [user, setUser] = useState(undefined)
  useEffect(() => { api('/auth/me').then(setUser).catch(() => setUser(null)) }, [])
  const signOut = async () => { await api('/auth/logout', { method: 'POST' }).catch(() => {}); setUser(null) }

  if (user === undefined) return <p className="loading">Loading…</p>
  if (!user) return <Login onSignedIn={setUser} />
  return user.role === 'customer' ? <Customer user={user} onSignOut={signOut} /> : <Analyst user={user} onSignOut={signOut} />
}
