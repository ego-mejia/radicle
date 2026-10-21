import styled from 'styled-components';

export const Waiting = styled.p`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Error = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.danger};
`;

export const Proposal = styled.div`
  padding: ${({ theme }) => theme.space.md};
  border: 1px dashed ${({ theme }) => theme.color.accent};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.accentSoft};
`;

export const Note = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Actions = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: ${({ theme }) => theme.space.sm};
`;
