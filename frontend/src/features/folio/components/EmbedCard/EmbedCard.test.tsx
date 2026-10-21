import { screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { EmbedCard } from '.';

const CARD = {
  url: 'https://blog.example.com/post',
  title: 'El post',
  description: 'Lo que hay que saber.',
  site_name: 'blog.example.com',
  icon_url: null,
  image_url: null,
  provider: null,
  embed_url: null,
};

describe('EmbedCard', () => {
  it('shows a card that opens the link, and reports the preview', async () => {
    mockFetch({ 'GET /api/v1/folio/link-preview': { status: 200, body: CARD } });
    const onPreview = vi.fn();
    renderWithProviders(<EmbedCard url={CARD.url} title="Guardado" onPreview={onPreview} />);
    const link = await screen.findByRole('link', { name: /El post/ });
    expect(link).toHaveAttribute('href', CARD.url);
    expect(link).toHaveAttribute('target', '_blank');
    expect(screen.getByText('Lo que hay que saber.')).toBeInTheDocument();
    await vi.waitFor(() => expect(onPreview).toHaveBeenCalledWith(CARD));
  });

  it('embeds the providers in a sandboxed iframe', async () => {
    const video = {
      ...CARD,
      url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
      title: 'La demo',
      provider: 'youtube',
      embed_url: 'https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ',
    };
    mockFetch({ 'GET /api/v1/folio/link-preview': { status: 200, body: video } });
    renderWithProviders(<EmbedCard url={video.url} />);
    const frame = await screen.findByTitle('La demo');
    expect(frame).toHaveAttribute('src', video.embed_url);
    expect(frame.getAttribute('sandbox')).not.toContain('allow-top-navigation');
  });

  it('falls back to the saved title when the preview fails', async () => {
    mockFetch({});
    renderWithProviders(<EmbedCard url={CARD.url} title="Guardado" />);
    expect(await screen.findByRole('link', { name: /Guardado/ })).toBeInTheDocument();
  });
});
