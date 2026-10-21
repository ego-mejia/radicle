import styled from 'styled-components';

export const Summary = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.lg};
  color: ${({ theme }) => theme.color.textMuted};

  strong {
    color: ${({ theme }) => theme.color.text};
    font-size: ${({ theme }) => theme.fontSize.lg};
  }
`;

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: ${({ theme }) => theme.space.sm};

  li {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: ${({ theme }) => theme.space.sm};
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const PageError = styled.span`
  flex-basis: 100%;
  color: ${({ theme }) => theme.color.danger};
  font-size: ${({ theme }) => theme.fontSize.xs};
`;

export const Problem = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;
