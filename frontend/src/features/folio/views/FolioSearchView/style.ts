import styled from 'styled-components';

export const Wrap = styled.div`
  max-width: 880px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Form = styled.form`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};

  > :first-child {
    flex: 1;
    min-width: 0;
  }
`;

export const Results = styled.ol`
  list-style: none;
  margin: 0;
  padding: 0;
`;

export const Note = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;
