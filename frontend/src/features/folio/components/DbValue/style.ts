import styled, { type DefaultTheme } from 'styled-components';
import type { ChoiceColor } from '../../../../services/api/folioDatabases';

/** A choice's color in the theme's tokens. */
export function choiceColor(theme: DefaultTheme, color: ChoiceColor): string {
  const tokens: Record<ChoiceColor, string> = {
    grey: theme.color.textMuted,
    blue: theme.color.info,
    green: theme.color.accent,
    yellow: theme.color.warning,
    red: theme.color.danger,
    purple: theme.color.violet,
  };
  return tokens[color];
}

export const Chip = styled.span<{ $color: ChoiceColor }>`
  display: inline-flex;
  align-items: center;
  height: 20px;
  padding: 0 8px;
  border-radius: ${({ theme }) => theme.radius.full};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  white-space: nowrap;
  color: ${({ theme, $color }) => choiceColor(theme, $color)};
  background: ${({ theme }) => theme.color.surface2};
  border: 1px solid currentColor;
`;

export const Chips = styled.span`
  display: inline-flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.xs};
`;

export const Num = styled.span`
  font-variant-numeric: tabular-nums;
`;

export const Person = styled.span`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
`;
