import styled, { css } from 'styled-components';

export const Item = styled.div<{ $done: boolean }>`
  display: flex;
  align-items: baseline;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => `${theme.space.xs} ${theme.space.md}`};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface2};

  input {
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
  flex: 1;
  min-width: 0;
`;

export const Who = styled.span`
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;
  color: ${({ theme }) => theme.color.accent};
`;

export const When = styled.span<{ $late: boolean }>`
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ $late, theme }) => ($late ? theme.color.danger : theme.color.textMuted)};
`;
