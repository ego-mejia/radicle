import styled from 'styled-components';

export const Title = styled.input`
  width: 100%;
  margin-bottom: ${({ theme }) => theme.space.sm};
  padding: 0 0 ${({ theme }) => theme.space.xs};
  border: 0;
  border-bottom: 2px solid ${({ theme }) => theme.color.accentFill};
  background: transparent;
  color: ${({ theme }) => theme.color.text};
  font-weight: 600;
  font-size: ${({ theme }) => theme.fontSize.lg};

  &:focus {
    outline: none;
  }
`;
