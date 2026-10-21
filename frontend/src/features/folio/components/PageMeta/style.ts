import styled from 'styled-components';

export const Card = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 14px;
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Rows = styled.dl`
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Row = styled.div`
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  dt {
    color: ${({ theme }) => theme.color.textMuted};
  }

  dd {
    margin: 0;
    font-weight: 600;
    text-align: right;
  }
`;

export const Labels = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;

  li {
    background: ${({ theme }) => theme.color.surface2};
    padding: 3px 8px;
    border-radius: ${({ theme }) => theme.radius.md};
  }
`;
