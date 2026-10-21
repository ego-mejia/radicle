import styled from 'styled-components';

export const Check = styled.label`
  display: flex;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.sm};
  margin-top: ${({ theme }) => theme.space.md};
  cursor: pointer;

  input {
    margin-top: 3px;
  }

  span {
    display: grid;
    gap: 2px;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;
