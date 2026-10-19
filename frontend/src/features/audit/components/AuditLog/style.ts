import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};

  > button {
    align-self: flex-start;
  }
`;

export const Filters = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.md};
  align-items: flex-end;

  > * {
    min-width: 140px;
  }
`;

export const Csv = styled.a`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 12px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;
`;

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  font-size: ${({ theme }) => theme.fontSize.md};

  th,
  td {
    padding: 6px ${({ theme }) => theme.space.sm};
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    text-align: left;
    vertical-align: top;
  }

  th {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }

  tbody tr[aria-expanded] {
    cursor: pointer;
  }

  tbody tr[aria-expanded]:hover {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const Details = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: ${({ theme }) => theme.space.md};

  pre {
    margin: 4px 0;
    padding: 8px;
    border-radius: ${({ theme }) => theme.radius.sm};
    background: ${({ theme }) => theme.color.surface2};
    font-size: ${({ theme }) => theme.fontSize.sm};
    white-space: pre-wrap;
    word-break: break-word;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Error = styled.p`
  color: ${({ theme }) => theme.color.danger};
`;
