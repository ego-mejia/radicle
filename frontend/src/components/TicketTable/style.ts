import styled from 'styled-components';

export const Scroller = styled.div`
  overflow-x: auto;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
`;

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${({ theme }) => theme.fontSize.md};

  th {
    position: sticky;
    top: 0;
    padding: 8px 10px;
    text-align: left;
    font-size: ${({ theme }) => theme.fontSize.sm};
    font-weight: 600;
    color: ${({ theme }) => theme.color.textMuted};
    background: ${({ theme }) => theme.color.surface};
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    white-space: nowrap;
  }

  td {
    padding: 7px 10px;
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    white-space: nowrap;
  }

  tbody tr {
    cursor: pointer;
  }

  tbody tr:hover,
  tbody tr:focus-visible {
    background: ${({ theme }) => theme.color.surface2};
    outline: none;
  }

  tbody tr[aria-selected='true'] {
    background: ${({ theme }) => theme.color.accentSoft};
  }

  tbody tr:last-child td {
    border-bottom: 0;
  }
`;

export const SortButton = styled.button`
  all: unset;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;

  &:hover,
  &:focus-visible {
    color: ${({ theme }) => theme.color.text};
  }

  svg {
    width: 12px;
    height: 12px;
  }
`;

export const TitleCell = styled.td`
  max-width: 420px;
  overflow: hidden;
  text-overflow: ellipsis;
`;

export const Cell = styled.span`
  display: inline-flex;
  align-items: center;
  gap: 6px;
`;

export const Muted = styled.span<{ $danger?: boolean }>`
  color: ${({ theme, $danger }) => ($danger ? theme.color.danger : theme.color.textMuted)};
`;

export const Sentinel = styled.div`
  height: 1px;
`;

export const Footer = styled.div`
  padding: 10px;
  text-align: center;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const CheckCell = styled.td`
  width: 32px;

  input {
    width: 16px;
    height: 16px;
    cursor: pointer;
  }
`;

export const Grip = styled.span`
  display: inline-grid;
  place-items: center;
  color: ${({ theme }) => theme.color.textMuted};
  cursor: grab;
`;
