import styled from 'styled-components';

export const Section = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
`;

export const Heading = styled.h2`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.lg};
`;

export const Form = styled.form`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};

  > :first-child {
    flex: 1;
    min-width: 0;
    font-family: ${({ theme }) => theme.fonts.mono};
  }
`;

/** The query again, with a caret under the character the error points at. */
export const Caret = styled.pre`
  margin: 0;
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.danger};
  white-space: pre-wrap;
  overflow-x: auto;
`;

export const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;

  th,
  td {
    text-align: left;
    padding: ${({ theme }) => theme.space.sm};
    border-top: 1px solid ${({ theme }) => theme.color.border};
  }

  th {
    font-size: ${({ theme }) => theme.fontSize.sm};
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 500;
  }
`;

export const Scroll = styled.div`
  overflow-x: auto;
`;

export const Note = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;
