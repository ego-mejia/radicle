import * as Popover from '@radix-ui/react-popover';
import styled from 'styled-components';

export const Trigger = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-height: 40px;
  padding: 4px 12px 4px 10px;
  border: 1px solid rgba(255, 255, 255, 0.14);
  border-radius: ${({ theme }) => theme.radius.full};
  background: rgba(255, 255, 255, 0.06);
  color: ${({ theme }) => theme.color.heroMuted};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.md};
  cursor: pointer;

  &:hover,
  &[data-state='open'] {
    border-color: rgba(255, 255, 255, 0.35);
  }

  b {
    color: ${({ theme }) => theme.color.accentFill};
  }
`;

export const Stack = styled.span`
  display: flex;
  align-items: center;
`;

export const Ring = styled.span<{ $admin: boolean }>`
  display: inline-flex;
  border-radius: ${({ theme }) => theme.radius.full};
  margin-left: -6px;
  box-shadow:
    0 0 0 2px ${({ theme }) => theme.color.hero},
    ${({ $admin, theme }) => ($admin ? `0 0 0 4px ${theme.color.accentFill}` : '0 0 0 0 transparent')};

  &:first-child {
    margin-left: 0;
  }
`;

export const More = styled.span`
  width: 26px;
  height: 26px;
  margin-left: -6px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 700;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 0 0 2px ${({ theme }) => theme.color.hero};
`;

export const Summary = styled.span`
  white-space: nowrap;
`;

export const Content = styled(Popover.Content)`
  width: min(300px, calc(100vw - 32px));
  max-height: 60vh;
  overflow-y: auto;
  padding: ${({ theme }) => theme.space.sm};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 14px;
  box-shadow: 0 12px 32px rgba(17, 24, 39, 0.16);
  color: ${({ theme }) => theme.color.text};
  z-index: 60;
`;

export const Group = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;
`;

export const GroupTitle = styled.span`
  padding: 8px 10px 4px;
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Person = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  min-height: 36px;
  padding: 0 10px;
  font-size: ${({ theme }) => theme.fontSize.md};

  small {
    margin-left: auto;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Everyone = styled.p`
  margin: ${({ theme }) => theme.space.sm} 10px 4px;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;
