import { cookies } from 'next/headers'
import { SESSION_COOKIE, verifyToken } from '@/lib/session'

// Defence in depth: the proxy already blocks unauthenticated requests, but every server action checks again.
// Returns an error message for the UI, or null when the session is valid.
export async function authError(): Promise<string | null> {
  const ok = await verifyToken((await cookies()).get(SESSION_COOKIE)?.value)
  return ok ? null : 'Your session has expired. Sign in again.'
}
