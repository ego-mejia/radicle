/** "1h 30m", "1.5h", "90m" or "90" (minutes) to minutes; null if it cannot be read. */
export function parseDuration(text: string): number | null {
  const value = text.trim().toLowerCase().replace(',', '.');
  if (!value) return null;
  if (/^\d+$/.test(value)) return Number(value);
  const match = /^(?:(\d+(?:\.\d+)?)\s*h)?\s*(?:(\d+)\s*m)?$/.exec(value);
  if (!match || (!match[1] && !match[2])) return null;
  const minutes = Math.round(Number(match[1] ?? 0) * 60) + Number(match[2] ?? 0);
  return minutes > 0 ? minutes : null;
}

export function formatMinutes(minutes: number): string {
  const h = Math.floor(minutes / 60);
  const m = minutes % 60;
  if (!h) return `${m}m`;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export function formatHours(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) return '—';
  return formatMinutes(Math.round(hours * 60));
}
