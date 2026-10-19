import * as Tooltip from '@radix-ui/react-tooltip';
import styled from 'styled-components';

export const Button = styled.button<{ $active: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 10px;
  border-radius: ${({ theme }) => theme.radius.full};
  border: 1px solid ${({ theme, $active }) => ($active ? theme.color.accent : theme.color.border)};
  background: ${({ theme, $active }) => ($active ? theme.color.accentSoft : 'transparent')};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  cursor: pointer;

  &:disabled {
    cursor: default;
    opacity: 0.8;
  }
`;

export const Tip = styled(Tooltip.Content)`
  max-width: 260px;
  padding: 6px 10px;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.text};
  color: ${({ theme }) => theme.color.bg};
  font-size: ${({ theme }) => theme.fontSize.sm};
  z-index: 70;
`;
