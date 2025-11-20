import React, { createContext, useContext, useMemo, useEffect, useState } from 'react'
import { Routes, Route, Navigate, useNavigate, useLocation, Link } from 'react-router-dom'

// === Config your microservices endpoints here ===
const AUTH_BASE = 'https://auth-microservices.iqbalfadhil.biz.id'
const TEST_BASE = 'https://test-microservices.iqbalfadhil.biz.id'

// === Auth context ===
const AuthCtx = createContext(null)
const useAuth = () => useContext(AuthCtx)

function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token') || '')
  const [user, setUser] = useState(() => {
    const raw = localStorage.getItem('user')
    return raw ? JSON.parse(raw) : null
  })
  const [loading, setLoading] = useState(false)

  const login = async (username, password) => {
    setLoading(true)
    try {
      const res = await fetch(`${AUTH_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })
      if (!res.ok) throw new Error(`Login failed: ${res.status}`)
      const data = await res.json()
      if (!data.token) throw new Error('No token in response')
      localStorage.setItem('token', data.token)
      setToken(data.token)

      const me = await fetch(`${AUTH_BASE}/api/auth/me?token=${encodeURIComponent(data.token)}`)
      const meData = await me.json()
      localStorage.setItem('user', JSON.stringify(meData))
      setUser(meData)
      return true
    } finally {
      setLoading(false)
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken('')
    setUser(null)
  }

  const refreshMe = async () => {
    if (!token) return null
    const r = await fetch(`${AUTH_BASE}/api/auth/me?token=${encodeURIComponent(token)}`)
    if (r.ok) {
      const d = await r.json()
      setUser(d)
      localStorage.setItem('user', JSON.stringify(d))
      return d
    }
    return null
  }

  const value = useMemo(() => ({ token, user, loading, login, logout, refreshMe }), [token, user, loading])
  return <AuthCtx.Provider value={value}>{children}</AuthCtx.Provider>
}

// === Layout ===
function Navbar() {
  const { user, logout } = useAuth()
  const nav = useNavigate()
  const isAuthed = !!user
  return (
    <nav className="w-full border-b bg-white/80 backdrop-blur sticky top-0 z-10">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <Link to={isAuthed ? '/dashboard' : '/'} className="font-semibold text-lg">English Test Simulation</Link>
        {isAuthed && (
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-500">{user?.username || user?.email || ''}</span>
            <button className="px-3 py-1.5 rounded-xl border hover:bg-gray-50" onClick={() => { logout(); nav('/login', { replace: true }) }}>Log out</button>
          </div>
        )}
      </div>
    </nav>
  )
}

function Page({ children }) {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar />
      <main className="max-w-5xl mx-auto px-4 py-8">{children}</main>
    </div>
  )
}

// === Route guards ===
function RequireAuth({ children }) {
  const { token } = useAuth()
  const location = useLocation()
  if (!token) return <Navigate to="/login" replace state={{ from: location }} />
  return children
}

function RedirectIfAuthed({ children }) {
  const { token } = useAuth()
  if (token) return <Navigate to="/dashboard" replace />
  return children
}

// === Pages ===
function LoginPage() {
  const { login, loading } = useAuth()
  const nav = useNavigate()
  const [form, setForm] = useState({ username: '', password: '' })
  const [err, setErr] = useState('')

  const onSubmit = async (e) => {
    e.preventDefault()
    setErr('')
    try {
      const ok = await login(form.username, form.password)
      if (ok) nav('/dashboard', { replace: true })
    } catch (e) {
      setErr(e.message || 'Login failed')
    }
  }

  return (
    <Page>
      <div className="max-w-md mx-auto bg-white rounded-2xl shadow p-6">
        <h1 className="text-2xl font-semibold mb-1">Welcome back</h1>
        <p className="text-sm text-gray-500 mb-6">Sign in to start your test.</p>
        {err && <div className="mb-4 text-sm text-red-600">{err}</div>}
        <form className="space-y-4" onSubmit={onSubmit}>
          <div>
            <label className="block text-sm mb-1">Username</label>
            <input className="w-full border rounded-xl px-3 py-2" value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} required />
          </div>
          <div>
            <label className="block text-sm mb-1">Password</label>
            <input type="password" className="w-full border rounded-xl px-3 py-2" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} required />
          </div>
          <button disabled={loading} className="w-full rounded-xl bg-black text-white py-2.5 disabled:opacity-60" type="submit">
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>
      </div>
    </Page>
  )
}

function DashboardPage() {
  const { user, refreshMe } = useAuth()
  const nav = useNavigate()
  const location = useLocation()
  const [latestScore, setLatestScore] = useState(() => location.state?.score ?? null)

  useEffect(() => { refreshMe() }, [])

  return (
    <Page>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-gray-500">Hello {user?.first_name || user?.username || 'there'}!</p>
        </div>
        <button className="px-4 py-2 rounded-xl bg-black text-white" onClick={() => nav('/test')}>Start Test</button>
      </div>



        <div className="rounded-2xl border bg-white p-5">
          <div className="text-sm text-gray-500 mb-2">Profile</div>
          <div className="grid gap-4">
        {latestScore !== null && (
          <div className="rounded-2xl border bg-white p-5">
            <div className="text-sm text-gray-500 mb-1">Most recent score</div>
            <div className="text-3xl font-semibold">{latestScore}</div>
          </div>
        )}
        </div>
      </div>
    </Page>
  )
}

function TestPage() {
  const { token } = useAuth()
  const nav = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [questions, setQuestions] = useState([])
  const [index, setIndex] = useState(0)
  const [answers, setAnswers] = useState({})

  useEffect(() => {
    let cancelled = false
    ;(async () => {
      try {
        const r = await fetch(`${TEST_BASE}/questions`)
        if (!r.ok) throw new Error(`Failed to load questions: ${r.status}`)
        const data = await r.json()
        if (!cancelled) setQuestions(Array.isArray(data) ? data : data?.questions || [])
      } catch (e) {
        if (!cancelled) setError(e.message || 'Error loading questions')
      } finally {
        if (!cancelled) setLoading(false)
      }
    })()
    return () => { cancelled = true }
  }, [])

  const q = questions[index]
  const total = questions.length
  const isLast = index === total - 1

  const select = (qid, opt) => setAnswers(prev => ({ ...prev, [qid]: opt }))

  const goNext = () => {
    if (!q) return
    if (!answers[q.id]) { alert('Please select an option to continue.'); return }
    setIndex(i => Math.min(i + 1, total - 1))
  }

  const handleSubmit = async () => {
    if (q && !answers[q.id]) { alert('Please select an option for this question.'); return }
    const payload = {
      answers: Object.entries(answers).map(([question_id, selected_option]) => ({
        question_id: Number(question_id),
        selected_option,
      }))
    }
    try {
      const r = await fetch(`${TEST_BASE}/submit?token=${encodeURIComponent(token)}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      if (!r.ok) throw new Error(`Submit failed: ${r.status}`)
      const data = await r.json()
      const score = data.score ?? data.total_score ?? data.result?.score ?? 0
      nav('/dashboard', { replace: true, state: { score } })
    } catch (e) {
      alert(e.message || 'Failed to submit answers')
    }
  }

  if (loading) return <Page><div className="text-gray-500">Loading questions…</div></Page>
  if (error) return <Page><div className="text-red-600">{error}</div></Page>
  if (!questions.length) return <Page><div>No questions available.</div></Page>

  return (
    <Page>
      <div className="mb-4 flex items-center justify-between">
        <h1 className="text-xl font-semibold">Test</h1>
        <div className="text-sm text-gray-500">Question {index + 1} / {total}</div>
      </div>

      <div className="rounded-2xl border bg-white p-6">
        <div className="text-lg font-medium mb-4">{q.question_text}</div>
        <div className="space-y-2">
          {(['A','B','C','D']).map(opt => (
            <label key={opt} className={`flex items-center gap-3 p-3 rounded-xl border cursor-pointer ${answers[q.id]===opt ? 'bg-gray-50 border-gray-900' : 'hover:bg-gray-50'}`}>
              <input type="radio" name={`q_${q.id}`} checked={answers[q.id] === opt} onChange={() => select(q.id, opt)} />
              <span className="font-semibold w-6">{opt}</span>
              <span>{q[`option_${opt.toLowerCase()}`]}</span>
            </label>
          ))}
        </div>

        <div className="mt-6 flex items-center justify-between">
          <button className="px-4 py-2 rounded-xl border" onClick={() => setIndex(i => Math.max(i - 1, 0))} disabled={index === 0}>Back</button>
          {!isLast ? (
            <button className="px-4 py-2 rounded-xl bg-black text-white" onClick={goNext}>Next</button>
          ) : (
            <button className="px-4 py-2 rounded-xl bg-black text-white" onClick={handleSubmit}>Submit</button>
          )}
        </div>
      </div>
    </Page>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<RedirectIfAuthed><LoginPage /></RedirectIfAuthed>} />
        <Route path="/dashboard" element={<RequireAuth><DashboardPage /></RequireAuth>} />
        <Route path="/test" element={<RequireAuth><TestPage /></RequireAuth>} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="*" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </AuthProvider>
  )
}