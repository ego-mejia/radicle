import * as Dropdown from '@radix-ui/react-dropdown-menu';
import styled from 'styled-components';

export const Content = styled(Dropdown.Content)`
  min-width: 180px;
  max-height: 360px;
  overflow: auto;
  padding: 4px;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.18);
  z-index: 50;
`;

export const Item = styled(Dropdown.Item)<{ $danger?: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: ${({ theme }) => theme.radius.sm};
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme, $danger }) => ($danger ? theme.color.danger : theme.color.text)};
  cursor: pointer;
  outline: none;

  &[data-highlighted] {
    background: ${({ theme }) => theme.color.surface2};
  }

  &[data-disabled] {
    opacity: 0.5;
    cursor: default;
  }

  svg {
    width: 14px;
    height: 14px;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Label = styled(Dropdown.Label)`
  padding: 6px 8px 4px;
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Separator = styled(Dropdown.Separator)`
  height: 1px;
  margin: 4px 0;
  background: ${({ theme }) => theme.color.border};
`;

export const Hint = styled.span`
  margin-left: auto;
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
`;
