import styled from 'styled-components';

export type Tone = 'neutral' | 'accent' | 'danger' | 'warning';

export const Pill = styled.span<{ $tone: Tone; $mono: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 20px;
  padding: 0 7px;
  border-radius: ${({ theme }) => theme.radius.full};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  white-space: nowrap;
  font-family: ${({ theme, $mono }) => ($mono ? theme.fonts.mono : 'inherit')};
  background: ${({ theme, $tone }) =>
    $tone === 'accent' ? theme.color.accentSoft : theme.color.surface2};
  color: ${({ theme, $tone }) =>
    $tone === 'accent'
      ? theme.color.accent
      : $tone === 'danger'
        ? theme.color.danger
        : $tone === 'warning'
          ? theme.color.warning
          : theme.color.textMuted};

  svg {
    width: 12px;
    height: 12px;
  }
`;

export const Key = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 500;
  color: ${({ theme }) => theme.color.accent};
  white-space: nowrap;
`;
