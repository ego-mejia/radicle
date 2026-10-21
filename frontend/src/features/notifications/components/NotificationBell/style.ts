import * as Popover from '@radix-ui/react-popover';
import styled, { css } from 'styled-components';

export const Trigger = styled.button`
  position: relative;
  display: grid;
  place-items: center;
  width: 36px;
  height: 36px;
  flex: none;
  padding: 0;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;

  svg {
    width: 18px;
    height: 18px;
  }

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const Count = styled.span`
  position: absolute;
  top: -6px;
  right: -6px;
  min-width: 18px;
  height: 18px;
  padding: 0 ${({ theme }) => theme.space.xs};
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.accentFill};
  color: ${({ theme }) => theme.color.onAccent};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 700;
  line-height: 18px;
  text-align: center;
`;

export const Panel = styled(Popover.Content)`
  width: min(380px, calc(100vw - 32px));
  max-height: min(520px, 70vh);
  display: flex;
  flex-direction: column;
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.18);
  z-index: 60;
  overflow: hidden;
`;

export const Head = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.lg}`};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }
`;

export const MarkAll = styled.button`
  border: 0;
  background: none;
  padding: 0;
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.accent};
  cursor: pointer;

  &:disabled {
    color: ${({ theme }) => theme.color.textMuted};
    cursor: default;
  }
`;

export const Empty = styled.p`
  margin: 0;
  padding: ${({ theme }) => theme.space.xl};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
  text-align: center;
`;

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  overflow-y: auto;
`;

export const Item = styled.button<{ $unread: boolean }>`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
  width: 100%;
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.lg}`};
  border: 0;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  background: none;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;

  ${({ $unread, theme }) =>
    $unread &&
    css`
      background: ${theme.color.accentSoft};
    `}

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const Dot = styled.span`
  flex: 0 0 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.accent};
`;

export const Text = styled.span`
  display: flex;
  flex-direction: column;
  gap: 2px;
  min-width: 0;
  font-size: ${({ theme }) => theme.fontSize.md};

  span {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const When = styled.span`
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
