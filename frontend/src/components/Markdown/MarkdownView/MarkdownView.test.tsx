import { screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import i18n from '../../../i18n';
import { TICKET } from '../../../test/fixtures';
import { renderWithProviders } from '../../../test/renderWithProviders';
import { MarkdownView } from '.';

describe('MarkdownView checklist', () => {
  beforeEach(() => i18n.changeLanguage('en'));

  it('renders checkboxes in API order with assignees', async () => {
    renderWithProviders(
      <MarkdownView checklist={TICKET.checklist} onToggle={() => undefined}>
        {TICKET.description_md}
      </MarkdownView>,
    );
    const boxes = await screen.findAllByRole('checkbox');
    expect(boxes.map((b) => (b as HTMLInputElement).checked)).toEqual([true, false, false]);
    expect(screen.getByRole('img', { name: '@luis' })).toBeInTheDocument();
    expect(screen.getByText('@nadie does not exist')).toBeInTheDocument();
  });

  it('toggles the clicked item by its index', async () => {
    const onToggle = vi.fn();
    renderWithProviders(
      <MarkdownView checklist={TICKET.checklist} onToggle={onToggle}>
        {TICKET.description_md}
      </MarkdownView>,
    );
    const boxes = await screen.findAllByRole('checkbox');
    await userEvent.click(boxes[1]!);
    expect(onToggle).toHaveBeenCalledWith(1, true);
    await userEvent.click(boxes[0]!);
    expect(onToggle).toHaveBeenCalledWith(0, false);
  });

  it('ignores checklist-looking lines in code blocks', async () => {
    const md = '```\n- [ ] not an item\n```\n- [ ] real';
    renderWithProviders(
      <MarkdownView
        checklist={[
          { index: 0, text: 'real', checked: false, assignee: null, assignee_unknown: false },
        ]}
        onToggle={() => undefined}
      >
        {md}
      </MarkdownView>,
    );
    const boxes = await screen.findAllByRole('checkbox');
    expect(boxes).toHaveLength(1);
    expect(boxes[0]).toBeEnabled();
  });

  it('is read only without onToggle and sanitizes html', async () => {
    renderWithProviders(
      <MarkdownView
        checklist={TICKET.checklist}
      >{`${TICKET.description_md}\n\n<img src=x onerror=alert(1)>`}</MarkdownView>,
    );
    const boxes = await screen.findAllByRole('checkbox');
    expect(boxes.every((b) => (b as HTMLInputElement).disabled)).toBe(true);
    expect(document.querySelector('img[onerror]')).toBeNull();
  });
});
