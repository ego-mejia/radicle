import styled from 'styled-components';
import type { Theme } from '../../../../styles/theme';

/** A space's tile color, stable per key, from the theme's status hues. */
function tileColor(theme: Theme, seed: string): string {
  const hues = [theme.color.accent, theme.color.info, theme.color.violet, theme.color.warning];
  let sum = 0;
  for (const ch of seed) sum += ch.charCodeAt(0);
  return hues[sum % hues.length] ?? theme.color.accent;
}

export const Tile = styled.span<{ $seed: string }>`
  flex: none;
  width: 22px;
  height: 22px;
  border-radius: ${({ theme }) => theme.radius.md};
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 700;
  color: ${({ theme, $seed }) => tileColor(theme, $seed)};
  background: ${({ theme, $seed }) => `${tileColor(theme, $seed)}22`};
`;

export const Count = styled.span`
  margin-left: auto;
  min-width: 20px;
  padding: 0 6px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.accentFill};
  color: ${({ theme }) => theme.color.onAccent};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 700;
  text-align: center;
`;

export const Key = styled.kbd`
  margin-left: auto;
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Action = styled.button`
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 6px 8px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.md};
  background: none;
  font: inherit;
  color: ${({ theme }) => theme.color.textMuted};
  text-align: left;
  cursor: pointer;

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.text};
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
    outline-offset: 2px;
  }

  svg {
    width: 16px;
    height: 16px;
    flex: none;
  }
`;
