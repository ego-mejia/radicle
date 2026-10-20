import { act, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import type { MilestoneRecap } from '../../../../services/api/types';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { announceDone } from '../../lib/celebrate';
import { MilestoneCelebration } from '.';

const fetchRecap = vi.fn();
vi.mock('../../lib/shareCard', () => ({
  drawShareCard: () => Promise.resolve(new Blob(['png'], { type: 'image/png' })),
}));
vi.mock('../../../../services/api/projects', async (original) => ({
  ...(await original<typeof import('../../../../services/api/projects')>()),
  fetchMilestoneRecap: (...args: unknown[]) => fetchRecap(...args),
}));

const RECAP: MilestoneRecap = {
  milestone: 'V1',
  project_key: 'PA',
  project_name: 'ProyectoA',
  target_date: '2026-12-15',
  complete: true,
  on_time: true,
  tickets: 12,
  done: 12,
  tasks: 8,
  bugs: 3,
  ideas: 1,
  minutes_logged: 1530,
  comments: 40,
  humans: 3,
  agents: 1,
  people: [{ handle: 'luis', display_name: 'Luis', kind: 'human' }],
  started_at: '2026-10-01T10:00:00Z',
  finished_at: '2026-10-19T10:00:00Z',
  days: 18,
};
// The router mounts the page a tick later; wait for it so the listener is in place.
async function mount() {
  renderWithProviders(<MilestoneCelebration />);
  await act(() => new Promise((resolve) => setTimeout(resolve, 20)));
}

const done = { project: 'PA', milestone: 'V1', status: { category: 'done' } };

describe('MilestoneCelebration', () => {
  beforeEach(() => {
    localStorage.clear();
    // jsdom has no canvas: the confetti simply does not draw.
    vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue(null);
    fetchRecap.mockReset().mockResolvedValue(RECAP);
  });

  it('celebrates when the last ticket is done, once', async () => {
    await mount();
    await act(async () => announceDone(done));
    expect(await screen.findByText('Congratulations! V1 is done 🎉')).toBeInTheDocument();
    expect(fetchRecap).toHaveBeenCalledWith('PA', 'V1');
    expect(screen.getByText(/and on time/)).toBeInTheDocument();
    expect(screen.getByText('25.5h')).toBeInTheDocument();
    expect(screen.getByText('Bugs squashed')).toBeInTheDocument();
    expect(screen.getByText('3 people · 1 AI agent')).toBeInTheDocument();

    act(() => screen.getByRole('button', { name: 'Close' }).click());
    await act(async () => announceDone(done));
    await waitFor(() => expect(fetchRecap).toHaveBeenCalledTimes(2));
    expect(screen.queryByText(/Congratulations/)).not.toBeInTheDocument();
  });

  it('shares the card on LinkedIn', async () => {
    const write = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, { clipboard: { write } });
    vi.stubGlobal(
      'ClipboardItem',
      class {
        constructor(public items: Record<string, Blob>) {}
      },
    );
    const tab = { location: { href: '' } };
    vi.spyOn(window, 'open').mockReturnValue(tab as unknown as Window);
    await mount();
    await act(async () => announceDone(done));
    await act(async () =>
      (await screen.findByRole('button', { name: /Share on LinkedIn/ })).click(),
    );
    await waitFor(() => expect(tab.location.href).toContain('linkedin.com/feed/?shareActive=true'));
    expect(write).toHaveBeenCalledTimes(1);
    expect(decodeURIComponent(tab.location.href)).toContain('completed V1 in ProyectoA');
    expect(await screen.findByText(/Image copied/)).toBeInTheDocument();
    vi.unstubAllGlobals();
  });

  it('stays quiet while tickets remain or the ticket is not done', async () => {
    fetchRecap.mockResolvedValue({ ...RECAP, complete: false, done: 11 });
    await mount();
    await act(async () => announceDone(done));
    await act(async () => announceDone({ ...done, status: { category: 'in_progress' } }));
    await act(async () => announceDone({ ...done, milestone: null }));
    expect(fetchRecap).toHaveBeenCalledTimes(1);
    expect(screen.queryByText(/Congratulations/)).not.toBeInTheDocument();
  });
});
