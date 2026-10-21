import styled, { css } from 'styled-components';

export const Groups = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xl};
  margin-top: ${({ theme }) => theme.space.xl};
`;

export const Group = styled.section`
  h2 {
    display: flex;
    align-items: center;
    gap: ${({ theme }) => theme.space.sm};
    margin: 0 0 ${({ theme }) => theme.space.sm};
    font-size: ${({ theme }) => theme.fontSize.lg};
  }

  ul {
    list-style: none;
    margin: 0;
    padding: 0;
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.lg};
    background: ${({ theme }) => theme.color.surface};
  }
`;

export const Count = styled.span`
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 500;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Row = styled.li<{ $done: boolean }>`
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.lg}`};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  &:last-child {
    border-bottom: 0;
  }

  input {
    width: 18px;
    height: 18px;
    accent-color: ${({ theme }) => theme.color.accent};
  }

  ${({ $done, theme }) =>
    $done &&
    css`
      color: ${theme.color.textMuted};
      ${Text} {
        text-decoration: line-through;
      }
    `}
`;

export const Text = styled.span`
  flex: 1 1 240px;
  min-width: 0;
  font-size: ${({ theme }) => theme.fontSize.lg};
`;

export const Page = styled.a`
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.accent};
`;

export const Due = styled.span<{ $late: boolean }>`
  min-width: 96px;
  text-align: right;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ $late, theme }) => ($late ? theme.color.danger : theme.color.textMuted)};
`;
