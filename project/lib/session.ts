// Signed session cookie for the single principal. Uses Web Crypto so it works in the proxy and in server code.
// Token = "<expiry ms>.<hex HMAC-SHA256 of expiry>". Needs SESSION_SECRET (16+ characters) in the Next server env.

export const SESSION_COOKIE = 'ea_session'
export const SESSION_MAX_AGE = 60 * 60 * 24 * 7 // seconds

async function sign(payload: string): Promise<string> {
  const secret = process.env.SESSION_SECRET ?? ''
  if (secret.length < 16) throw new Error('SESSION_SECRET is not set (16+ characters required).')
  const key = await crypto.subtle.importKey('raw', new TextEncoder().encode(secret), { name: 'HMAC', hash: 'SHA-256' }, false, ['sign'])
  const sig = await crypto.subtle.sign('HMAC', key, new TextEncoder().encode(payload))
  return Array.from(new Uint8Array(sig), (b) => b.toString(16).padStart(2, '0')).join('')
}

// Compares without bailing out at the first different character.
export function safeEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let diff = 0
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i)
  return diff === 0
}

export async function makeToken(): Promise<string> {
  const payload = String(Date.now() + SESSION_MAX_AGE * 1000)
  return `${payload}.${await sign(payload)}`
}

export async function verifyToken(token: string | undefined): Promise<boolean> {
  if (!token) return false
  const [payload, sig] = token.split('.')
  if (!payload || !sig || !(Number(payload) > Date.now())) return false
  try {
    return safeEqual(sig, await sign(payload))
  } catch {
    return false // no secret configured: nobody gets in
  }
}
