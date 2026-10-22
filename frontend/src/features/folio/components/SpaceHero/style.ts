import { Link } from '@tanstack/react-router';
import styled, { css } from 'styled-components';

const gutter = css`
  padding-left: max(24px, env(safe-area-inset-left, 0px));
  padding-right: max(24px, env(safe-area-inset-right, 0px));
`;

export const Hero = styled.section`
  ${gutter};
  padding-top: ${({ theme }) => theme.space.lg};
  padding-bottom: 28px;
  background: ${({ theme }) => theme.color.hero};
  color: ${({ theme }) => theme.color.heroText};
  display: flex;
  flex-direction: column;
  gap: 18px;
  /* Edge to edge across the content column: cancel the shell's top padding and reach both
     sides of the column (100cqw is the column, measured by FolioPage's container). */
  margin: -${({ theme }) => theme.space.xl} calc((100% - 100cqw) / 2) 0;

  @media (max-width: 600px) {
    margin-top: -${({ theme }) => theme.space.lg};
  }
`;

export const Top = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Kicker = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.accentFill};
`;

export const Crumbs = styled.nav`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.md};

  a {
    color: ${({ theme }) => theme.color.heroMuted};
    text-decoration: none;
  }
  a:hover {
    color: ${({ theme }) => theme.color.heroText};
  }
  > span {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Here = styled.span`
  color: ${({ theme }) => theme.color.accentFill} !important;
  font-weight: 600;
`;

export const Actions = styled.div`
  margin-left: auto;
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
`;

const button = css`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  min-height: 40px;
  padding: 0 14px;
  border-radius: ${({ theme }) => theme.radius.lg};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;
  text-decoration: none;
  cursor: pointer;

  svg {
    width: 16px;
    height: 16px;
  }
`;

const ghost = css`
  ${button};
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.08);
  color: ${({ theme }) => theme.color.heroText};

  &:hover {
    border-color: rgba(255, 255, 255, 0.4);
  }
`;

export const Ghost = styled.button`
  ${ghost};
`;

export const GhostLink = styled(Link)`
  ${ghost};
`;

export const Primary = styled.button`
  ${button};
  border: 1px solid ${({ theme }) => theme.color.accentFill};
  background: ${({ theme }) => theme.color.accentFill};
  color: ${({ theme }) => theme.color.onAccent};
`;

export const Middle = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  gap: ${({ theme }) => theme.space.md};

  h1 {
    margin: 0;
    font-size: clamp(32px, 5vw, 46px);
    line-height: 1.05;
    letter-spacing: -0.02em;
    text-wrap: balance;
  }
  p {
    margin: 0;
    max-width: 600px;
    font-size: ${({ theme }) => theme.fontSize.lg};
    line-height: 1.6;
    color: ${({ theme }) => theme.color.heroMuted};
  }
`;

export const Stats = styled.div`
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  align-items: center;
  gap: ${({ theme }) => theme.space.lg};
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.heroMuted};

  b {
    color: ${({ theme }) => theme.color.heroText};
  }
`;

export const Search = styled.form`
  width: 100%;
  max-width: 620px;
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 52px;
  margin-top: ${({ theme }) => theme.space.xs};
  padding: 0 8px 0 18px;
  border-radius: 14px;
  background: ${({ theme }) => theme.color.heroText};
  color: ${({ theme }) => theme.color.textMuted};
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);

  > svg {
    width: 18px;
    height: 18px;
    flex: none;
  }
  input {
    flex: 1;
    min-width: 0;
    border: 0;
    outline: 0;
    background: none;
    font: inherit;
    font-size: ${({ theme }) => theme.fontSize.lg};
    color: ${({ theme }) => theme.color.hero};
  }
  button {
    min-height: 38px;
    padding: 0 14px;
    border: 0;
    border-radius: ${({ theme }) => theme.radius.lg};
    background: ${({ theme }) => theme.color.hero};
    color: ${({ theme }) => theme.color.heroText};
    font: inherit;
    font-size: ${({ theme }) => theme.fontSize.md};
    font-weight: 600;
    cursor: pointer;
  }
  &:focus-within {
    outline: 2px solid ${({ theme }) => theme.color.accentFill};
    outline-offset: 2px;
  }
`;

export const Pills = styled.nav`
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Pill = styled(Link)<{ $on: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 34px;
  padding: 0 14px;
  border-radius: ${({ theme }) => theme.radius.full};
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;
  text-decoration: none;
  border: 1px solid
    ${({ $on, theme }) => ($on ? theme.color.accentFill : 'rgba(255, 255, 255, 0.14)')};
  background: ${({ $on, theme }) => ($on ? theme.color.accentFill : 'rgba(255, 255, 255, 0.08)')};
  color: ${({ $on, theme }) => ($on ? theme.color.onAccent : theme.color.heroText)};

  small {
    font-family: ${({ theme }) => theme.fonts.mono};
    font-size: ${({ theme }) => theme.fontSize.xs};
    opacity: 0.75;
  }
  &:hover {
    border-color: ${({ $on, theme }) => ($on ? theme.color.accentFill : 'rgba(255, 255, 255, 0.4)')};
  }
`;
