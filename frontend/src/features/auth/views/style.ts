import styled from 'styled-components';

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Heading = styled.div`
  display: flex;
  flex-direction: column;
  gap: 4px;

  h1 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }

  p {
    margin: 0;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
