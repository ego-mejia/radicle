import * as Dropdown from '@radix-ui/react-dropdown-menu';
import styled from 'styled-components';

export const Trigger = styled.button`
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 44px;
  padding: 6px 10px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: none;
  font: inherit;
  font-weight: 700;
  font-size: ${({ theme }) => theme.fontSize.lg};
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;

  &[data-state='open'] {
    border-color: ${({ theme }) => theme.color.accent};
    background: ${({ theme }) => theme.color.surface2};
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
    outline-offset: 2px;
  }

  > svg:last-child {
    width: 14px;
    height: 14px;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Badge = styled.span`
  padding: 3px 8px;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => (theme.mode === 'dark' ? theme.color.accent : theme.color.onAccent)};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 500;
`;

export const Content = styled(Dropdown.Content)`
  width: min(380px, calc(100vw - 32px));
  padding: ${({ theme }) => theme.space.sm};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 14px;
  box-shadow: 0 12px 32px rgba(17, 24, 39, 0.12);
  z-index: 60;
`;

export const Label = styled(Dropdown.Label)`
  padding: 8px 12px 4px;
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const App = styled(Dropdown.Item)<{ $current: boolean }>`
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 12px;
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme, $current }) => ($current ? theme.color.accentSoft : 'transparent')};
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;
  outline: none;

  &[data-highlighted] {
    background: ${({ theme, $current }) => ($current ? theme.color.accentSoft : theme.color.surface2)};
  }

  &[data-highlighted]:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
  }
`;

export const Tile = styled.span<{ $app: 'docket' | 'folio' }>`
  flex: 0 0 44px;
  width: 44px;
  height: 44px;
  border-radius: ${({ theme }) => theme.radius.lg};
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: ${({ theme, $app }) =>
    $app === 'folio'
      ? theme.color.accentFill
      : theme.mode === 'dark'
        ? theme.color.surface2
        : theme.color.text};
  color: ${({ theme, $app }) => ($app === 'folio' ? theme.color.onAccent : theme.color.accentFill)};

  svg {
    width: 22px;
    height: 22px;
  }
`;

export const Text = styled.span`
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;

  b {
    font-size: ${({ theme }) => theme.fontSize.lg};
    font-weight: 600;
  }

  small {
    font-size: ${({ theme }) => theme.fontSize.md};
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Keys = styled.kbd`
  padding: 2px 6px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Check = styled.span`
  display: inline-flex;
  color: ${({ theme }) => theme.color.accent};

  svg {
    width: 18px;
    height: 18px;
  }
`;

export const Separator = styled(Dropdown.Separator)`
  height: 1px;
  margin: 6px 4px;
  background: ${({ theme }) => theme.color.border};
`;

export const Admin = styled(Dropdown.Item)`
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  border-radius: ${({ theme }) => theme.radius.lg};
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;
  outline: none;

  &[data-highlighted] {
    background: ${({ theme }) => theme.color.surface2};
  }

  svg {
    width: 18px;
    height: 18px;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Note = styled.p`
  margin: 0;
  padding: 4px 12px 8px;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;
