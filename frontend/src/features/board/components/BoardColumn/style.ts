import styled from 'styled-components';

export const Column = styled.section<{ $state: 'idle' | 'allowed' | 'blocked' | 'over' }>`
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 300px;
  background: ${({ theme }) => (theme.mode === 'dark' ? theme.color.surface : theme.color.surface2)};
  border: 1px solid
    ${({ theme, $state }) =>
      $state === 'over'
        ? theme.color.accent
        : $state === 'allowed'
          ? theme.color.accentSoft
          : theme.color.border};
  border-style: ${({ $state }) => ($state === 'allowed' ? 'dashed' : 'solid')};
  border-radius: ${({ theme }) => theme.radius.lg};
  opacity: ${({ $state }) => ($state === 'blocked' ? 0.45 : 1)};
  transition:
    border-color 0.1s,
    opacity 0.1s;
`;

export const Head = styled.header`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.md};
    font-weight: 700;
  }
`;

export const Count = styled.span`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Cards = styled.div`
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 0 8px 8px;
  overflow-y: auto;
`;

export const Footer = styled.div`
  padding: 4px 12px 10px;
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Empty = styled.div`
  padding: 16px 8px;
  text-align: center;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;
