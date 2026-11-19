import { Analytics } from '@vercel/analytics/next'
import { Geist_Mono, Instrument_Serif, Plus_Jakarta_Sans } from 'next/font/google'
import type { Metadata, Viewport } from 'next'
import './globals.css'

const plusJakartaSans = Plus_Jakarta_Sans({
  subsets: ['latin'],
  variable: '--font-plus-jakarta-sans',
  display: 'swap',
})

const brandFont = Instrument_Serif({
  subsets: ['latin'],
  weight: '400',
  variable: '--font-brand',
  display: 'swap',
})

const geistMono =Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
  display: 'swap',
})

export const metadata: Metadata = {
  title: { default: 'Executive Assistant', template: '%s | Executive Assistant' },
  description: 'A calm, clear view of your meetings, follow-ups, and approvals for today.',
  generator: 'Next.js',
}

export const viewport: Viewport = {
  colorScheme: 'light dark',
  themeColor: [
    { media: '(prefers-color-scheme: light)', color: 'white' },
    { media: '(prefers-color-scheme: dark)', color: 'black' },
  ],
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`${plusJakartaSans.variable} ${geistMono.variable} ${brandFont.variable} font-sans antialiased`}>
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
