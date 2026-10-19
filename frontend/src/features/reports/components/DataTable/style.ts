import styled from 'styled-components';

export const Details = styled.details`
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};

  summary {
    padding: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.md};
    cursor: pointer;
    font-weight: 600;
  }
`;

export const Scroll = styled.div`
  max-height: 360px;
  overflow: auto;

  table {
    width: 100%;
    border-collapse: collapse;
    font-size: ${({ theme }) => theme.fontSize.md};
    font-variant-numeric: tabular-nums;
  }

  th,
  td {
    padding: 6px ${({ theme }) => theme.space.md};
    border-top: 1px solid ${({ theme }) => theme.color.border};
    text-align: left;
    white-space: nowrap;
  }

  th {
    position: sticky;
    top: 0;
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 600;
  }
`;
