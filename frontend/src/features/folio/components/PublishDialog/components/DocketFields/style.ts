import styled from 'styled-components';

export const Box = styled.details`
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};

  summary {
    display: flex;
    justify-content: space-between;
    gap: ${({ theme }) => theme.space.sm};
    padding: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.md};
    cursor: pointer;
    font-size: ${({ theme }) => theme.fontSize.md};
    font-weight: 600;
  }
`;

export const Inner = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.md};
  padding: 0 ${({ theme }) => theme.space.md} ${({ theme }) => theme.space.md};
`;

export const Muted = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-weight: 400;
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
