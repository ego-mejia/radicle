import styled from 'styled-components';

export const Current = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Hits = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
`;

export const Hit = styled.button`
  display: flex;
  justify-content: space-between;
  gap: ${({ theme }) => theme.space.sm};
  width: 100%;
  min-height: 36px;
  padding: ${({ theme }) => theme.space.sm} ${({ theme }) => theme.space.md};
  border: 0;
  background: none;
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.md};
  text-align: left;
  cursor: pointer;

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;
