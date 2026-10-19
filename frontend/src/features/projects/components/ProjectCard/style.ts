import styled from 'styled-components';

export const Card = styled.a`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;
  transition: border-color 0.12s;

  &:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Top = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Name = styled.div`
  font-size: ${({ theme }) => theme.fontSize.lg};
  font-weight: 700;
`;

export const Meta = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
