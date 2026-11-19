import type { ReactNode } from 'react'
import { Check, type LucideIcon } from 'lucide-react'

export const panel =
  'rounded-xl border border-[#e4dac6] bg-[#fcfaf5] p-5 shadow-[0_1px_2px_rgba(0,0,0,0.035)] sm:p-6 dark:border-zinc-800 dark:bg-[#111114]'

export function PageHeader({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string
  title: string
  description?: string
  action?: ReactNode
}) {
  return (
    <header className="mb-7 flex flex-col gap-5 sm:flex-row sm:items-end sm:justify-between">
      <div>
        <p className="mb-2 font-mono text-[12px] font-medium uppercase tracking-[0.14em] text-teal-700 dark:text-zinc-400">{eyebrow}</p>
        <h1 className="font-heading text-[30px] font-medium leading-tight tracking-tight sm:text-[38px]">{title}</h1>
        {description && <p className="mt-1.5 text-sm text-[#655e57] dark:text-zinc-400">{description}</p>}
      </div>
      {action}
    </header>
  )
}

export function Panel({
  children,
  className = '',
  ...rest
}: { children: ReactNode; className?: string } & React.HTMLAttributes<HTMLElement>) {
  return (
    <section className={`${panel} ${className}`} {...rest}>
      {children}
    </section>
  )
}

export function StatCard({ icon: Icon, label, value, detail }: { icon: LucideIcon; label: string; value: number | string; detail: string }) {
  return (
    <article className="rounded-xl border border-[#e4dac6] bg-[#fcfaf5] p-4 shadow-[0_1px_2px_rgba(0,0,0,0.035)] dark:border-zinc-800 dark:bg-[#111114]">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-[13px] font-medium text-stone-600 dark:text-zinc-400">{label}</h2>
        <Icon aria-hidden="true" className="size-4 text-[#655e57] dark:text-zinc-500" strokeWidth={1.8} />
      </div>
      <div className="flex items-baseline justify-between gap-2">
        <span className="font-heading text-[32px] font-medium leading-none tracking-tight tabular-nums">{value}</span>
        <span className="text-[12px] text-[#655e57] dark:text-zinc-500">{detail}</span>
      </div>
    </article>
  )
}

export function SectionHeading({ icon: Icon, title, count, id }: { icon: LucideIcon; title: string; count?: number; id?: string }) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2.5">
        <Icon aria-hidden="true" className="size-4 text-[#655e57] dark:text-zinc-400" strokeWidth={1.8} />
        <h2 id={id} className="font-heading text-[18px] font-medium tracking-tight">{title}</h2>
      </div>
      {count !== undefined && (
        <span className="rounded-md bg-[#efe8d9] px-2 py-1 text-[11px] font-medium tabular-nums text-[#655e57] dark:bg-zinc-800 dark:text-zinc-400">{count}</span>
      )}
    </div>
  )
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="rounded-lg border border-dashed border-[#d6c9ae] px-4 py-6 text-center text-xs text-[#655e57] dark:border-zinc-700 dark:text-zinc-400">
      {message}
    </div>
  )
}

const tones = {
  neutral: 'bg-[#efe8d9] text-stone-600 dark:bg-zinc-800 dark:text-zinc-400',
  info: 'bg-[#e3efeb] text-teal-800 dark:bg-blue-400/10 dark:text-blue-300',
  danger: 'bg-red-50 text-red-700 dark:bg-red-400/10 dark:text-red-300',
  warning: 'bg-amber-50 text-amber-800 dark:bg-amber-400/10 dark:text-amber-300',
  success: 'bg-[#f3e6d5] text-[#7c3a12] dark:bg-green-400/10 dark:text-green-300',
  accent: 'bg-teal-100 text-teal-900 dark:bg-indigo-400/10 dark:text-indigo-300',
} as const
export type Tone = keyof typeof tones

export function Pill({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`inline-flex items-center gap-1 rounded-md px-1.5 py-0.5 font-mono text-[11px] font-medium capitalize ${tones[tone]}`}>{tone === 'success' && <Check aria-hidden="true" className="size-3" strokeWidth={2.5} />}{children}</span>
}

export const iconTile = {
  danger: 'bg-red-50 text-red-600 dark:bg-red-400/10 dark:text-red-300',
  info: 'bg-[#e3efeb] text-teal-700 dark:bg-blue-400/10 dark:text-blue-300',
}

export function NoteBox({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="max-h-64 min-w-0 overflow-y-auto rounded-lg border border-[#ece5d6] bg-[#f8f4ea] px-3 py-2.5 wrap-anywhere text-[12px] leading-relaxed text-stone-600 dark:border-zinc-800 dark:bg-zinc-900/70 dark:text-zinc-400">
      <span className="mb-1 block font-mono text-[11px] font-medium uppercase tracking-[0.1em] text-[#655e57] dark:text-zinc-500">{label}</span>
      <span className="whitespace-pre-wrap">{children}</span>
    </div>
  )
}

export function ErrorNotice({ children }: { children: ReactNode }) {
  return (
    <div role="alert" className="rounded-xl border border-red-200 bg-red-50 p-4 text-[14px] text-red-700 dark:border-red-400/30 dark:bg-red-400/[0.07] dark:text-red-300">
      {children}
    </div>
  )
}

export function Loading() {
  return (
    <div className="space-y-4" aria-busy="true" aria-label="Loading">
      <div className="h-12 w-56 animate-pulse motion-reduce:animate-none rounded-lg bg-[#e6dcc8] dark:bg-zinc-800" />
      <div className="h-32 animate-pulse motion-reduce:animate-none rounded-xl bg-[#e6dcc8]/70 dark:bg-zinc-800/60" />
      <div className="h-48 animate-pulse motion-reduce:animate-none rounded-xl bg-[#e6dcc8]/70 dark:bg-zinc-800/60" />
    </div>
  )
}
