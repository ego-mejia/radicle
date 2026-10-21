import styled from 'styled-components';

export const Term = styled.div`
  flex: 1;
  display: grid;
  gap: 2px;
  min-width: 0;

  p {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.md};
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;

export const Form = styled.form`
  display: grid;
  gap: ${({ theme }) => theme.space.sm};
  padding-top: ${({ theme }) => theme.space.md};
  border-top: 1px solid ${({ theme }) => theme.color.border};
`;

export const Pair = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: ${({ theme }) => theme.space.sm};
`;
