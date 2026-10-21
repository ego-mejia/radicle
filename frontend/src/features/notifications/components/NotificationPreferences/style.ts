import styled from 'styled-components';

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${({ theme }) => theme.fontSize.md};

  th,
  td {
    padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    text-align: left;
  }

  thead th {
    font-size: ${({ theme }) => theme.fontSize.sm};
    font-weight: 600;
    color: ${({ theme }) => theme.color.textMuted};
  }

  tbody th {
    font-weight: 500;
  }

  td {
    width: 96px;
  }

  input {
    width: 16px;
    height: 16px;
    accent-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Muted = styled.p`
  margin: ${({ theme }) => `${theme.space.md} 0 0`};
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;
