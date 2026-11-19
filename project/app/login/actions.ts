'use server'

import { cookies } from 'next/headers'
import { redirect } from 'next/navigation'
import { SESSION_COOKIE, SESSION_MAX_AGE, makeToken, safeEqual } from '@/lib/session'

export async function loginAction(_prev: string | null, formData: FormData): Promise<string | null> {
  const expected = process.env.UI_PASSWORD ?? ''
  if (expected.length < 8 || (process.env.SESSION_SECRET ?? '').length < 16) {
    return 'Sign-in is not configured. Set UI_PASSWORD (8+ characters) and SESSION_SECRET (16+ characters) on the server.'
  }
  const given = String(formData.get('password') ?? '')
  if (!safeEqual(given, expected)) {
    await new Promise((r) => setTimeout(r, 800)) // slows down guessing
    return 'Wrong password.'
  }
  ;(await cookies()).set(SESSION_COOKIE, await makeToken(), {
    httpOnly: true,
    sameSite: 'lax',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: SESSION_MAX_AGE,
  })
  redirect('/brief')
}

export async function logoutAction() {
  ;(await cookies()).delete(SESSION_COOKIE)
  redirect('/login')
}
