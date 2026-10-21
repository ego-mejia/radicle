import styled from 'styled-components';

export const Wrap = styled.div`
  position: relative;
`;

export const Panel = styled.div`
  position: absolute;
  z-index: 20;
  top: calc(100% + ${({ theme }) => theme.space.xs});
  left: 0;
  right: 0;
  max-height: 420px;
  overflow-y: auto;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  box-shadow: 0 8px 24px rgba(17, 24, 39, 0.12);
  padding: ${({ theme }) => theme.space.xs};
`;

export const List = styled.ul`
  list-style: none;
  margin: 0;
  padding: 0;
`;

export const Option = styled.a<{ $active: boolean }>`
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  border-radius: ${({ theme }) => theme.radius.md};
  text-decoration: none;
  color: ${({ theme }) => theme.color.text};
  background: ${({ $active, theme }) => ($active ? theme.color.surface2 : 'transparent')};

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const Title = styled.span`
  font-weight: 600;
  font-size: 14px;
`;

export const Small = styled.span`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
`;

export const Footer = styled.p`
  margin: 0;
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
`;
