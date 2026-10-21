import styled from 'styled-components';

export const Panel = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding: ${({ theme }) => theme.space.xl};
  border-radius: ${({ theme }) => theme.radius.lg};
  border: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme }) => theme.color.surface};
  min-width: 0;

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xl};
  }
`;

export const Meta = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Note = styled.blockquote`
  margin: 0;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  border-left: 3px solid ${({ theme }) => theme.color.accent};
  background: ${({ theme }) => theme.color.surface2};
  border-radius: ${({ theme }) => theme.radius.md};
`;

export const Fields = styled.dl`
  display: grid;
  grid-template-columns: max-content minmax(0, 1fr);
  gap: ${({ theme }) => `${theme.space.xs} ${theme.space.lg}`};
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};

  dt {
    color: ${({ theme }) => theme.color.textMuted};
  }

  dd {
    margin: 0;
  }
`;

export const Actions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Error = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;
