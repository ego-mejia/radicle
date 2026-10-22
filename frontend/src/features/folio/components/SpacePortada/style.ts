import { Link } from '@tanstack/react-router';
import styled, { css } from 'styled-components';

export const Bento = styled.div`
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: ${({ theme }) => theme.space.lg};

  @media (max-width: 900px) {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  @media (max-width: 640px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

const box = css`
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 20px 22px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 16px;
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
`;

export const Card = styled.section<{ $wide?: boolean; $tone?: 'lime' }>`
  ${box};
  grid-column: span ${({ $wide }) => ($wide ? 2 : 1)};
  ${({ $tone, theme }) =>
    $tone === 'lime' &&
    css`
      background: ${theme.color.accentSoft};
      border-color: ${theme.color.accentSoft};
    `}

  @media (max-width: 640px) {
    grid-column: auto;
  }
`;

export const Start = styled(Link)`
  ${box};
  padding: 0;
  overflow: hidden;
  grid-column: span 2;
  grid-row: span 2;
  text-decoration: none;

  &:hover {
    border-color: ${({ theme }) => theme.color.textMuted};
  }
  @media (max-width: 640px) {
    grid-column: auto;
    grid-row: auto;
  }
`;

export const Cover = styled.div`
  height: 200px;
  background: ${({ theme }) => theme.color.hero};
  color: ${({ theme }) => theme.color.accentFill};

  svg {
    width: 100%;
    height: 100%;
  }
`;

export const StartBody = styled.div`
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 20px 22px;

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xxl};
    line-height: 1.2;
    text-wrap: balance;
  }
  p {
    margin: 0;
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.lg};
    line-height: 1.55;
  }
`;

export const Tag = styled.span`
  align-self: flex-start;
  padding: 3px 8px;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  text-transform: uppercase;
`;

export const Head = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Kicker = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const More = styled(Link)`
  margin-left: auto;
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;
  color: ${({ theme }) => theme.color.accent};
  text-decoration: none;
`;

export const Inner = styled(Link)`
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 14px;
  border-radius: 12px;
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;

  span {
    font-size: ${({ theme }) => theme.fontSize.md};
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Title = styled(Link)`
  font-size: ${({ theme }) => theme.fontSize.lg};
  font-weight: 600;
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;

  &:hover {
    color: ${({ theme }) => theme.color.accent};
  }
`;

export const Row = styled(Link)`
  display: flex;
  align-items: baseline;
  gap: ${({ theme }) => theme.space.sm};
  padding: 8px 0;
  border-top: 1px solid ${({ theme }) => theme.color.surface2};
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 500;
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;

  small {
    margin-left: auto;
    white-space: nowrap;
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 400;
  }
  &:hover {
    color: ${({ theme }) => theme.color.accent};
  }
`;

export const Empty = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;
