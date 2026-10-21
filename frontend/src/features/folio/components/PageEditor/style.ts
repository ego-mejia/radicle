import { Link } from '@tanstack/react-router';
import styled from 'styled-components';

export const Screen = styled.div`
  position: fixed;
  inset: 0;
  /* Full screen: above the Folio bar (z-index 30), which would cover its toolbar. */
  z-index: 40;
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

export const Cover = styled.div`
  position: relative;
  height: 240px;
  background: ${({ theme }) => theme.color.surface2};
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
    display: block;
  }
`;

export const CoverTools = styled.div`
  position: absolute;
  right: ${({ theme }) => theme.space.xl};
  bottom: ${({ theme }) => theme.space.md};
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Page = styled.div`
  position: relative;
  max-width: 760px;
  margin: 0 auto;
  padding: 48px ${({ theme }) => theme.space.xl} 160px;
`;
