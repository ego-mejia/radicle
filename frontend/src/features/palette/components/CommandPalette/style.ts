import * as Dialog from '@radix-ui/react-dialog';
import styled from 'styled-components';

export const Overlay = styled(Dialog.Overlay)`
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  z-index: 80;
`;

export const Content = styled(Dialog.Content)`
  position: fixed;
  top: 12vh;
  left: 50%;
  transform: translateX(-50%);
  width: min(620px, calc(100vw - 32px));
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.25);
  z-index: 81;
  overflow: hidden;

  .sr-only {
    position: absolute;
    width: 1px;
    height: 1px;
    overflow: hidden;
    clip: rect(0 0 0 0);
  }
`;

export const Input = styled.input`
  border: 0;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  padding: ${({ theme }) => theme.space.lg};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.lg};
  background: transparent;
  color: ${({ theme }) => theme.color.text};
  outline: none;
`;

export const List = styled.div`
  overflow: auto;
  padding: ${({ theme }) => theme.space.sm};
`;

export const Group = styled.div`
  padding: 6px 10px 2px;
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
  text-transform: uppercase;
  letter-spacing: 0.04em;
`;

export const Item = styled.div<{ $active: boolean }>`
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme, $active }) => ($active ? theme.color.accentSoft : 'transparent')};
  cursor: pointer;

  svg {
    width: 16px;
    height: 16px;
    color: ${({ theme }) => theme.color.textMuted};
    flex-shrink: 0;
  }

  span {
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;

export const Hint = styled.small`
  color: ${({ theme }) => theme.color.textMuted};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-variant-ligatures: none;
  max-width: 45%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

export const Empty = styled.p`
  margin: ${({ theme }) => theme.space.md};
  color: ${({ theme }) => theme.color.textMuted};
`;
