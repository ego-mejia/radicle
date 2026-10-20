import * as Popover from '@radix-ui/react-popover';
import styled from 'styled-components';

export const Panel = styled(Popover.Content)`
  z-index: 50;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  width: 280px;
  max-height: min(70vh, 520px);
  overflow-y: auto;
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  box-shadow: 0 16px 36px rgba(17, 24, 39, 0.16);
`;

export const Head = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.md};
  }
`;

export const Group = styled.div`
  display: flex;
  flex-direction: column;
  gap: 2px;

  h3 {
    margin: 0 0 4px;
    font-size: ${({ theme }) => theme.fontSize.xs};
    color: ${({ theme }) => theme.color.textMuted};
    text-transform: uppercase;
    letter-spacing: 0.04em;
  }
`;

export const Item = styled.div<{ $active: boolean }>`
  display: flex;
  align-items: center;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme, $active }) => ($active ? theme.color.accentSoft : 'transparent')};

  > button:first-child {
    flex: 1;
    min-width: 0;
    padding: 5px 8px;
    border: 0;
    background: none;
    color: ${({ theme }) => theme.color.text};
    font: inherit;
    font-size: ${({ theme }) => theme.fontSize.md};
    text-align: left;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    cursor: pointer;
  }

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const Remove = styled.button`
  display: grid;
  place-items: center;
  width: 24px;
  height: 24px;
  border: 0;
  background: none;
  color: ${({ theme }) => theme.color.textMuted};
  cursor: pointer;

  svg {
    width: 14px;
    height: 14px;
  }
`;

export const Empty = styled.span`
  padding: 0 8px;
  color: ${({ theme }) => theme.color.textMuted};
`;
