import i18n from '../i18n';

function locale(): string {
  return i18n.resolvedLanguage === 'es' ? 'es-MX' : 'en-US';
}

/** "3 min ago", "hace 2 días". */
export function relativeTime(iso: string, now = Date.now()): string {
  const seconds = Math.round((new Date(iso).getTime() - now) / 1000);
  const rtf = new Intl.RelativeTimeFormat(locale(), { numeric: 'auto' });
  const units: [Intl.RelativeTimeFormatUnit, number][] = [
    ['year', 31536000],
    ['month', 2592000],
    ['week', 604800],
    ['day', 86400],
    ['hour', 3600],
    ['minute', 60],
  ];
  for (const [unit, size] of units) {
    if (Math.abs(seconds) >= size) return rtf.format(Math.round(seconds / size), unit);
  }
  return rtf.format(seconds, 'second');
}

/** "Nov 15, 2026" for YYYY-MM-DD dates, without timezone shifts. */
export function formatDate(day: string | null | undefined): string {
  if (!day) return '';
  const [y, m, d] = day.split('-').map(Number);
  return new Intl.DateTimeFormat(locale(), { dateStyle: 'medium', timeZone: 'UTC' }).format(
    new Date(Date.UTC(y!, (m ?? 1) - 1, d ?? 1)),
  );
}

export function formatDateTime(iso: string): string {
  return new Intl.DateTimeFormat(locale(), { dateStyle: 'medium', timeStyle: 'short' }).format(
    new Date(iso),
  );
}

export function isOverdue(day: string | null | undefined, today = new Date()): boolean {
  if (!day) return false;
  return day < today.toISOString().slice(0, 10);
}

const KEY_RE = /^\s*([A-Za-z][A-Za-z0-9]{1,9})-(\d+)\s*$/;

/** "pa-4 " -> "PA-4", or null when the text is not a ticket key. */
export function asTicketKey(text: string): string | null {
  const match = KEY_RE.exec(text);
  return match ? `${match[1]!.toUpperCase()}-${match[2]}` : null;
}

export function projectOf(key: string): string {
  return key.split('-')[0]!.toUpperCase();
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
}
