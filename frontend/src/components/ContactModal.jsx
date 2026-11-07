import { useState } from 'react'
import Modal from './ui/Modal'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function ContactModal({ onClose }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [success, setSuccess] = useState(false)
  const [error, setError] = useState(null)

  async function handleSubmit(e) {
    e.preventDefault()
    setError(null)
    // Client-side guards (server also validates)
    if (name.trim().length < 1 || name.length > 100) return setError('Name must be 1–100 characters.')
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) return setError('Enter a valid email address.')
    if (message.trim().length < 1 || message.length > 3000) return setError('Message must be 1–3000 characters.')
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/contact`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, message }),
      })
      if (!res.ok) {
        throw new Error(res.status === 429
          ? "You've sent several messages today. Please try again tomorrow."
          : res.status === 422 || res.status === 400
            ? 'Please check your name, email and message, then try again.'
            : 'Something went wrong. Please try again.')
      }
      setSuccess(true)
      setTimeout(() => onClose(), 2000)
    } catch (err) {
      setError(err instanceof TypeError ? "Can't reach our server. Check your connection." : (err.message || 'Something went wrong. Please try again.'))
    } finally {
      setLoading(false)
    }
  }

  const inputStyle = {
    width: '100%',
    background: '#1a1a1a',
    border: '1px solid #2a2a2a',
    borderRadius: '8px',
    padding: '12px 14px',
    fontSize: '14px',
    color: '#fff',
    fontFamily: 'inherit',
    boxSizing: 'border-box',
    transition: 'border-color 0.15s',
  }

  const labelStyle = {
    fontSize: '12px',
    color: 'var(--text-muted)',
    fontWeight: 600,
    letterSpacing: '0.06em',
    textTransform: 'uppercase',
    marginBottom: '6px',
    display: 'block',
  }

  return (
    <Modal title="Get in touch" onClose={onClose} maxWidth="640px" zIndex={200} padded>
        <p style={{ margin: '0 0 24px', fontSize: '14px', color: 'var(--text-body)', lineHeight: 1.5 }}>
          Have questions or feedback? We'll get back to you shortly.
        </p>

        {success ? (
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              gap: '16px',
              padding: '32px 0',
              textAlign: 'center',
            }}
          >
            <div style={{ fontSize: '48px', lineHeight: 1 }}>✅</div>
            <div style={{ fontSize: '16px', fontWeight: 600, color: '#fff' }}>
              Message sent!
            </div>
            <div style={{ fontSize: '14px', color: 'var(--text-body)' }}>
              We'll be in touch soon.
            </div>
          </div>
        ) : (
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div>
              <label htmlFor="contact-name" style={labelStyle}>Name</label>
              <input
                id="contact-name"
                type="text"
                required
                maxLength={100}
                value={name}
                onChange={e => setName(e.target.value)}
                placeholder="Your name"
                style={inputStyle}
                onFocus={e => (e.currentTarget.style.borderColor = '#e63946')}
                onBlur={e => (e.currentTarget.style.borderColor = '#2a2a2a')}
              />
            </div>

            <div>
              <label htmlFor="contact-email" style={labelStyle}>Email</label>
              <input
                id="contact-email"
                type="email"
                required
                maxLength={200}
                value={email}
                onChange={e => setEmail(e.target.value)}
                placeholder="you@example.com"
                style={inputStyle}
                onFocus={e => (e.currentTarget.style.borderColor = '#e63946')}
                onBlur={e => (e.currentTarget.style.borderColor = '#2a2a2a')}
              />
            </div>

            <div>
              <label htmlFor="contact-message" style={labelStyle}>Message</label>
              <textarea
                id="contact-message"
                required
                maxLength={3000}
                value={message}
                onChange={e => setMessage(e.target.value)}
                placeholder="How can we help?"
                rows={5}
                style={{ ...inputStyle, resize: 'vertical', minHeight: '120px' }}
                onFocus={e => (e.currentTarget.style.borderColor = '#e63946')}
                onBlur={e => (e.currentTarget.style.borderColor = '#2a2a2a')}
              />
            </div>

            {error && (
              <div
                role="alert"
                style={{
                  background: 'rgba(230,57,70,0.08)',
                  border: '1px solid rgba(230,57,70,0.3)',
                  borderRadius: '8px',
                  padding: '12px 16px',
                  fontSize: '13px',
                  color: '#e63946',
                }}
              >
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              style={{
                background: loading ? '#6b1c22' : '#e63946',
                border: 'none',
                borderRadius: '10px',
                padding: '14px',
                fontSize: '14px',
                fontWeight: 700,
                color: '#fff',
                cursor: loading ? 'not-allowed' : 'pointer',
                fontFamily: 'inherit',
                letterSpacing: '0.02em',
                transition: 'opacity 0.15s',
              }}
              onMouseEnter={e => { if (!loading) e.currentTarget.style.opacity = '0.85' }}
              onMouseLeave={e => (e.currentTarget.style.opacity = '1')}
            >
              {loading ? 'Sending…' : 'Send Message'}
            </button>
          </form>
        )}
    </Modal>
  )
}
