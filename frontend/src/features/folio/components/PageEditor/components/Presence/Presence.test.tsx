import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { renderWithProviders } from '../../../../../../test/renderWithProviders';
import {
  colorFor,
  readPeers,
  throttle,
  uniquePeople,
  type Peer,
} from '../../../../editor/presence';
import { Presence } from '.';

const peer = (clientId: number, name: string, extra: Partial<Peer> = {}): Peer => ({
  clientId,
  name,
  handle: name.toLowerCase(),
  color: colorFor(name),
  agent: false,
  ...extra,
});

describe('Presence', () => {
  it('shows each person once and the agent writing', async () => {
    renderWithProviders(
      <Presence
        peers={[
          peer(1, 'Ana Torres'),
          peer(2, 'Ana Torres'), // a second tab
          peer(3, 'Luis'),
          peer(4, 'Agente de docs', { agent: true }),
        ]}
      />,
    );
    expect(await screen.findByLabelText('3 people in this document')).toBeInTheDocument();
    expect(screen.getByText('AT')).toBeInTheDocument();
    expect(screen.getByText('Agente de docs is writing')).toBeInTheDocument();
  });

  it('shows nothing when you are alone', async () => {
    renderWithProviders(<Presence peers={[]} />);
    await new Promise((resolve) => setTimeout(resolve, 0));
    expect(screen.queryByLabelText(/in this document/)).toBeNull();
  });
});

describe('presence helpers', () => {
  it('reads peers from awareness, without this client', () => {
    const states = new Map<number, Record<string, unknown>>([
      [1, { user: { name: 'Yo', color: '#000' } }],
      [
        2,
        {
          user: { name: 'Luis', handle: 'luis', color: '#2563EB' },
          pointer: { x: 1, y: 2, at: 3 },
        },
      ],
      [3, {}], // connected but not announced yet
    ]);
    const peers = readPeers({ getStates: () => states }, 1);
    expect(peers).toEqual([
      {
        clientId: 2,
        name: 'Luis',
        handle: 'luis',
        color: '#2563EB',
        agent: false,
        pointer: { x: 1, y: 2, at: 3 },
      },
    ]);
  });

  it('gives each name the same color from the palette', () => {
    expect(colorFor('ana')).toBe(colorFor('ana'));
    expect(uniquePeople([peer(1, 'B', { agent: true }), peer(2, 'A')]).map((p) => p.name)).toEqual([
      'A',
      'B',
    ]);
  });

  it('throttles to the last value', async () => {
    const seen: number[] = [];
    const push = throttle((n: number) => seen.push(n), 20);
    for (let n = 0; n < 10; n++) push(n);
    expect(seen).toEqual([0]);
    await new Promise((r) => setTimeout(r, 40));
    expect(seen).toEqual([0, 9]);
  });
});
