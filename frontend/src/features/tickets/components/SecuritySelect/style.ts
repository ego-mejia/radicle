import styled from 'styled-components';

export const Chip = styled.span<{ $locked: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 26px;
  padding: 0 8px;
  border-radius: ${({ theme }) => theme.radius.full};
  border: 1px solid ${({ theme, $locked }) => ($locked ? theme.color.warning : theme.color.border)};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme, $locked }) => ($locked ? theme.color.warning : theme.color.textMuted)};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  cursor: pointer;
`;
