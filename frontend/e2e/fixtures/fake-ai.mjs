/**
 * A deterministic OpenAI-compatible chat server for the end-to-end specs, so Folio's AI
 * (chat, summarize, rewrite, publish suggestions, glossary) runs without a real model.
 * It answers from what Radicle sends: the chat cites the passage that shares the most
 * words with the question. Start it with `startFakeAi(port)` or `node fake-ai.mjs 8790`.
 */
import http from 'node:http';
import { fileURLToPath } from 'node:url';

const WORD = /[\p{L}\p{N}]{4,}/gu;
const words = (text) => new Set((text.toLowerCase().match(WORD) ?? []).map((w) => w));

function passages(system) {
  const block = system.split('Passages:')[1] ?? '';
  return block
    .trim()
    .split(/\n\n(?=\[\d+\] )/)
    .map((part) => part.match(/^\[(\d+)\] (.+)\n([\s\S]*)$/))
    .filter(Boolean)
    .map((m) => ({ n: Number(m[1]), title: m[2], text: m[3].trim() }));
}

function chatAnswer(system, question) {
  const asked = words(question);
  let best = null;
  let score = 0;
  for (const p of passages(system)) {
    const have = words(`${p.title} ${p.text}`);
    const s = [...asked].filter((w) => have.has(w)).length;
    if (s > score) [best, score] = [p, s];
  }
  if (!best || score < 2) {
    const who = system.match(/suggest asking (.+?)\. Don't guess/)?.[1] ?? 'un admin';
    return `Los docs no cubren esto. Te sugiero preguntarle a ${who}.`;
  }
  const sentence = best.text.replace(/\s+/g, ' ').split(/(?<=[.!?])\s/)[0];
  const outdated = best.title.includes('(OUTDATED)')
    ? ' Ojo: esta guía puede estar desactualizada.'
    : '';
  return `Según **${best.title.replace(' (OUTDATED)', '')}**: ${sentence} [${best.n}]${outdated}`;
}

function metadata(prompt) {
  const types = prompt.match(/^Document types: (.*)$/m)?.[1].split(', ') ?? [];
  const inUse = (prompt.match(/^Labels in use: (.*)$/m)?.[1] ?? '').split(', ');
  const body = prompt.split(/^# .*$/m)[1] ?? prompt;
  const first = body
    .replace(/[#*_>`[\]]/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  let description = first.split(/(?<=[.!?])\s/)[0].slice(0, 380);
  if (description.length < 40) description = `${description} Guía interna del equipo.`.trim();
  const labels = inUse.filter((l) => l && l !== 'none yet').slice(0, 2);
  return JSON.stringify({
    description: description.endsWith('.') ? description : `${description}.`,
    labels: labels.length ? labels : ['guia'],
    doc_type: types.includes('how-to') ? 'how-to' : types[0],
  });
}

const TERMS = [
  ['MCP', 'Model Context Protocol: el protocolo con el que los agentes usan las tools de Radicle.'],
  ['RQL', 'El lenguaje de consultas de Radicle para filtrar tickets y docs.'],
  ['Folio', 'La app de documentación de Radicle: spaces, páginas, búsqueda y chat.'],
  ['Docket', 'El ticket tracker de Radicle: proyectos, tickets, milestones y áreas.'],
];

function glossary(docs) {
  const found = [];
  const parts = docs.split(/\n\n(?=\[\d+\] )/).map((p) => p.match(/^\[(\d+)\] ([\s\S]*)$/));
  for (const [term, definition] of TERMS) {
    const doc = parts.find((m) => m && m[2].includes(term));
    if (doc) found.push({ term, aliases: [], definition, doc: Number(doc[1]) });
  }
  return JSON.stringify(found);
}

function summarize(page) {
  const heads = [...page.matchAll(/^#{1,3} (.+)$/gm)].map((m) => m[1]).slice(1, 6);
  const points = heads.length ? heads : page.split(/(?<=[.!?])\s/).slice(0, 3);
  return points.map((p) => `- ${p.trim()}`).join('\n');
}

function rewrite(system, text) {
  const sentences = text.trim().split(/(?<=[.!?])\s+/);
  if (system.includes('shorter')) return sentences[0];
  if (system.includes('Translate')) return `${text.trim()} (translated)`;
  if (system.includes('formal')) return `Se recomienda lo siguiente: ${text.trim()}`;
  return sentences.map((s) => s.charAt(0).toUpperCase() + s.slice(1)).join('\n\n');
}

export function reply(messages = []) {
  const system = messages.find((m) => m.role === 'system')?.content ?? '';
  const user = [...messages].reverse().find((m) => m.role === 'user')?.content ?? '';
  if (system.startsWith('You answer questions')) return chatAnswer(system, user);
  if (system.startsWith('You propose publishing metadata')) return metadata(user);
  if (system.startsWith('You build a glossary')) return glossary(user);
  if (system.startsWith('You summarize')) return summarize(user);
  if (system.startsWith('You edit a passage')) return rewrite(system, user);
  return 'OK';
}

function send(res, body) {
  if (!body.stream) {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        choices: [{ message: { role: 'assistant', content: reply(body.messages) } }],
        usage: { prompt_tokens: 100, completion_tokens: 40 },
      }),
    );
    return;
  }
  res.writeHead(200, { 'Content-Type': 'text/event-stream' });
  const pieces = reply(body.messages).match(/\S+\s*/g) ?? [];
  let i = 0;
  const tick = setInterval(() => {
    if (i < pieces.length) {
      res.write(`data: ${JSON.stringify({ choices: [{ delta: { content: pieces[i++] } }] })}\n\n`);
      return;
    }
    clearInterval(tick);
    res.write(
      `data: ${JSON.stringify({ choices: [], usage: { prompt_tokens: 100, completion_tokens: pieces.length } })}\n\n`,
    );
    res.end('data: [DONE]\n\n');
  }, 30);
}

export function startFakeAi(port = 8790) {
  const server = http.createServer((req, res) => {
    let raw = '';
    req.on('data', (c) => (raw += c));
    req.on('end', () => {
      if (req.method === 'POST' && req.url?.endsWith('/chat/completions')) {
        try {
          send(res, JSON.parse(raw || '{}'));
        } catch (e) {
          res.writeHead(400, { 'Content-Type': 'application/json' });
          res.end(JSON.stringify({ error: { message: String(e) } }));
        }
        return;
      }
      res.writeHead(404, { 'Content-Type': 'application/json' });
      res.end('{"error":{"message":"not found"}}');
    });
  });
  return new Promise((resolve) => server.listen(port, '0.0.0.0', () => resolve(server)));
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const port = Number(process.argv[2] ?? 8790);
  await startFakeAi(port);
  console.log(`fake AI on http://0.0.0.0:${port}/v1`);
}
