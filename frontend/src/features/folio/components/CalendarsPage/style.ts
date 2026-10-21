import styled from 'styled-components';

export const Page = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  max-width: 1200px;
  margin: 0 auto;
  padding: ${({ theme }) => theme.space.xl} ${({ theme }) => theme.space.lg};
`;

export const Header = styled.header`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  h1 {
    margin: 0 auto 0 0;
    font-size: ${({ theme }) => theme.fontSize.xxl};
  }

  a {
    color: ${({ theme }) => theme.color.textMuted};
  }

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Tabs = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.xs};
`;
