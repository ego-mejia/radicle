import * as Popover from '@radix-ui/react-popover';
import styled from 'styled-components';

export const Trigger = styled.button<{ $category: string }>`
  display: inline-flex;
  align-items: center;
  gap: 7px;
  height: 30px;
  padding: 0 10px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme, $category }) =>
    $category === 'done' ? theme.color.accentSoft : theme.color.surface};
  font: inherit;
  font-weight: 600;
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;

  &:hover:not(:disabled) {
    border-color: ${({ theme }) => theme.color.accent};
  }

  &:disabled {
    cursor: default;
  }

  svg.chevron {
    width: 14px;
    height: 14px;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Content = styled(Popover.Content)`
  padding: 4px;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
  z-index: 50;
`;

export const Resolution = styled.span`
  font-weight: 400;
  color: ${({ theme }) => theme.color.textMuted};
`;
