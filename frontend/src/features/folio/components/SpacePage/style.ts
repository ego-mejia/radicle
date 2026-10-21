import styled, { css } from 'styled-components';

export const Page = styled.div`
  display: flex;
  flex-direction: column;
  min-height: 100%;
`;

export const Cover = styled.header<{ $image: string | null }>`
  background: ${({ theme }) => theme.color.accentSoft};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  ${({ $image }) =>
    $image &&
    css`
      background-image: url(${$image});
      background-size: cover;
      background-position: center;
    `}
`;

export const CoverInner = styled.div`
  max-width: 1280px;
  margin: 0 auto;
  padding: 48px ${({ theme }) => theme.space.xxl} ${({ theme }) => theme.space.xxl};
  display: flex;
  flex-wrap: wrap;
  align-items: flex-end;
  gap: ${({ theme }) => theme.space.xl};

  @media (max-width: 600px) {
    padding: ${({ theme }) => `${theme.space.xl} ${theme.space.lg}`};
  }
`;

export const Mark = styled.span`
  flex: 0 0 64px;
  width: 64px;
  height: 64px;
  border-radius: 16px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
  font-weight: 700;
  background: ${({ theme }) => theme.color.text};
  color: ${({ theme }) => theme.color.accentFill};
`;

export const Heading = styled.div`
  flex: 1 1 320px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};

  h1 {
    margin: 0;
    font-size: 34px;
    line-height: 1.15;
    letter-spacing: -0.02em;
  }

  p {
    margin: 0;
    font-size: 16px;
    line-height: 1.6;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Kind = styled.span`
  align-self: flex-start;
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.onAccent};
`;

export const Actions = styled.div`
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
  padding: ${({ theme }) => `${theme.space.xl} ${theme.space.xxl} 64px`};
  box-sizing: border-box;
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.xxl};

  @media (max-width: 600px) {
    padding: ${({ theme }) => `${theme.space.lg} ${theme.space.lg} 48px`};
  }
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
