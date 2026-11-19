import { cookies } from 'next/headers'
import { NextResponse, type NextRequest } from 'next/server'
import { callApi } from '@/lib/api'
import { SESSION_COOKIE, verifyToken } from '@/lib/session'

// The browser can't call the agent API directly (it needs the API key), so Next asks for the Google
// consent URL on the browser's behalf and redirects there. Only a signed-in principal can do this.
export async function GET(request: NextRequest) {
  const settings = new URL('/settings', request.url)
  if (!(await verifyToken((await cookies()).get(SESSION_COOKIE)?.value))) {
    return NextResponse.redirect(new URL('/login', request.url))
  }
  const { data, error } = await callApi<{ url: string }>('/oauth/google/start')
  if (!data) {
    settings.searchParams.set('google_error', error ?? 'could not start')
    return NextResponse.redirect(settings)
  }
  return NextResponse.redirect(data.url)
}
