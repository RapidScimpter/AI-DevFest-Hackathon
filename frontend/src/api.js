// Small fetch wrapper. The session lives in an httpOnly cookie; the device identifier is
// only attached when the customer has granted the device permission.
let shareDevice = false
export const setShareDevice = (value) => { shareDevice = value }

function deviceId() {
  try {
    let id = localStorage.getItem('surokkha-device')
    if (!id) { id = 'web-' + crypto.randomUUID(); localStorage.setItem('surokkha-device', id) }
    return id
  } catch { return null }
}

export async function api(path, { method = 'GET', body } = {}) {
  const headers = {}
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  const id = shareDevice && deviceId()
  if (id) headers['X-Device-Id'] = id
  const res = await fetch('/api' + path, { method, headers, credentials: 'same-origin', body: body === undefined ? undefined : JSON.stringify(body) })
  const data = res.headers.get('content-type')?.includes('json') ? await res.json() : null
  if (!res.ok) {
    const detail = data?.detail
    const error = new Error(Array.isArray(detail) ? detail.map((d) => d.msg).join('. ') : detail || 'Something went wrong. Try again.')
    error.status = res.status
    throw error
  }
  return data
}

export const taka = (n) => '৳' + Number(n ?? 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })
export const pct = (n, d = 0) => (n == null ? 'n/a' : (n * 100).toFixed(d) + '%')
export const when = (iso) => (iso ? new Date(iso).toLocaleString('en-GB', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) : '')
export function duration(s) {
  if (s == null) return 'n/a'
  if (s < 90) return Math.round(s) + ' sec'
  if (s < 5400) return Math.round(s / 60) + ' min'
  return (s / 3600).toFixed(1) + ' hr'
}

export function locate() {
  return new Promise((resolve) => {
    if (!navigator.geolocation) return resolve(null)
    navigator.geolocation.getCurrentPosition((p) => resolve({ latitude: p.coords.latitude, longitude: p.coords.longitude }), () => resolve(null), { timeout: 4000, maximumAge: 600000 })
  })
}
