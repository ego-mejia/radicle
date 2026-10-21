import { screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import { mockFetch, renderWithProviders } from '../../../../test/renderWithProviders';
import { UnansweredQuestions } from '.';

const ROWS = [
  {
    question: '¿Cuál es la receta del pozole?',
    answer: 'No encontré esto en los docs.',
    feedback: null,
    feedback_note: null,
    asked_at: '2026-10-21T10:00:00Z',
  },
  {
    question: '¿Cómo conecto un agente?',
    answer: 'Ve a Admin [1].',
    feedback: 'down',
    feedback_note: 'Falta el token',
    asked_at: '2026-10-21T09:00:00Z',
  },
];

describe('UnansweredQuestions', () => {
  it('lists questions without a source and answers rated down, with the note', async () => {
    mockFetch({
      'GET /api/v1/folio/admin/chat/unanswered': { status: 200, body: { items: ROWS } },
    });
    renderWithProviders(<UnansweredQuestions />);
    expect(await screen.findByText('¿Cuál es la receta del pozole?')).toBeInTheDocument();
    expect(screen.getByText('No source in the docs')).toBeInTheDocument();
    expect(screen.getByText('Rated not helpful')).toBeInTheDocument();
    expect(screen.getByText('“Falta el token”')).toBeInTheDocument();
  });

  it('says when there is nothing to document and shows errors', async () => {
    mockFetch({ 'GET /api/v1/folio/admin/chat/unanswered': { status: 200, body: { items: [] } } });
    renderWithProviders(<UnansweredQuestions />);
    expect(await screen.findByText(/Every question so far/)).toBeInTheDocument();
  });

  it('shows the API error', async () => {
    mockFetch({
      'GET /api/v1/folio/admin/chat/unanswered': {
        status: 403,
        body: { status: 403, detail: 'Only Folio admins see this.', errors: [] },
      },
    });
    renderWithProviders(<UnansweredQuestions />);
    expect(await screen.findByRole('alert')).toHaveTextContent('Only Folio admins see this.');
  });
});
