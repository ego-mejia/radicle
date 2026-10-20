import * as Popover from '@radix-ui/react-popover';
import styled from 'styled-components';

export const Trigger = styled.button`
  display: grid;
  place-items: center;
  width: 32px;
  height: 32px;
  flex: none;
  padding: 0;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  cursor: pointer;

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const Content = styled(Popover.Content)`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.sm};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
  z-index: 50;
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(9, 30px);
  gap: 2px;
`;

export const Choice = styled.button<{ $active: boolean }>`
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid ${({ theme, $active }) => ($active ? theme.color.accent : 'transparent')};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme, $active }) => ($active ? theme.color.accentSoft : 'transparent')};
  cursor: pointer;

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const None = styled.button`
  align-self: flex-start;
  padding: 4px 8px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: transparent;
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
  cursor: pointer;

  &:hover:not(:disabled) {
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.text};
  }

  &:disabled {
    opacity: 0.5;
    cursor: default;
  }
`;
