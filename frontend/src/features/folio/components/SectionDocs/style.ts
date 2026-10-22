import { Link } from '@tanstack/react-router';
import styled from 'styled-components';

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: ${({ theme }) => theme.space.lg};
`;

export const Card = styled(Link)`
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 18px 20px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 16px;
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;

  b {
    font-size: ${({ theme }) => theme.fontSize.lg};
    line-height: 1.3;
  }
  span {
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.md};
    line-height: 1.5;
  }
  small {
    margin-top: auto;
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.sm};
  }
  &:hover {
    border-color: ${({ theme }) => theme.color.textMuted};
  }
`;
