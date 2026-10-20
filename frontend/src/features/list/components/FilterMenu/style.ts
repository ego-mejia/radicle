import * as Popover from '@radix-ui/react-popover';
import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
`;

export const Badge = styled.span`
  display: inline-grid;
  place-items: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.onAccent};
  color: ${({ theme }) => theme.color.accentFill};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 700;
`;

export const Panel = styled(Popover.Content)`
  z-index: 50;
  width: min(420px, calc(100vw - 32px));
  max-height: min(70vh, 560px);
  overflow-y: auto;
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  box-shadow: 0 16px 36px rgba(17, 24, 39, 0.16);
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Section = styled.section`
  h3 {
    margin: 0 0 6px;
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.xs};
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
`;

export const Chips = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
`;

export const Chip = styled.button`
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  padding: 3px 10px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 999px;
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;

  &:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }

  &[aria-pressed='true'] {
    border-color: ${({ theme }) => theme.color.accent};
    background: ${({ theme }) => theme.color.accentSoft};
    color: ${({ theme }) => theme.color.accent};
    font-weight: 600;
  }
`;

export const Footer = styled.div`
  display: flex;
  justify-content: space-between;
  position: sticky;
  bottom: -12px;
  margin: 0 -12px -12px;
  padding: 8px 12px;
  border-top: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme }) => theme.color.surface};
`;

export const Active = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px 2px 10px;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.sm};

  button {
    all: unset;
    display: inline-grid;
    place-items: center;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    cursor: pointer;
  }

  button:hover {
    background: ${({ theme }) => theme.color.surface};
  }
`;
