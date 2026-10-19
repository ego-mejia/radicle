import styled from 'styled-components';

export const List = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Composer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  align-items: flex-start;

  > :first-child {
    width: 100%;
  }
`;

export const Empty = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;
