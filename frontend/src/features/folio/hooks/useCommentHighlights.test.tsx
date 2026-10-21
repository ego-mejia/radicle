import { render } from '@testing-library/react';
import { useRef } from 'react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import type { FolioThread } from '../../../services/api/folioComments';
import { useCommentHighlights } from './useCommentHighlights';

const thread = (quote: string, extra: Partial<FolioThread> = {}): FolioThread => ({
  id: quote,
  kind: 'inline',
  anchor: { quote, prefix: '', suffix: '', offset: 0 },
  orphaned: false,
  resolved_at: null,
  resolved_by: null,
  comments: [],
  ...extra,
});

function Page({ threads }: { threads: FolioThread[] }) {
  const ref = useRef<HTMLDivElement>(null);
  useCommentHighlights(ref, threads, 1);
  return (
    <div ref={ref}>
      <p>Crea el agente y conéctalo por MCP.</p>
    </div>
  );
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe('useCommentHighlights', () => {
  it('highlights open inline threads only', () => {
    const set = vi.fn();
    vi.stubGlobal('CSS', { highlights: { set, delete: vi.fn() } });
    vi.stubGlobal(
      'Highlight',
      class {
        ranges: Range[];
        constructor(...ranges: Range[]) {
          this.ranges = ranges;
        }
      },
    );
    render(
      <Page
        threads={[
          thread('conéctalo por MCP'),
          thread('el agente', { resolved_at: '2026-10-21T00:00:00Z' }),
          thread('borrado', { orphaned: true }),
          thread('no aparece'),
        ]}
      />,
    );
    const [name, highlight] = set.mock.calls[0]!;
    expect(name).toBe('folio-comment');
    expect(highlight.ranges.map((r: Range) => r.toString())).toEqual(['conéctalo por MCP']);
  });

  it('does nothing where the browser has no highlights', () => {
    vi.stubGlobal('CSS', {});
    expect(() => render(<Page threads={[thread('conéctalo por MCP')]} />)).not.toThrow();
  });
});
