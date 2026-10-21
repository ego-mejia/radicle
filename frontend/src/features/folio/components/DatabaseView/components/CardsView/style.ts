import styled from 'styled-components';

export const Grid = styled.ul`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: ${({ theme }) => theme.space.md};
  margin: 0;
  padding: 0;
  list-style: none;
`;

export const Card = styled.li`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
`;

export const Title = styled.div`
  font-weight: 600;
  min-height: 1.2em;
`;

export const Fields = styled.dl`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.sm};

  div {
    display: flex;
    gap: ${({ theme }) => theme.space.sm};
    align-items: center;
  }

  dt {
    min-width: 72px;
    color: ${({ theme }) => theme.color.textMuted};
  }

  dd {
    margin: 0;
  }

  svg {
    width: 14px;
    height: 14px;
  }
`;
