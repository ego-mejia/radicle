import styled from 'styled-components';

export const Box = styled.nav`
  padding: ${({ theme }) => theme.space.md};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};

  ul {
    display: grid;
    gap: ${({ theme }) => theme.space.xs};
    margin: ${({ theme }) => theme.space.sm} 0 0;
    padding: 0;
    list-style: none;
  }

  li {
    display: flex;
    justify-content: space-between;
    gap: ${({ theme }) => theme.space.sm};
  }

  a {
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Label = styled.span`
  color: ${({ theme }) => theme.color.accent};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
`;

export const Muted = styled.p`
  margin: ${({ theme }) => theme.space.sm} 0 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};

  li & {
    margin: 0;
  }
`;
