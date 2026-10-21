/** One server-sent event: its name and its parsed JSON data. */
export type ServerEvent = { event: string; data: unknown };

/**
 * Reads server-sent events from a fetch body as they arrive. EventSource only does GET, and
 * the docs chat streams the answer to a POST.
 */
export async function* readEvents(body: ReadableStream<Uint8Array>): AsyncGenerator<ServerEvent> {
  const reader = body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  for (;;) {
    const { value, done } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    let end = buffer.indexOf('\n\n');
    while (end !== -1) {
      const parsed = parseBlock(buffer.slice(0, end));
      if (parsed) yield parsed;
      buffer = buffer.slice(end + 2);
      end = buffer.indexOf('\n\n');
    }
    if (done) break;
  }
  const last = parseBlock(buffer);
  if (last) yield last;
}

export function parseBlock(block: string): ServerEvent | null {
  let event = 'message';
  const data: string[] = [];
  for (const line of block.split('\n')) {
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) data.push(line.slice(5).trimStart());
  }
  if (data.length === 0) return null;
  return { event, data: JSON.parse(data.join('\n')) };
}
