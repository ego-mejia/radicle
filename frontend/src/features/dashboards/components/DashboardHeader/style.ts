import styled from 'styled-components';

export const Bar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  margin-bottom: ${({ theme }) => theme.space.lg};

  h1 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xxl};
  }
`;

export const Muted = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Spacer = styled.span`
  flex: 1;
`;
