import styled from 'styled-components';

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  margin-bottom: ${({ theme }) => theme.space.md};
  font-size: ${({ theme }) => theme.fontSize.md};

  th,
  td {
    padding: 6px ${({ theme }) => theme.space.sm};
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    text-align: center;
  }

  th[scope='row'] {
    text-align: left;
    font-weight: 400;
  }

  code {
    display: block;
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.xs};
  }
`;

export const Cell = styled.td<{ $changed: boolean }>`
  background: ${({ theme, $changed }) => ($changed ? theme.color.accentSoft : 'transparent')};
`;
