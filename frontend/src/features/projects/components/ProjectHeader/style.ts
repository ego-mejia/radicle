import styled from 'styled-components';

export const Header = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  margin-bottom: ${({ theme }) => theme.space.lg};
`;

export const TitleRow = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  flex-wrap: wrap;

  h1 {
    margin: 0;
    font-size: ${({ theme }) => theme.fontSize.xl};
    letter-spacing: -0.01em;
  }
`;

export const Tabs = styled.nav`
  display: flex;
  gap: 2px;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};
  overflow-x: auto;
`;

export const Tab = styled.a`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 12px;
  margin-bottom: -1px;
  border-bottom: 2px solid transparent;
  color: ${({ theme }) => theme.color.textMuted};
  font-weight: 600;
  text-decoration: none;
  white-space: nowrap;

  &:hover {
    color: ${({ theme }) => theme.color.text};
  }

  &[data-status='active'] {
    color: ${({ theme }) => theme.color.text};
    border-bottom-color: ${({ theme }) => theme.color.accent};
  }

  svg {
    width: 15px;
    height: 15px;
  }
`;

export const Spacer = styled.div`
  flex: 1;
`;

export const Count = styled.span`
  min-width: 18px;
  padding: 0 5px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.accentFill};
  color: ${({ theme }) => theme.color.onAccent};
  font-size: ${({ theme }) => theme.fontSize.xs};
  font-weight: 700;
  text-align: center;
`;
