import styled from 'styled-components';

export const Groups = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xl};
  max-width: 760px;
`;

export const Group = styled.section`
  display: flex;
  flex-direction: column;
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.xl}`};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
`;

export const Title = styled.h2`
  margin: ${({ theme }) => `${theme.space.sm} 0`};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Row = styled.a`
  display: flex;
  align-items: baseline;
  gap: ${({ theme }) => theme.space.sm};
  padding: ${({ theme }) => `${theme.space.md} 0`};
  border-top: 1px solid ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.text};
  font-weight: 500;
  text-decoration: none;

  &:first-child {
    border-top: 0;
  }

  &:hover {
    color: ${({ theme }) => theme.color.accent};
  }

  small {
    margin-left: auto;
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 400;
  }
`;
