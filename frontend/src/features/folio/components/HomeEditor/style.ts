import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Toolbar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Status = styled.p`
  flex: 1;
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Errors = styled.ul`
  margin: 0;
  padding: ${({ theme }) => theme.space.md} ${({ theme }) => theme.space.xl};
  border: 1px solid ${({ theme }) => theme.color.danger};
  border-radius: ${({ theme }) => theme.radius.md};
  color: ${({ theme }) => theme.color.danger};
  font-size: ${({ theme }) => theme.fontSize.md};
`;
