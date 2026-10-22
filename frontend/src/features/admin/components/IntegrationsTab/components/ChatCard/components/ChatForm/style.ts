import styled from 'styled-components';

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: ${({ theme }) => theme.space.md};
  align-items: end;
`;

export const Kinds = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.lg};

  label {
    display: inline-flex;
    gap: 6px;
    align-items: center;
  }
`;

export const Route = styled.fieldset`
  margin: 0;
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Row = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
`;
