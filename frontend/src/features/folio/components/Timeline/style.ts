import styled, { type DefaultTheme } from 'styled-components';

type Status = 'done' | 'in_progress' | 'planned' | undefined;

const tone = (theme: DefaultTheme, status: Status) =>
  status === 'done'
    ? theme.color.accent
    : status === 'in_progress'
      ? theme.color.info
      : theme.color.textMuted;

export const Line = styled.ol`
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: minmax(140px, 1fr);
  gap: ${({ theme }) => theme.space.lg};
  margin: 0;
  padding: ${({ theme }) => theme.space.sm} 0;
  list-style: none;
  overflow-x: auto;
`;

export const Item = styled.li<{ $status: Status }>`
  position: relative;
  display: grid;
  align-content: start;
  gap: ${({ theme }) => theme.space.xs};
  padding-top: ${({ theme }) => theme.space.xl};

  /* The line, from this milestone to the next. */
  &::before {
    content: '';
    position: absolute;
    top: 7px;
    left: 0;
    right: ${({ theme }) => `-${theme.space.lg}`};
    border-top: 2px ${({ $status }) => ($status === 'planned' ? 'dashed' : 'solid')}
      ${({ theme }) => theme.color.border};
  }

  &:last-child::before {
    right: 0;
  }

  --tone: ${({ theme, $status }) => tone(theme, $status)};
`;

export const Dot = styled.span`
  position: absolute;
  top: 0;
  left: 0;
  width: 16px;
  height: 16px;
  border: 2px solid var(--tone);
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface};
`;

export const Date = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-family: ${({ theme }) => theme.fonts.mono};
`;

export const Title = styled.strong`
  color: ${({ theme }) => theme.color.text};
`;

export const Status = styled.span<{ $status: Status }>`
  justify-self: start;
  color: ${({ theme, $status }) => tone(theme, $status)};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  text-transform: uppercase;
`;

export const Text = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
`;
