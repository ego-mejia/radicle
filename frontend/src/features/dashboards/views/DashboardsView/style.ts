import styled from 'styled-components';

export const Page = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Create = styled.form`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.sm};
  max-width: 560px;

  input {
    flex: 1;
    min-width: 200px;
  }
`;

export const Error = styled.p`
  width: 100%;
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: ${({ theme }) => theme.space.md};

  a {
    display: flex;
    flex-direction: column;
    gap: 6px;
    padding: ${({ theme }) => theme.space.lg};
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.md};
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
    text-decoration: none;
  }

  a:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }

  a > svg {
    color: ${({ theme }) => theme.color.accent};
  }

  span {
    display: flex;
    align-items: center;
    gap: 6px;
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;
