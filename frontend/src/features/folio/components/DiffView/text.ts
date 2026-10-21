/** Readable text of a TipTap block, for diffs: headings keep their #, lists their bullet. */
type Json = { type?: string; text?: string; attrs?: Record<string, unknown>; content?: Json[] };

function inline(node: Json): string {
  if (node.type === 'text') return node.text ?? '';
  if (node.type === 'hardBreak') return '\n';
  return (node.content ?? []).map(inline).join('');
}

export function blockText(block: Json): string {
  const children = block.content ?? [];
  switch (block.type) {
    case 'heading':
      return `${'#'.repeat(Number(block.attrs?.level ?? 1))} ${inline(block)}`;
    case 'bulletList':
    case 'orderedList':
    case 'taskList':
      return children.map((item) => `• ${blockText(item)}`).join('\n');
    case 'codeBlock':
      return inline(block);
    case 'image':
      return `[${String(block.attrs?.alt ?? block.attrs?.title ?? 'image')}]`;
    case 'horizontalRule':
      return '———';
    default:
      return children.length && children.every((c) => c.type === 'text' || c.type === 'hardBreak')
        ? inline(block)
        : children.map(blockText).filter(Boolean).join('\n');
  }
}

/** A metadata value as one line: lists joined by commas, empty as a dash. */
export function valueText(value: unknown): string {
  if (value === null || value === undefined || value === '') return '—';
  if (Array.isArray(value)) return value.length ? value.map(String).join(', ') : '—';
  if (typeof value === 'object') return JSON.stringify(value);
  return String(value);
}
