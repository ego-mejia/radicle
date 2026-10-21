import styled from 'styled-components';
import { darkTheme } from '../../../../../../styles/theme';

export const Card = styled.a`
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  text-decoration: none;
  color: ${({ theme }) => theme.color.text};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};

  &:hover h2 {
    text-decoration: underline;
  }
`;

/** The dark cover with Radicle's roots, or the page's own cover image. */
export const Cover = styled.div`
  height: 260px;
  background: ${darkTheme.color.bg};
  color: ${({ theme }) => theme.color.accentFill};

  svg,
  img {
    display: block;
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
`;

export const Body = styled.div`
  padding: ${({ theme }) => theme.space.xxl};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Tag = styled.span`
  align-self: flex-start;
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};
  padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
  border-radius: ${({ theme }) => theme.radius.md};
`;

export const Title = styled.h2`
  margin: 0;
  font-size: 34px;
  line-height: 1.15;
  letter-spacing: -0.02em;
`;

export const Description = styled.p`
  margin: 0;
  font-size: 16px;
  line-height: 1.6;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Meta = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;
