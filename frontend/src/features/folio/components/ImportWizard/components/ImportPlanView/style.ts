import styled from 'styled-components';

export const Totals = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(110px, 1fr));
  gap: ${({ theme }) => theme.space.sm};

  div {
    display: grid;
    padding: ${({ theme }) => theme.space.md};
    background: ${({ theme }) => theme.color.surface};
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.md};
  }

  strong {
    font-size: ${({ theme }) => theme.fontSize.xl};
  }

  span {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;

export const Rows = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Row = styled.div`
  display: grid;
  grid-template-columns: minmax(140px, 1fr) minmax(180px, 2fr);
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${({ theme }) => theme.fontSize.sm};

  th {
    text-align: left;
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 500;
    padding: 6px 8px;
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
  }

  td {
    padding: 6px 8px;
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    vertical-align: top;
  }
`;

export const Title = styled.td<{ $depth: number }>`
  padding-left: ${({ $depth }) => 8 + $depth * 18}px !important;

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const PageError = styled.div`
  color: ${({ theme }) => theme.color.danger};
  font-size: ${({ theme }) => theme.fontSize.xs};
`;

export const Problem = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;

export const Actions = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: ${({ theme }) => theme.space.sm};
`;
