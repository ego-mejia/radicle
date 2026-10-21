import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  padding-bottom: ${({ theme }) => theme.space.md};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
`;

export const Group = styled.section`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
`;

export const Title = styled.h2`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};

  svg {
    width: 13px;
    height: 13px;
  }
`;

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;

  a {
    display: block;
    padding: ${({ theme }) => `${theme.space.xs} 0`};
    font-size: ${({ theme }) => theme.fontSize.lg};
    color: ${({ theme }) => theme.color.text};
    text-decoration: none;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  a:hover {
    color: ${({ theme }) => theme.color.accent};
  }
`;
