import styled from 'styled-components';

export const Box = styled.section`
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  overflow-x: auto;
`;

export const Head = styled.header`
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  gap: ${({ theme }) => theme.space.sm};
  margin-bottom: ${({ theme }) => theme.space.sm};

  strong {
    font-size: ${({ theme }) => theme.fontSize.md};
  }
`;

export const Rql = styled.code`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: ${({ theme }) => theme.fontSize.sm};

  th,
  td {
    padding: ${({ theme }) => theme.space.xs} ${({ theme }) => theme.space.sm};
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
    text-align: left;
    vertical-align: top;
  }

  th {
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 600;
  }

  a {
    color: ${({ theme }) => theme.color.text};
    font-family: ${({ theme }) => theme.fonts.mono};
    font-weight: 600;
    white-space: nowrap;
  }
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Error = styled(Muted)`
  color: ${({ theme }) => theme.color.danger};
`;
