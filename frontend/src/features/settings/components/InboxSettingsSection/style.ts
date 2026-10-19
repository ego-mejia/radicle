import styled from 'styled-components';

export const Form = styled.form`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};

  > button {
    align-self: flex-start;
  }
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: ${({ theme }) => theme.space.md};
`;

export const Row = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Check = styled.label`
  display: inline-flex;
  align-items: center;
  gap: 6px;
`;

export const Link = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  code {
    padding: 4px 8px;
    border-radius: ${({ theme }) => theme.radius.sm};
    background: ${({ theme }) => theme.color.surface2};
  }

  a {
    display: inline-flex;
    align-items: center;
    gap: 4px;
  }
`;
