import { NextResponse, type NextRequest } from 'next/server'
import { SESSION_COOKIE, verifyToken } from '@/lib/session'

// Everything except /login and static assets needs a valid session cookie (server actions are covered too).
export async function proxy(request: NextRequest) {
  if (await verifyToken(request.cookies.get(SESSION_COOKIE)?.value)) return NextResponse.next()
  const url = request.nextUrl.clone()
  url.pathname = '/login'
  url.search = ''
  return NextResponse.redirect(url)
}

export const config = {
  matcher: ['/((?!login|_next/static|_next/image|.*\\.(?:png|jpg|jpeg|svg|ico)$).*)'],
}
