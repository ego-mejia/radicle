import styled from 'styled-components';

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: ${({ theme }) => theme.space.sm};

  button {
    display: flex;
    flex-direction: column;
    gap: 4px;
    padding: ${({ theme }) => theme.space.md};
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.md};
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
    font: inherit;
    text-align: left;
    cursor: pointer;
  }

  button:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }

  span {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
`;
