import type { StatusConf, TransitionConf, Workflow, WorkflowConf } from '../services/api/types';

export function slug(name: string): string {
  const value = name
    .toLowerCase()
    .normalize('NFD')
    .replace(/[̀-ͯ]/g, '')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '')
    .slice(0, 60);
  return value || 'x';
}

/** A ref not used yet, from a name: "Blocked" -> blocked, blocked_2... */
export function freshRef(name: string, taken: Iterable<string>): string {
  const used = new Set(taken);
  const base = slug(name);
  let ref = base;
  for (let i = 2; used.has(ref); i += 1) ref = `${base}_${i}`;
  return ref;
}

/** Problems that block saving, in the user's language via keys + params. */
export function workflowErrors(
  w: WorkflowConf,
): { key: string; params?: Record<string, string> }[] {
  const errors: { key: string; params?: Record<string, string> }[] = [];
  const initial = w.statuses.filter((s) => s.is_initial).length;
  if (initial !== 1)
    errors.push({ key: 'workflow.errors.initial', params: { count: `${initial}` } });
  if (!w.statuses.some((s) => s.category === 'done')) errors.push({ key: 'workflow.errors.done' });
  const names = w.statuses.map((s) => s.name.trim().toLowerCase());
  const repeated = names.find((n, i) => n && names.indexOf(n) !== i);
  if (repeated) errors.push({ key: 'workflow.errors.repeated', params: { name: repeated } });
  if (names.some((n) => !n)) errors.push({ key: 'workflow.errors.emptyName' });
  return errors;
}

/** Names of statuses that no path from the initial status reaches (a warning). */
export function unreachable(w: WorkflowConf): string[] {
  const byRef = new Map(w.statuses.map((s) => [s.ref, s]));
  const start = w.statuses.find((s) => s.is_initial);
  if (!start) return [];
  const seen = new Set([start.ref]);
  const frontier = [start.ref];
  while (frontier.length) {
    const current = frontier.pop()!;
    for (const t of w.transitions ?? []) {
      const fromOk = t.from === current || (!t.from && byRef.get(current)?.category !== 'done');
      if (fromOk && !seen.has(t.to)) {
        seen.add(t.to);
        frontier.push(t.to);
      }
    }
  }
  return w.statuses.filter((s) => !seen.has(s.ref)).map((s) => s.name);
}

/** Statuses in `before` that are gone from `after` (they need a mapping when they hold tickets). */
export function removedStatuses(before: WorkflowConf, after: WorkflowConf): StatusConf[] {
  const kept = new Set(after.statuses.map((s) => s.ref));
  return before.statuses.filter((s) => !kept.has(s.ref));
}

/** Transitions from `from` (null = any status not done) to `to`. */
export function transitionsBetween(
  w: WorkflowConf,
  from: string | null,
  to: string,
): TransitionConf[] {
  return (w.transitions ?? []).filter((t) => (t.from ?? null) === from && t.to === to);
}

const CATEGORY_STYLE: Record<string, string> = {
  todo: 'fill:#F1F2F4,stroke:#9CA3AF,color:#111827',
  in_progress: 'fill:#ECF8C8,stroke:#4D7C0F,color:#1A2E05',
  done: 'fill:#C6F432,stroke:#4D7C0F,color:#1A2E05',
};

function label(text: string): string {
  return text.replace(/["<>]/g, "'");
}

/** Mermaid state diagram source for the preview. */
export function toMermaid(w: WorkflowConf, anyLabel: string): string {
  const id = (ref: string) => `s_${ref}`;
  const lines = ['flowchart LR'];
  for (const s of w.statuses) {
    lines.push(`  ${id(s.ref)}(["${label(s.name)}"])`);
    lines.push(`  style ${id(s.ref)} ${CATEGORY_STYLE[s.category] ?? ''}`);
  }
  const initial = w.statuses.find((s) => s.is_initial);
  if (initial) lines.push(`  start(( )) --> ${id(initial.ref)}`);
  let anyUsed = false;
  for (const t of w.transitions ?? []) {
    if (!w.statuses.some((s) => s.ref === t.to)) continue;
    if (t.from) {
      lines.push(`  ${id(t.from)} -->|"${label(t.name)}"| ${id(t.to)}`);
    } else {
      anyUsed = true;
      lines.push(`  any{{"${label(anyLabel)}"}} -.->|"${label(t.name)}"| ${id(t.to)}`);
    }
  }
  if (anyUsed) lines.push('  style any fill:none,stroke-dasharray:4 3');
  return lines.join('\n');
}

/** A project's workflow as the editor's configuration, matched by ref. */
export function toConf(workflow: Workflow): WorkflowConf {
  const refOf = (name: string) => workflow.statuses.find((s) => s.name === name)?.ref ?? slug(name);
  return {
    statuses: workflow.statuses.map((s) => ({
      ref: s.ref ?? slug(s.name),
      name: s.name,
      category: s.category,
      is_initial: s.is_initial,
    })),
    transitions: workflow.transitions.map((tr) => ({
      ref: tr.ref ?? slug(tr.name),
      name: tr.name,
      from: tr.from_ref ?? (tr.from_status ? refOf(tr.from_status) : null),
      to: tr.to_ref || refOf(tr.to_status),
      allowed_resolutions: tr.allowed_resolutions,
      rules: tr.rules,
    })),
  };
}
