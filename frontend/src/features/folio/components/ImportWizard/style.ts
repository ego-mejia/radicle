import styled from 'styled-components';

export const Wizard = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Head = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.md};

  div {
    display: grid;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const History = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: ${({ theme }) => theme.space.sm};

  li {
    display: flex;
    align-items: center;
    gap: ${({ theme }) => theme.space.sm};
  }

  button {
    background: none;
    border: 0;
    padding: 0;
    color: ${({ theme }) => theme.color.accent};
    cursor: pointer;
    font: inherit;
  }

  small {
    flex: 1;
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Problem = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;
