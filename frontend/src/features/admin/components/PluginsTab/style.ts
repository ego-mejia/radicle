import styled from 'styled-components';

export const Stack = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Manifest = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};

  textarea {
    font-family: ${({ theme }) => theme.fonts.mono};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;

export const Actions = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
`;
