import styled from 'styled-components';

export const Page = styled.div`
  background: ${({ theme }) => theme.color.surface};
  min-height: 100%;
`;

export const Bar = styled.div`
  max-width: 1600px;
  margin: 0 auto;
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.xxl}`};
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};

  @media (max-width: 600px) {
    padding: ${({ theme }) => `${theme.space.sm} ${theme.space.lg}`};
  }
`;

export const Crumbs = styled.nav`
  flex: 1;
  min-width: 0;
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
  font-size: 14px;

  span {
    display: inline-flex;
    gap: ${({ theme }) => theme.space.sm};
  }

  a,
  span > span {
    color: ${({ theme }) => theme.color.textMuted};
    text-decoration: none;
  }

  a:hover {
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Body = styled.div`
  max-width: 1600px;
  margin: 0 auto;
  padding: ${({ theme }) => `${theme.space.lg} ${theme.space.xxl} ${theme.space.xxl}`};

  @media (max-width: 600px) {
    padding: ${({ theme }) => theme.space.lg};
  }
`;

export const Title = styled.h1`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  margin: 0 0 ${({ theme }) => theme.space.lg};
  font-size: 32px;
  letter-spacing: -0.02em;

  svg {
    width: 28px;
    height: 28px;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Board = styled.div`
  position: relative;
  height: calc(100vh - 220px);
  min-height: 420px;
`;
