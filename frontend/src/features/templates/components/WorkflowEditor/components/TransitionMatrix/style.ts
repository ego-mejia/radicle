import styled from 'styled-components';

export const Scroll = styled.div`
  overflow-x: auto;
  max-width: 100%;
`;

export const Table = styled.table`
  border-collapse: collapse;
  font-size: ${({ theme }) => theme.fontSize.sm};

  th,
  td {
    border: 1px solid ${({ theme }) => theme.color.border};
    padding: 4px;
    text-align: center;
    min-width: 84px;
  }

  th {
    font-weight: 500;
    color: ${({ theme }) => theme.color.textMuted};
    background: ${({ theme }) => theme.color.surface2};
  }

  th[scope='row'] {
    text-align: left;
    white-space: nowrap;
  }
`;

export const Cell = styled.td<{ $disabled?: boolean }>`
  background: ${({ theme, $disabled }) => ($disabled ? theme.color.surface2 : 'transparent')};
  vertical-align: middle;
`;

export const On = styled.button`
  display: block;
  width: 100%;
  margin: 2px 0;
  padding: 3px 6px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.xs};
  cursor: pointer;
`;

export const Off = styled.button`
  width: 100%;
  border: 1px dashed transparent;
  border-radius: ${({ theme }) => theme.radius.sm};
  background: none;
  color: ${({ theme }) => theme.color.textMuted};
  cursor: pointer;
  opacity: 0.4;

  &:hover,
  &:focus-visible {
    opacity: 1;
    border-color: ${({ theme }) => theme.color.border};
  }
`;

export const Rules = styled.span`
  display: inline-grid;
  place-items: center;
  min-width: 16px;
  height: 16px;
  margin-left: 4px;
  padding: 0 4px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.accent};
  color: ${({ theme }) => theme.color.surface};
  font-size: 10px;
  font-weight: 600;
`;
