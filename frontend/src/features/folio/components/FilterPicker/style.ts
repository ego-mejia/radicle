import * as Popover from '@radix-ui/react-popover';
import styled from 'styled-components';

export const Trigger = styled.button<{ $active: boolean }>`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  min-height: 38px;
  padding: 0 ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme, $active }) => ($active ? theme.color.text : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme, $active }) => ($active ? theme.color.text : theme.color.surface)};
  color: ${({ theme, $active }) => ($active ? theme.color.bg : theme.color.text)};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  font-weight: 500;
  cursor: pointer;

  svg {
    width: 14px;
    height: 14px;
    color: ${({ theme, $active }) => ($active ? theme.color.accentFill : theme.color.textMuted)};
  }

  &[data-state='open'] {
    box-shadow: 0 0 0 3px ${({ theme }) => theme.color.surface2};
  }
`;

export const Content = styled(Popover.Content)`
  display: flex;
  flex-direction: column;
  gap: 2px;
  width: min(300px, calc(100vw - 32px));
  max-height: min(420px, 70vh);
  overflow-y: auto;
  padding: ${({ theme }) => theme.space.sm};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 14px;
  box-shadow: 0 16px 40px rgba(17, 24, 39, 0.16);
  z-index: 60;
`;

export const Search = styled.input`
  min-height: 38px;
  margin-bottom: ${({ theme }) => theme.space.xs};
  padding: 0 ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
`;

export const Label = styled.span`
  padding: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.md} 2px;
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Option = styled.button<{ $on: boolean }>`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  min-height: 36px;
  padding: 0 ${({ theme }) => theme.space.md};
  border: 0;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme, $on }) => ($on ? theme.color.accentSoft : 'none')};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-weight: ${({ $on }) => ($on ? 600 : 400)};
  text-align: left;
  cursor: pointer;

  &:hover {
    background: ${({ theme, $on }) => ($on ? theme.color.accentSoft : theme.color.surface2)};
  }
`;

export const Box = styled.span<{ $on: boolean }>`
  display: grid;
  place-items: center;
  flex: none;
  width: 16px;
  height: 16px;
  border: 1.5px solid ${({ theme, $on }) => ($on ? theme.color.accent : theme.color.textMuted)};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme, $on }) => ($on ? theme.color.accent : 'none')};

  svg {
    width: 11px;
    height: 11px;
    color: ${({ theme }) => theme.color.bg};
  }
`;

export const Count = styled.small`
  margin-left: auto;
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Hint = styled.p`
  margin: 0;
  padding: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.md};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;
