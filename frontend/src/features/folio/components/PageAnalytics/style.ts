import styled from 'styled-components';

export const Body = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.md};
  margin-top: ${({ theme }) => theme.space.md};
`;

export const Heading = styled.h3`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Muted = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Readers = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: ${({ theme }) => theme.space.xs};

  li {
    display: flex;
    justify-content: space-between;
    gap: ${({ theme }) => theme.space.md};
    padding: ${({ theme }) => theme.space.xs} 0;
    border-bottom: 1px solid ${({ theme }) => theme.color.border};
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
