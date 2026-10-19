import styled, { css } from 'styled-components';
import { classificationToken, type Quadrant } from '../../../../lib/inbox';
import type { Classification } from '../../../../services/api/types';

export const Wrap = styled.div`
  display: grid;
  grid-template-columns: minmax(0, 1fr) 260px;
  gap: ${({ theme }) => theme.space.lg};

  @media (max-width: 900px) {
    grid-template-columns: 1fr;
  }
`;

export const Matrix = styled.div`
  display: grid;
  grid-template-columns: 24px 1fr;
  grid-template-rows: 1fr 24px;
  gap: 4px;
`;

export const AxisY = styled.div`
  writing-mode: vertical-rl;
  transform: rotate(180deg);
  text-align: center;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const AxisX = styled.div`
  grid-column: 2;
  text-align: center;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Grid = styled.div`
  position: relative;
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  grid-template-rows: repeat(5, minmax(72px, 1fr));
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  overflow: hidden;
  background: ${({ theme }) => theme.color.surface};
`;

const tint = css<{ $quadrant: Quadrant }>`
  background: ${({ theme, $quadrant }) =>
    $quadrant === 'quick_wins'
      ? theme.color.accentSoft
      : $quadrant === 'not_worth'
        ? theme.color.surface2
        : 'transparent'};
`;

export const Cell = styled.div<{ $quadrant: Quadrant; $over: boolean }>`
  ${tint}
  display: flex;
  flex-wrap: wrap;
  align-content: center;
  justify-content: center;
  gap: 4px;
  padding: 4px;
  border: 1px solid ${({ theme }) => theme.color.border};
  outline: ${({ theme, $over }) => ($over ? `2px dashed ${theme.color.accent}` : 'none')};
  outline-offset: -3px;
  z-index: 1;
`;

export const Label = styled.span`
  align-self: start;
  justify-self: start;
  margin: 4px 6px;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.xs};
  text-transform: uppercase;
  letter-spacing: 0.04em;
  pointer-events: none;
  z-index: 2;
`;

export const Dot = styled.button<{ $kind: Classification; $dragging: boolean }>`
  border-radius: 50%;
  border: 2px solid ${({ theme }) => theme.color.surface};
  background: ${({ theme, $kind }) => theme.color[classificationToken($kind)]};
  opacity: ${({ $dragging }) => ($dragging ? 0.4 : 0.9)};
  cursor: grab;
  padding: 0;
  flex: none;
`;

export const Side = styled.aside`
  display: flex;
  flex-direction: column;
  gap: 6px;

  h3 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }

  p {
    margin: 0;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Unscored = styled.div`
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: ${({ theme }) => theme.fontSize.md};

  b {
    font-family: ${({ theme }) => theme.fonts.mono};
    font-weight: 500;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
