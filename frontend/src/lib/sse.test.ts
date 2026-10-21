import { describe, expect, it } from 'vitest';
import { parseBlock, readEvents } from './sse';

function streamOf(...chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder();
  return new ReadableStream({
    start(controller) {
      for (const chunk of chunks) controller.enqueue(encoder.encode(chunk));
      controller.close();
    },
  });
}

describe('readEvents', () => {
  it('reads events split anywhere across chunks', async () => {
    const body = streamOf(
      'event: delta\ndata: {"text": "Ve a "}\n\nevent: del',
      'ta\ndata: {"text": "Admin [1]."}\n\n',
      'event: done\ndata: {"message": {"id": "m1"}}\n\n',
    );
    const got = [];
    for await (const e of readEvents(body)) got.push(e);
    expect(got).toEqual([
      { event: 'delta', data: { text: 'Ve a ' } },
      { event: 'delta', data: { text: 'Admin [1].' } },
      { event: 'done', data: { message: { id: 'm1' } } },
    ]);
  });

  it('keeps a last event without its blank line and skips comments', async () => {
    const got = [];
    for await (const e of readEvents(streamOf(': ping\n\nevent: error\ndata: {"detail": "x"}'))) {
      got.push(e);
    }
    expect(got).toEqual([{ event: 'error', data: { detail: 'x' } }]);
    expect(parseBlock(': ping')).toBeNull();
  });
});
