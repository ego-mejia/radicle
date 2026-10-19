import styled from 'styled-components';

export const Checks = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.lg};

  label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }
`;

export const Help = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
