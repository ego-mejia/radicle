import { ApiError } from '../../../../services/api/client';
import type { HomeLayoutBlock } from '../../../../services/api/folio';

export type BlockError = { field: string; message: string; position?: number };

/** A 422's errors by block id: `blocks[2].config.rql` belongs to the third block. */
export function blockErrors(error: unknown, blocks: HomeLayoutBlock[]): Map<string, BlockError[]> {
  const out = new Map<string, BlockError[]>();
  if (!(error instanceof ApiError) || error.status !== 422) return out;
  for (const e of error.problem.errors) {
    const match = /^blocks\[(\d+)\]\.?(.*)$/.exec(e.field ?? '');
    const block = match ? blocks[Number(match[1])] : undefined;
    if (!match || !block) continue;
    const list = out.get(block.id) ?? [];
    list.push({ field: match[2] ?? '', message: e.message, position: e.position });
    out.set(block.id, list);
  }
  return out;
}
