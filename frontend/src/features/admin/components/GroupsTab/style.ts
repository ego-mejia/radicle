import styled from 'styled-components';

export const Group = styled.div<{ $open: boolean }>`
  border: 1px solid ${({ theme, $open }) => ($open ? theme.color.accent : theme.color.border)};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  overflow: hidden;
  transition: border-color 0.15s ease;
`;

export const Header = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding-right: ${({ theme }) => theme.space.sm};
`;

export const Toggle = styled.button`
  all: unset;
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: 10px 12px;
  cursor: pointer;
  border-radius: ${({ theme }) => theme.radius.md};

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
    outline-offset: -2px;
  }
`;

export const Chevron = styled.span<{ $open: boolean }>`
  display: inline-flex;
  color: ${({ theme }) => theme.color.textMuted};
  transform: rotate(${({ $open }) => ($open ? 90 : 0)}deg);
  transition: transform 0.15s ease;
`;

export const Icon = styled.span`
  display: inline-grid;
  place-items: center;
  width: 30px;
  height: 30px;
  flex: none;
  border-radius: 50%;
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.accent};
`;

export const Text = styled.span`
  min-width: 0;
  display: flex;
  flex-direction: column;
  line-height: 1.3;

  strong {
    font-weight: 600;
  }

  small {
    overflow: hidden;
    color: ${({ theme }) => theme.color.textMuted};
    text-overflow: ellipsis;
    white-space: nowrap;
  }
`;

export const Count = styled.span`
  margin-left: auto;
  flex: none;
  padding: 2px 10px;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Members = styled.div`
  padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md} ${theme.space.md} 56px`};
  border-top: 1px solid ${({ theme }) => theme.color.border};
  background: ${({ theme }) => theme.color.surface2};
`;
