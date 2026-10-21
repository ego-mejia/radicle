import { fireEvent, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { useThemeMode } from '../../../../hooks/useThemeMode';
import { darkTheme } from '../../../../styles/theme';
import { renderWithProviders } from '../../../../test/renderWithProviders';
import { Diagram } from '.';

const mermaid = vi.hoisted(() => ({ initialize: vi.fn(), render: vi.fn() }));
vi.mock('mermaid', () => ({ default: mermaid }));

function Dark() {
  const { setPreference } = useThemeMode();
  return <button onClick={() => setPreference('dark')}>dark</button>;
}

describe('Diagram', () => {
  beforeEach(() => {
    mermaid.initialize.mockClear();
    mermaid.render.mockReset();
  });

  it('draws the Mermaid source in the theme and redraws when it changes', async () => {
    mermaid.render.mockResolvedValue({ svg: '<svg data-testid="drawn"></svg>' });
    renderWithProviders(
      <>
        <Dark />
        <Diagram source="flowchart LR; A-->B" caption="Flujo" />
      </>,
    );
    expect(await screen.findByTestId('drawn')).toBeInTheDocument();
    expect(screen.getByRole('img', { name: 'Flujo' })).toBeInTheDocument();
    expect(mermaid.render).toHaveBeenCalledWith(expect.any(String), 'flowchart LR; A-->B');
    expect(mermaid.initialize.mock.calls[0]?.[0]).toMatchObject({ securityLevel: 'strict' });

    fireEvent.click(screen.getByRole('button', { name: 'dark' }));
    await waitFor(() =>
      expect(mermaid.initialize.mock.calls.at(-1)?.[0].themeVariables).toMatchObject({
        darkMode: true,
        textColor: darkTheme.color.text,
      }),
    );
  });

  it('says why a diagram does not compile', async () => {
    mermaid.render.mockRejectedValue(new Error('Parse error on line 1:\nflowchart ->'));
    renderWithProviders(<Diagram source="flowchart ->" />);
    const alert = await screen.findByRole('alert');
    expect(alert).toHaveTextContent("This diagram doesn't compile:");
    expect(alert).toHaveTextContent('Parse error on line 1:');
    expect(alert).toHaveTextContent('flowchart ->');
  });
});
