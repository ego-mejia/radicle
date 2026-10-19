import styled from 'styled-components';

export const List = styled.div`
  display: flex;
  gap: 2px;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  overflow-x: auto;
`;

export const Tab = styled.button<{ $active: boolean }>`
  padding: 8px 12px;
  border: 0;
  border-bottom: 2px solid ${({ theme, $active }) => ($active ? theme.color.accent : 'transparent')};
  margin-bottom: -1px;
  background: none;
  font: inherit;
  font-weight: 600;
  white-space: nowrap;
  color: ${({ theme, $active }) => ($active ? theme.color.text : theme.color.textMuted)};
  cursor: pointer;

  &:hover {
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Count = styled.span`
  margin-left: 6px;
  font-size: ${({ theme }) => theme.fontSize.xs};
  color: ${({ theme }) => theme.color.textMuted};
`;
