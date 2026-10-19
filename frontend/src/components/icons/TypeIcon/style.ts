import styled from 'styled-components';
import type { TicketType } from '../../../services/api/types';

export const Wrap = styled.span<{ $type: TicketType }>`
  display: inline-grid;
  place-items: center;
  flex: none;
  color: ${({ theme, $type }) =>
    $type === 'bug'
      ? theme.color.danger
      : $type === 'draft'
        ? theme.color.warning
        : theme.color.accent};

  svg {
    display: block;
  }
`;
