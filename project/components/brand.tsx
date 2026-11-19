import { BriefcaseBusiness } from 'lucide-react'

// Logo mark + wordmark shared by the sidebar and the login page.
export default function Brand({ size = 'md' }: { size?: 'sm' | 'md' }) {
  const sm = size === 'sm'
  return (
    <span className="flex items-center gap-2.5">
      <span
        className={`grid shrink-0 place-items-center bg-gradient-to-br from-teal-600 to-teal-800 text-white shadow-sm ring-1 ring-inset ring-white/20 ${sm ? 'size-8 rounded-lg' : 'size-9 rounded-xl'}`}
      >
        <BriefcaseBusiness aria-hidden="true" className={sm ? 'size-4' : 'size-[18px]'} strokeWidth={1.8} />
      </span>
      <span className="font-[family-name:var(--font-brand)] text-[21px] italic leading-none tracking-tight">Executive Assistant</span>
    </span>
  )
}
