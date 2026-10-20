import styled from 'styled-components';

export const Column = styled.section<{
  $state: 'idle' | 'allowed' | 'blocked' | 'over';
  $over?: boolean;
}>`
  display: flex;
  flex-direction: column;
  min-width: 0;
  min-height: 300px;
  background: ${({ theme, $state }) =>
    $state === 'over'
      ? theme.color.accentSoft
      : theme.mode === 'dark'
        ? theme.color.surface
        : theme.color.surface2};
  border-radius: ${({ theme }) => theme.radius.md};
  box-shadow: ${({ theme, $state, $over }) =>
    $state === 'allowed' || $state === 'over'
      ? `inset 0 0 0 2px ${theme.color.accent}`
      : $over
        ? `inset 0 0 0 2px ${theme.color.danger}`
        : 'none'};
  opacity: ${({ $state }) => ($state === 'blocked' ? 0.45 : 1)};
  transition:
    background 0.1s,
    box-shadow 0.1s,
    opacity 0.1s;
`;

export const Head = styled.header`
  position: sticky;
  top: 0;
  z-index: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px 8px;
  border-radius: ${({ theme }) => `${theme.radius.md} ${theme.radius.md} 0 0`};
  background: inherit;

  h2 {
    margin: 0;
    color: ${({ theme }) => theme.color.textMuted};
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
`;

export const Count = styled.span<{ $over?: boolean }>`
  padding: 0 6px;
  border-radius: ${({ theme }) => theme.radius.full};
  font-size: 12px;
  font-weight: 600;
  color: ${({ theme, $over }) => ($over ? theme.color.surface : theme.color.textMuted)};
  background: ${({ theme, $over }) => ($over ? theme.color.danger : 'transparent')};
`;

export const Cards = styled.div`
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 2px 8px 8px;
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
