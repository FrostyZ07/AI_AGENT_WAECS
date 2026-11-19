export function formatTime(value: string) {
  const [hours, minutes] = value.split(':').map(Number)
  const suffix = hours >= 12 ? 'PM' : 'AM'
  const hour = hours % 12 || 12
  return `${hour}:${String(minutes).padStart(2, '0')} ${suffix}`
}

export function dayLabel(day: number): string {
  if (day === 0) return 'Today'
  if (day === 1) return 'Tomorrow'
  return `In ${day} days`
}
