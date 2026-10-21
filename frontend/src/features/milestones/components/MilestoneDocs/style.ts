import styled from 'styled-components';

export const Box = styled.section`
  display: grid;
  gap: ${({ theme }) => theme.space.xs};
  padding-top: ${({ theme }) => theme.space.sm};
  border-top: 1px solid ${({ theme }) => theme.color.border};
`;

export const Title = styled.h3`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
`;

export const List = styled.ul`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => `${theme.space.xs} ${theme.space.lg}`};
  margin: 0;
  padding: 0;
  list-style: none;
  font-size: ${({ theme }) => theme.fontSize.md};

  li {
    display: inline-flex;
    align-items: center;
    gap: ${({ theme }) => theme.space.xs};
  }

  a {
    display: inline-flex;
    align-items: center;
    gap: ${({ theme }) => theme.space.xs};
  }
`;

export const Meta = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
