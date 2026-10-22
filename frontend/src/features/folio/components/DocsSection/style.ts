import { Link } from '@tanstack/react-router';
import styled from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: ${({ theme }) => theme.space.lg};
  align-items: start;
`;

export const Module = styled.section`
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 18px 20px;
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 16px;
  background: ${({ theme }) => theme.color.surface};
`;

export const ModuleHead = styled.div`
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: ${({ theme }) => theme.space.sm};

  h2 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.lg};
  }
  small {
    margin-left: auto;
    font-family: ${({ theme }) => theme.fonts.mono};
    font-size: ${({ theme }) => theme.fontSize.xs};
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Mark = styled.span`
  width: 32px;
  height: 32px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};
  font-weight: 700;
`;

export const Row = styled(Link)`
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px 0;
  border-top: 1px solid ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.text};
  text-decoration: none;

  b {
    font-size: ${({ theme }) => theme.fontSize.md};
    font-weight: 600;
  }
  span {
    font-size: ${({ theme }) => theme.fontSize.sm};
    color: ${({ theme }) => theme.color.textMuted};
  }
  &:hover b {
    color: ${({ theme }) => theme.color.accent};
  }
`;
