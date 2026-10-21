import styled from 'styled-components';

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Row = styled.div`
  display: grid;
  grid-template-columns: 2fr 1fr;
  gap: ${({ theme }) => theme.space.md};

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
`;
