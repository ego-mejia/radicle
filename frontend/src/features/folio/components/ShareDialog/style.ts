import styled from 'styled-components';

export const Form = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Check = styled.label`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.md};

  input {
    accent-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Error = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.danger};
`;

export const Result = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};

  p {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }
`;

export const Warn = styled.p`
  color: ${({ theme }) => theme.color.warning};
`;
