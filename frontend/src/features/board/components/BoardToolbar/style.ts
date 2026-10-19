import styled from 'styled-components';

export const Bar = styled.div`
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  padding: 0 0 ${({ theme }) => theme.space.sm};

  select {
    width: auto;
  }
`;

export const Filters = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
`;

export const Chip = styled.button<{ $active: boolean }>`
  height: 28px;
  padding: 0 10px;
  border-radius: ${({ theme }) => theme.radius.full};
  border: 1px solid ${({ theme, $active }) => ($active ? theme.color.accent : theme.color.border)};
  background: ${({ theme, $active }) => ($active ? theme.color.accentSoft : theme.color.surface)};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  cursor: pointer;
`;

export const Spacer = styled.span`
  flex: 1;
`;
