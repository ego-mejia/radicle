import { Link } from '@tanstack/react-router';
import styled, { css } from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xxl};
`;

export const Heading = styled.h2`
  margin: 0 0 ${({ theme }) => theme.space.md};
  font-size: ${({ theme }) => theme.fontSize.xl};
`;

export const Steps = styled.ol`
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

const card = css`
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  padding: 18px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 16px;
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;

  &:hover {
    border-color: ${({ theme }) => theme.color.textMuted};
  }
  small,
  span {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.md};
  }
`;

export const Step = styled(Link)<{ $next: boolean }>`
  ${card};
  ${({ $next, theme }) =>
    $next &&
    css`
      border-color: ${theme.color.accentFill};
      box-shadow: 0 0 0 3px ${theme.color.accentSoft};
    `}
`;

export const Number = styled.span<{ $done: boolean; $next: boolean }>`
  width: 30px;
  height: 30px;
  border-radius: ${({ theme }) => theme.radius.full};
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  background: ${({ $done, $next, theme }) =>
    $done || $next ? theme.color.accentFill : theme.color.surface2};
  color: ${({ $done, $next, theme }) => ($done || $next ? theme.color.onAccent : theme.color.textMuted)};

  svg {
    width: 15px;
    height: 15px;
  }
`;

export const Bar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: ${({ theme }) => theme.space.md};
`;

export const Chips = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Chip = styled.button`
  min-height: 32px;
  padding: 0 12px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 600;
  cursor: pointer;

  &[aria-pressed='true'] {
    background: ${({ theme }) => theme.color.text};
    border-color: ${({ theme }) => theme.color.text};
    color: ${({ theme }) => theme.color.surface};
  }
`;

export const Grid = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

export const Card = styled(Link)`
  ${card};

  b {
    font-size: ${({ theme }) => theme.fontSize.lg};
    line-height: 1.3;
  }
`;

export const Label = styled.span`
  align-self: flex-start;
  padding: 2px 8px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.text} !important;
  font-size: ${({ theme }) => theme.fontSize.sm} !important;
  font-weight: 600;
`;
