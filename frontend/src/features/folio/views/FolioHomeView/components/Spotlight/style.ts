import styled, { css } from 'styled-components';

export type Tone = 'accent' | 'plain';

export const Card = styled.article<{ $tone: Tone }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.xxl};
  border-radius: ${({ theme }) => theme.radius.lg};
  ${({ $tone, theme }) =>
    $tone === 'accent'
      ? css`
          background: ${theme.color.accentFill};
          color: ${theme.color.onAccent};
        `
      : css`
          background: ${theme.color.surface};
          color: ${theme.color.text};
          border: 1px solid ${theme.color.border};
        `}
`;

export const Label = styled.span<{ $tone: Tone }>`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 500;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: ${({ $tone, theme }) => ($tone === 'accent' ? 'inherit' : theme.color.accent)};
`;

export const Title = styled.h2`
  margin: 0;
  font-size: 22px;
  line-height: 1.25;
  letter-spacing: -0.01em;
`;

export const Text = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.lg};
  line-height: 1.55;
`;

export const More = styled.a`
  align-self: flex-start;
  color: inherit;
  font-weight: 600;
  font-size: 14px;
`;
