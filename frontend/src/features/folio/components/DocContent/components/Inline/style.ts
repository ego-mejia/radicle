import styled, { css } from 'styled-components';

export type Tone = 'accent' | 'warning' | 'danger' | 'muted';

/** A 1px border in the tone's theme color. */
export const toned = css<{ $tone: Tone }>`
  border: 1px solid
    ${({ theme, $tone }) =>
      ({
        accent: theme.color.accent,
        warning: theme.color.warning,
        danger: theme.color.danger,
        muted: theme.color.textMuted,
      })[$tone]};
`;

export const Code = styled.code`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: 0.88em;
  background: ${({ theme }) => theme.color.surface2};
  padding: 2px 6px;
  border-radius: ${({ theme }) => theme.radius.sm};
`;

export const Status = styled.span<{ $tone: Tone }>`
  ${toned};
  display: inline-block;
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  line-height: 1.6;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 0 6px;
  border-radius: ${({ theme }) => theme.radius.sm};
`;

export const Mention = styled.span`
  color: ${({ theme }) => theme.color.accent};
  font-weight: 600;
`;
