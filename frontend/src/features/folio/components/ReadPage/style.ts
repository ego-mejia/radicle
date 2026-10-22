import styled, { css } from 'styled-components';
import { darkTheme } from '../../../../styles/theme';

export const Page = styled.div`
  background: ${({ theme }) => theme.color.surface};
  min-height: 100%;
`;

export const Bar = styled.div`
  max-width: 1280px;
  margin: 0 auto;
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.xxl}`};
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};

  @media (max-width: 600px) {
    padding: ${({ theme }) => `${theme.space.sm} ${theme.space.lg}`};
  }
`;

export const Crumbs = styled.nav`
  flex: 1 1 240px;
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

export const Actions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};

  a,
  button {
    display: inline-flex;
    align-items: center;
    gap: ${({ theme }) => theme.space.sm};
    min-height: 40px;
    padding: 0 14px;
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.lg};
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
    font: inherit;
    font-size: ${({ theme }) => theme.fontSize.md};
    font-weight: 500;
    text-decoration: none;
    cursor: pointer;
  }
  /* The page's ⋯ menu, an icon with only a label: square, or the padding above leaves its
     icon a dot. Menus with text (Export) keep their width. */
  button[aria-haspopup='menu'][aria-label] {
    justify-content: center;
    width: 40px;
    padding: 0;
  }

  svg {
    width: 16px;
    height: 16px;
  }
`;

// The cover band is dark in both themes, like the magazine design.
export const Cover = styled.div<{ $image: string | null }>`
  height: 240px;
  background: ${darkTheme.color.bg};
  border-top: 3px solid ${({ theme }) => theme.color.accentFill};
  color: ${({ theme }) => theme.color.accentFill};
  overflow: hidden;
  svg {
    display: block;
    width: 100%;
    height: 100%;
  }
  ${({ $image }) =>
    $image &&
    css`
      background-image: url(${$image});
      background-size: cover;
      background-position: center;
    `}

  @media (max-width: 600px) {
    height: 140px;
  }
`;

export const Layout = styled.div`
  max-width: 1180px;
  margin: 0 auto;
  padding: 48px ${({ theme }) => theme.space.xxl} 80px;
  display: flex;
  flex-wrap: wrap;
  gap: 48px;
  align-items: flex-start;
  justify-content: center;

  @media (max-width: 600px) {
    padding: ${({ theme }) => `${theme.space.xl} ${theme.space.lg} 64px`};
  }
`;

export const Article = styled.article`
  flex: 0 1 720px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 22px;
`;

export const Aside = styled.aside`
  flex: 1 1 220px;
  max-width: 280px;
  min-width: 0;
  position: sticky;
  top: 88px;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xl};

  @media (max-width: 1040px) {
    position: static;
    max-width: none;
  }
`;

export const DraftNote = styled.p`
  margin: 0;
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.lg}`};
  border: 1px dashed ${({ theme }) => theme.color.warning};
  border-radius: ${({ theme }) => theme.radius.lg};
  color: ${({ theme }) => theme.color.warning};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Tag = styled.span`
  align-self: flex-start;
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: ${({ theme }) => theme.color.accentSoft};
  /* text, not onAccent: in dark mode accentSoft is dark too and onAccent vanished on it. */
  color: ${({ theme }) => theme.color.text};
  padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
  border-radius: ${({ theme }) => theme.radius.md};
`;

export const Title = styled.h1`
  margin: 0;
  font-size: 46px;
  line-height: 1.08;
  letter-spacing: -0.025em;

  @media (max-width: 600px) {
    font-size: 34px;
  }
`;

export const Lead = styled.p`
  margin: 0;
  font-size: 21px;
  line-height: 1.55;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Byline = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  padding-bottom: 22px;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  font-size: 14px;
  color: ${({ theme }) => theme.color.textMuted};

  strong {
    color: ${({ theme }) => theme.color.text};
    font-weight: 600;
  }
`;
