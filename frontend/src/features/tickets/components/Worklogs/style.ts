import styled from 'styled-components';

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
`;

export const Item = styled.li`
  display: flex;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.sm} 0;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
`;

export const Body = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;

  small {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.xs};
  }
`;

export const Empty = styled.p`
  color: ${({ theme }) => theme.color.textMuted};
`;
