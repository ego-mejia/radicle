import styled from 'styled-components';
import type { Priority } from '../../../services/api/types';

export const Wrap = styled.span<{ $priority: Priority }>`
  display: inline-grid;
  place-items: center;
  flex: none;
  color: ${({ theme, $priority }) =>
    $priority === 'highest'
      ? theme.color.danger
      : $priority === 'high'
        ? theme.color.warning
        : theme.color.textMuted};
`;
