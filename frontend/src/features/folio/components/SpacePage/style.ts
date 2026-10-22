import styled from 'styled-components';

export const Page = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 100%;
`;

export const Actions = styled.div`
  padding-top: ${({ theme }) => theme.space.xl};
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Body = styled.div`
  width: 100%;
  max-width: 1280px;
  margin: 0 auto;
  padding: ${({ theme }) => theme.space.xl} 0 64px;
  box-sizing: border-box;
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.xxl};
`;

export const Side = styled.aside`
  flex: 0 1 300px;
  min-width: 240px;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const SideTitle = styled.h2`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Main = styled.section`
  flex: 1 1 420px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const SectionTitle = styled.h2`
  margin: 0;
  font-size: 17px;
  font-weight: 700;
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Posts = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 18px;

  &:empty {
    display: none;
  }

  li + li {
    border-top: 1px solid ${({ theme }) => theme.color.surface2};
  }

  a {
    display: flex;
    gap: ${({ theme }) => theme.space.sm};
    padding: ${({ theme }) => `${theme.space.lg} ${theme.space.xl}`};
    font-size: ${({ theme }) => theme.fontSize.lg};
    font-weight: 600;
    color: ${({ theme }) => theme.color.text};
    text-decoration: none;
  }

  a:hover {
    color: ${({ theme }) => theme.color.accent};
  }
`;

export const SideLink = styled.div`
  margin-bottom: ${({ theme }) => theme.space.md};

  a {
    display: flex;
    align-items: center;
    gap: ${({ theme }) => theme.space.sm};
    color: ${({ theme }) => theme.color.text};
    font-size: ${({ theme }) => theme.fontSize.md};
    text-decoration: none;
  }

  a:hover {
    color: ${({ theme }) => theme.color.accent};
  }

  svg {
    width: 16px;
    height: 16px;
  }
`;
