import styled from 'styled-components';
import { CURSOR_FILL } from '../../lib/tour';

export const Layer = styled.div`
  position: fixed;
  inset: 0;
  z-index: 70;
  pointer-events: none;
`;

export const Spotlight = styled.div`
  position: fixed;
  border-radius: ${({ theme }) => theme.radius.md};
  outline: 3px solid ${({ theme }) => theme.color.accentFill};
  box-shadow:
    0 0 0 4px ${({ theme }) => theme.color.accent},
    0 0 0 9999px rgba(17, 24, 39, 0.32);
  transition:
    top 0.35s ease,
    left 0.35s ease,
    width 0.35s ease,
    height 0.35s ease;

  @media (prefers-reduced-motion: reduce) {
    transition: none;
  }
`;

// X and Y move with different easings, so the cursor travels along an arc.
export const CursorX = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  transition: transform 0.75s cubic-bezier(0.45, 0, 0.25, 1);

  @media (prefers-reduced-motion: reduce) {
    transition: none;
  }
`;

export const CursorY = styled.div`
  transition: transform 0.75s cubic-bezier(0.2, 0.7, 0.3, 1);

  @media (prefers-reduced-motion: reduce) {
    transition: none;
  }
`;

export const Cursor = styled.svg<{ $pressing: boolean }>`
  display: block;
  width: 30px;
  height: 34px;
  margin: -2px 0 0 -3px;
  transform: scale(${({ $pressing }) => ($pressing ? 0.82 : 1)});
  transform-origin: 3px 2px;
  transition: transform 0.12s ease;
  filter: drop-shadow(0 4px 8px ${({ theme }) => theme.color.accentFill})
    drop-shadow(0 1px 2px rgba(17, 24, 39, 0.35));

  path {
    fill: ${CURSOR_FILL};
    stroke: ${({ theme }) => theme.color.accent};
    stroke-width: 2;
    stroke-linejoin: round;
  }
`;

export const Card = styled.div`
  position: fixed;
  width: 320px;
  padding: 12px 14px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 14px;
  background: ${({ theme }) => theme.color.surface};
  box-shadow: 0 16px 40px rgba(17, 24, 39, 0.25);
  pointer-events: auto;

  p {
    margin: 4px 0 10px;
    line-height: 1.45;
  }
`;

export const CardHead = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;

  small {
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 600;
  }
`;

export const Stop = styled.button`
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 50%;
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;
`;

export const CardActions = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: 6px;
`;
