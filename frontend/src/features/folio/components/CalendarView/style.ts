import styled, { css, type DefaultTheme } from 'styled-components';
import type { CalendarColor, EventCategory } from '../../../../services/api/folioCalendars';

/** Each category and calendar color as a theme token. */
const CATEGORY: Record<EventCategory, keyof DefaultTheme['color']> = {
  release: 'accent',
  event: 'info',
  vacation: 'violet',
  oncall: 'warning',
  other: 'textMuted',
};
const COLOR: Record<CalendarColor, keyof DefaultTheme['color']> = {
  blue: 'info',
  green: 'accent',
  purple: 'violet',
  orange: 'warning',
  red: 'danger',
  teal: 'catDone',
  gray: 'textMuted',
};

export const Wrap = styled.section<{ $color: CalendarColor }>`
  border: 1px solid ${({ theme }) => theme.color.border};
  border-top: 3px solid ${({ theme, $color }) => theme.color[COLOR[$color]]};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  overflow: hidden;
`;

export const Bar = styled.header`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.md};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  h3 {
    margin: 0 auto 0 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
    text-transform: capitalize;
  }

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Grid = styled.div<{ $mode: 'month' | 'week' }>`
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  ${({ $mode }) =>
    $mode === 'week' &&
    css`
      min-height: 280px;
    `}

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
`;

export const Weekday = styled.div`
  padding: ${({ theme }) => theme.space.xs} ${({ theme }) => theme.space.sm};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.xs};
  text-transform: uppercase;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  @media (max-width: 640px) {
    display: none;
  }
`;

export const Day = styled.div<{ $outside: boolean; $today: boolean }>`
  min-height: 92px;
  padding: ${({ theme }) => theme.space.xs};
  border-right: 1px solid ${({ theme }) => theme.color.border};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme, $outside }) => ($outside ? theme.color.surface2 : 'transparent')};
  display: flex;
  flex-direction: column;
  gap: 2px;

  &:nth-child(7n) {
    border-right: none;
  }
`;

export const DayNumber = styled.span<{ $today: boolean }>`
  align-self: flex-start;
  min-width: 22px;
  padding: 0 ${({ theme }) => theme.space.xs};
  border-radius: ${({ theme }) => theme.radius.full};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme, $today }) => ($today ? theme.color.onAccent : theme.color.textMuted)};
  background: ${({ theme, $today }) => ($today ? theme.color.accentFill : 'transparent')};
  text-align: center;
`;

export const Chip = styled.button<{ $category: EventCategory | 'milestone' }>`
  display: block;
  width: 100%;
  padding: 1px ${({ theme }) => theme.space.xs};
  border: none;
  border-left: 3px solid
    ${({ theme, $category }) =>
      $category === 'milestone' ? theme.color.text : theme.color[CATEGORY[$category]]};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.xs};
  text-align: left;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  cursor: ${({ onClick }) => (onClick ? 'pointer' : 'default')};

  time {
    color: ${({ theme }) => theme.color.textMuted};
    margin-right: ${({ theme }) => theme.space.xs};
  }
`;

export const Legend = styled.ul`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.md};
  margin: 0;
  padding: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.md};
  list-style: none;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.xs};
`;

export const Swatch = styled.span<{ $category: EventCategory | 'milestone' }>`
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: ${({ theme }) => theme.space.xs};
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme, $category }) =>
    $category === 'milestone' ? theme.color.text : theme.color[CATEGORY[$category]]};
`;

export const Muted = styled.p`
  margin: 0;
  padding: ${({ theme }) => theme.space.md};
  color: ${({ theme }) => theme.color.textMuted};
`;
