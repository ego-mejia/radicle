import styled from 'styled-components';

export const Row = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  min-width: 0;
`;

export const Chip = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  max-width: 100%;
  height: 20px;
  padding: 0 6px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 3px;
  background: ${({ theme }) => theme.color.surface};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  color: ${({ theme }) => theme.color.text};
  cursor: inherit;

  span {
    overflow: hidden;
    white-space: nowrap;
    text-overflow: ellipsis;
  }

  > svg {
    flex: none;
    width: 12px;
    height: 12px;
    color: ${({ theme }) => theme.color.textMuted};
  }

  &:is(button) {
    cursor: pointer;

    &:hover,
    &[data-state='open'] {
      background: ${({ theme }) => theme.color.surface2};
    }

    &:focus-visible {
      outline: 2px solid ${({ theme }) => theme.color.accent};
      outline-offset: 1px;
    }
  }

  /* An empty milestone shows only on the hovered or focused card (see TicketCard). */
  &[data-empty] {
    border-style: dashed;
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 400;
    opacity: 0;
    transition: opacity 0.1s;
  }

  &[data-empty][data-state='open'],
  &[data-empty]:focus-visible {
    opacity: 1;
  }
`;
