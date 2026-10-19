import styled from 'styled-components';

export const Row = styled.div<{ $dragging: boolean; $selected: boolean }>`
  display: grid;
  grid-template-columns: auto auto 1fr auto auto auto 64px 20px;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: 6px ${({ theme }) => theme.space.sm};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme, $selected }) => ($selected ? theme.color.accentSoft : theme.color.surface)};
  opacity: ${({ $dragging }) => ($dragging ? 0.4 : 1)};
  font-size: ${({ theme }) => theme.fontSize.md};

  &:last-child {
    border-bottom: 0;
  }

  @media (max-width: 640px) {
    grid-template-columns: auto auto 1fr 64px;

    > :nth-child(n + 5):not(:nth-last-child(2)) {
      display: none;
    }
  }
`;

export const Handle = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: grab;
`;

export const Title = styled.button`
  border: 0;
  background: none;
  padding: 0;
  text-align: left;
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  cursor: pointer;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;

  &:hover {
    text-decoration: underline;
  }
`;

export const Status = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  white-space: nowrap;
`;

export const Hours = styled.span`
  text-align: right;
  font-variant-numeric: tabular-nums;
`;

export const Missing = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 3px;
  color: ${({ theme }) => theme.color.warning};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Empty = styled.span`
  width: 20px;
`;
