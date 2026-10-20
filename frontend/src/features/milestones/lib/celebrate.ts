import type { TFunction } from 'i18next';
import type { MilestoneRecap } from '../../../services/api/types';

export type CardStat = { value: string; label: string };

/** Fired when a ticket with a milestone reaches done; the celebration checks the rest. */
export const TICKET_DONE = 'radicle:ticket-done';
export type TicketDone = { project: string; milestone: string };

export function announceDone(ticket: {
  project: string;
  milestone: string | null;
  status: { category: string };
}) {
  if (ticket.status.category !== 'done' || !ticket.milestone) return;
  const detail: TicketDone = { project: ticket.project, milestone: ticket.milestone };
  window.dispatchEvent(new CustomEvent(TICKET_DONE, { detail }));
}

/** Celebrate each milestone once per browser, even if its last ticket moves twice. */
export function firstTime(project: string, milestone: string): boolean {
  const key = `radicle:celebrated:${project}:${milestone}`;
  try {
    if (localStorage.getItem(key)) return false;
    localStorage.setItem(key, new Date().toISOString());
  } catch {
    // No storage (private mode): celebrate anyway.
  }
  return true;
}

/** The numbers worth bragging about, best first. */
export function recapStats(r: MilestoneRecap, t: TFunction): CardStat[] {
  const hours = Math.round((r.minutes_logged / 60) * 10) / 10;
  const stats: CardStat[] = [
    { value: String(r.done), label: t('celebration.stats.shipped') },
    { value: `${hours}h`, label: t('celebration.stats.hours') },
    { value: String(r.bugs), label: t('celebration.stats.bugs') },
    { value: String(r.tasks), label: t('celebration.stats.tasks') },
    { value: String(r.ideas), label: t('celebration.stats.ideas') },
  ];
  if (r.days !== null) stats.push({ value: String(r.days), label: t('celebration.stats.days') });
  else stats.push({ value: String(r.comments), label: t('celebration.stats.comments') });
  return stats;
}

export function teamLine(r: MilestoneRecap, t: TFunction): string {
  const people = t('celebration.people', { count: r.humans });
  return r.agents ? `${people} · ${t('celebration.agents', { count: r.agents })}` : people;
}
