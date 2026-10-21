import styled from 'styled-components';

export const List = styled.ul`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  margin: 0 0 ${({ theme }) => theme.space.md};
  padding: 0;
  list-style: none;

  li {
    display: flex;
    flex-direction: column;
    gap: ${({ theme }) => theme.space.sm};
    padding-bottom: ${({ theme }) => theme.space.md};
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
  }

  svg {
    width: 14px;
    height: 14px;
  }
`;

export const Line = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};

  input,
  select {
    flex: 1 1 140px;
    width: auto;
  }
`;

export const Choices = styled.section`
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.sm};
  padding-left: ${({ theme }) => theme.space.lg};
  border-left: 2px solid ${({ theme }) => theme.color.border};
`;

export const Note = styled.p`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.warning};
`;
