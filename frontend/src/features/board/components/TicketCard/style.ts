import styled, { css, keyframes } from 'styled-components';

// A moved card glows once in the accent; one that reached done glows brighter, grows a
// little and a shine sweeps across it.
const glow = (color: string, spread: number) => keyframes`
  0% { box-shadow: 0 0 0 0 ${color}; }
  35% { box-shadow: 0 0 0 ${spread / 3}px ${color}, 0 0 ${spread}px ${color}; }
  100% { box-shadow: 0 0 0 0 transparent; }
`;
const pop = keyframes`
  0%, 100% { transform: scale(1); }
  30% { transform: scale(1.04); }
`;
const sweep = keyframes`
  from { transform: translateX(-120%) skewX(-20deg); }
  to { transform: translateX(220%) skewX(-20deg); }
`;

const flashes = {
  moved: css`
    animation: ${({ theme }) => glow(theme.color.accent, 14)} 0.8s ease-out;
  `,
  done: css`
    animation:
      ${({ theme }) => glow(theme.color.accentFill, 26)} 1.3s ease-out,
      ${pop} 0.6s ease-out;

    &::after {
      content: '';
      position: absolute;
      inset: 0;
      width: 45%;
      pointer-events: none;
      background: linear-gradient(
        90deg,
        transparent,
        ${({ theme }) => theme.color.accentFill},
        transparent
      );
      opacity: 0.55;
      animation: ${sweep} 0.9s ease-out forwards;
    }
  `,
};

// Jira-like cards: white tiles on a grey column, a soft shadow instead of a border.
const lift = css`
  box-shadow: ${({ theme }) =>
    theme.mode === 'dark'
      ? `0 0 0 1px ${theme.color.border}`
      : '0 1px 1px rgba(9, 30, 66, 0.25), 0 0 1px rgba(9, 30, 66, 0.31)'};
`;

export const Card = styled.div<{
  $draft: boolean;
  $dragging: boolean;
  $overlay: boolean;
  $dropTarget: boolean;
  $flash?: 'moved' | 'done';
}>`
  position: relative;
  overflow: ${({ $flash }) => ($flash === 'done' ? 'hidden' : 'visible')};
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 12px 8px;
  background: ${({ theme }) => theme.color.surface};
  border-radius: ${({ theme }) => theme.radius.sm};
  ${lift};
  outline: ${({ theme, $draft }) => ($draft ? `1px dashed ${theme.color.textMuted}` : 'none')};
  outline-offset: -1px;
  cursor: grab;
  opacity: ${({ $dragging }) => ($dragging ? 0.35 : 1)};
  transform: ${({ $overlay }) => ($overlay ? 'rotate(2deg)' : 'none')};
  ${({ $overlay }) =>
    $overlay &&
    css`
      box-shadow: 0 12px 28px rgba(9, 30, 66, 0.3);
    `}
  touch-action: none;
  user-select: none;
  transition:
    background 0.1s,
    box-shadow 0.1s;

  &::before {
    content: '';
    position: absolute;
    left: 0;
    right: 0;
    top: -5px;
    height: 2px;
    border-radius: 2px;
    background: ${({ theme, $dropTarget }) => ($dropTarget ? theme.color.accent : 'transparent')};
  }

  &:hover {
    background: ${({ theme }) => (theme.mode === 'dark' ? theme.color.surface2 : '#F7F8F9')};
  }

  ${({ $flash }) => $flash && flashes[$flash]}

  @media (prefers-reduced-motion: reduce) {
    animation: none;
    &::after {
      animation: none;
      opacity: 0;
    }
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
    outline-offset: 1px;
  }
`;

export const Title = styled.div`
  font-size: ${({ theme }) => theme.fontSize.md};
  line-height: 1.4;
  overflow-wrap: anywhere;
`;

export const Labels = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
`;

export const Tag = styled.span`
  padding: 0 5px;
  border-radius: 3px;
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: 11px;
  font-weight: 700;
  line-height: 18px;
  text-transform: uppercase;
  letter-spacing: 0.02em;
`;

export const Bottom = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  min-height: 24px;
`;

export const Key = styled.span<{ $done: boolean }>`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  color: ${({ theme }) => theme.color.textMuted};
  text-decoration: ${({ $done }) => ($done ? 'line-through' : 'none')};
`;

export const Spacer = styled.span`
  flex: 1;
`;

export const Pill = styled.span<{ $danger?: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 0 6px;
  border-radius: 999px;
  background: ${({ theme, $danger }) => ($danger ? theme.color.danger : theme.color.surface2)};
  color: ${({ theme, $danger }) => ($danger ? theme.color.surface : theme.color.textMuted)};
  font-size: 11px;
  font-weight: 600;
  line-height: 18px;

  svg {
    width: 11px;
    height: 11px;
  }
`;

export const Meta = styled.span<{ $danger?: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme, $danger }) => ($danger ? theme.color.danger : theme.color.textMuted)};

  svg {
    width: 12px;
    height: 12px;
  }
`;

export const Blocked = styled.span`
  display: inline-flex;
  color: ${({ theme }) => theme.color.danger};

  svg {
    width: 14px;
    height: 14px;
  }
`;
