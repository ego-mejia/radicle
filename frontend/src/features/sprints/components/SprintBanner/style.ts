import styled from 'styled-components';

export const Banner = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  margin: 0 0 ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-left: 3px solid ${({ theme }) => theme.color.accent};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  font-size: ${({ theme }) => theme.fontSize.md};

  span {
    color: ${({ theme }) => theme.color.textMuted};
  }

  a {
    margin-left: auto;
  }
`;

export const Goal = styled.em`
  color: ${({ theme }) => theme.color.text};
`;
