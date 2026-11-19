import { Analytics } from '@vercel/analytics/next'
import { Crimson_Pro, Fraunces, Geist_Mono, Instrument_Serif, Outfit, Plus_Jakarta_Sans } from 'next/font/google'
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
  style: ['normal', 'italic'],
  variable: '--font-brand',
  display: 'swap',
})

const geistMono =Geist_Mono({
  subsets: ['latin'],
  variable: '--font-geist-mono',
  display: 'swap',
})

// Headings: warm serif. Navigation and buttons: geometric sans. Body: Plus Jakarta Sans. Labels: mono.
const headingFont = Fraunces({
  subsets: ['latin'],
  variable: '--font-fraunces',
  display: 'swap',
})

// Reading font: used only for the assistant's brief paragraph.
const readingFont = Crimson_Pro({
  subsets: ['latin'],
  variable: '--font-crimson',
  display: 'swap',
})

const navFont = Outfit({
  subsets: ['latin'],
  variable: '--font-outfit',
  display: 'swap',
})

export const metadata: Metadata = {
  title: { default: 'Executive Assistant', template: '%s | Executive Assistant' },
  description: 'A calm, clear view of your meetings, follow-ups, and approvals for today.',
  generator: 'Next.js',
}

export const viewport: Viewport = {
  colorScheme: 'light',
  themeColor: '#f3eee3',
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en">
      <body className={`${plusJakartaSans.variable} ${geistMono.variable} ${brandFont.variable} ${headingFont.variable} ${navFont.variable} ${readingFont.variable} font-sans antialiased`}>
        {children}
        {process.env.NODE_ENV === 'production' && <Analytics />}
      </body>
    </html>
  )
}
