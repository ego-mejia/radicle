import styled from 'styled-components';

export const Expander = styled.button<{ $open: boolean }>`
  all: unset;
  display: inline-flex;
  align-items: center;
  gap: 2px;
  min-width: 34px;
  height: 22px;
  margin-right: 4px;
  padding: 0 4px;
  border-radius: ${({ theme }) => theme.radius.sm};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.xs};
  cursor: pointer;

  svg {
    transform: rotate(${({ $open }) => ($open ? 90 : 0)}deg);
    transition: transform 0.12s ease;
  }

  &:hover {
    background: ${({ theme }) => theme.color.accentSoft};
    color: ${({ theme }) => theme.color.accent};
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
  }
`;

export const Spacer = styled.span`
  display: inline-block;
  width: 38px;
`;

export const GroupRow = styled.tr`
  && td {
    padding: 0;
    background: ${({ theme }) => theme.color.surface2};
  }
`;

export const GroupToggle = styled.button<{ $open: boolean }>`
  all: unset;
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  box-sizing: border-box;
  padding: 7px 10px;
  cursor: pointer;

  svg {
    color: ${({ theme }) => theme.color.textMuted};
    transform: rotate(${({ $open }) => ($open ? 90 : 0)}deg);
    transition: transform 0.12s ease;
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
    outline-offset: -2px;
  }
`;

export const Count = styled.span`
  padding: 0 8px;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.xs};
`;

export const Loading = styled.td`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
