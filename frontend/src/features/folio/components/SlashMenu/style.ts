import styled from 'styled-components';

export const Menu = styled.div`
  width: 260px;
  max-height: 320px;
  overflow-y: auto;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  box-shadow: 0 8px 24px rgb(0 0 0 / 0.12);
  padding: ${({ theme }) => theme.space.xs};
`;

export const Item = styled.button<{ $active: boolean }>`
  display: flex;
  width: 100%;
  min-height: 36px;
  align-items: center;
  padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
  border: 0;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme, $active }) => ($active ? theme.color.accentSoft : 'transparent')};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  text-align: left;
  cursor: pointer;
`;

export const Empty = styled.p`
  margin: 0;
  padding: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;
