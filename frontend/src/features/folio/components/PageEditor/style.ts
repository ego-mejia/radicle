import { Link } from '@tanstack/react-router';
import styled from 'styled-components';

export const Screen = styled.div`
  position: fixed;
  inset: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
`;

export const Bar = styled.header`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.xl}`};
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
`;

export const Back = styled(Link)`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  min-height: 36px;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
  text-decoration: none;
  &:hover {
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Crumb = styled.span`
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: ${({ theme }) => theme.fontSize.md};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const SaveState = styled.span<{ $error: boolean }>`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme, $error }) => ($error ? theme.color.danger : theme.color.textMuted)};
`;

export const Scroll = styled.main`
  flex: 1;
  overflow-y: auto;
`;

export const Page = styled.div`
  max-width: 760px;
  margin: 0 auto;
  padding: 48px ${({ theme }) => theme.space.xl} 160px;
`;
