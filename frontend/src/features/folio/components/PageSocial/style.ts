import styled, { css } from 'styled-components';

export const Bar = styled.section`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.md} 0`};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
`;

export const Reactions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.xs};
`;

const pill = css`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  min-height: 36px;
  padding: ${({ theme }) => `0 ${theme.space.md}`};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  cursor: pointer;

  &:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }

  svg {
    width: 16px;
    height: 16px;
  }
`;

export const Reaction = styled.button<{ $mine: boolean }>`
  ${pill};
  ${({ $mine, theme }) =>
    $mine &&
    css`
      background: ${theme.color.accentSoft};
      border-color: ${theme.color.accent};
    `}
`;

export const Count = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Toggles = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Toggle = styled.button<{ $on?: boolean }>`
  ${pill};
  ${({ $on, theme }) =>
    $on &&
    css`
      svg {
        fill: ${theme.color.accentFill};
        color: ${theme.color.accent};
      }
    `}
`;
