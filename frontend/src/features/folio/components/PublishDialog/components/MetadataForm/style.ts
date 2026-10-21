import styled from 'styled-components';

export const Form = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Row = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: ${({ theme }) => theme.space.lg};
`;

export const Checks = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => `${theme.space.xs} ${theme.space.lg}`};
`;

export const Check = styled.label`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  min-height: 32px;
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Count = styled.span<{ $bad: boolean }>`
  align-self: flex-end;
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme, $bad }) => ($bad ? theme.color.danger : theme.color.textMuted)};
`;
