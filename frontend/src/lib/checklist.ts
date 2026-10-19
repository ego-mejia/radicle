// Mirrors backend/radicle/services/markdown.py: which lines are checklist items, and their index.
const FENCE = /^\s{0,3}(`{3,}|~{3,})/;
const ITEM = /^\s*[-*]\s+\[[ xX]\]\s+/;

/** Map of 0-based line number to checklist index, skipping fenced code. */
export function checklistLines(markdown: string): Map<number, number> {
  const map = new Map<number, number>();
  let fence: string | null = null;
  markdown.split('\n').forEach((line, number) => {
    const match = FENCE.exec(line);
    if (fence !== null) {
      if (match && match[1]![0] === fence[0] && match[1]!.length >= fence.length) fence = null;
      return;
    }
    if (match) {
      fence = match[1]!;
      return;
    }
    if (ITEM.test(line)) map.set(number, map.size);
  });
  return map;
}
