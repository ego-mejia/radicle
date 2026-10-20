import styled from 'styled-components';

export const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
  overflow-x: auto;
  padding: 0 0 ${({ theme }) => theme.space.md};
`;

export const Tools = styled.div`
  display: flex;
  justify-content: flex-end;
  margin-bottom: 4px;
`;

export const ToggleAll = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  border: 0;
  background: none;
  padding: 4px 8px;
  border-radius: ${({ theme }) => theme.radius.sm};
  color: ${({ theme }) => theme.color.textMuted};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  cursor: pointer;

  svg {
    width: 14px;
    height: 14px;
  }

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Header = styled.div`
  display: grid;
  gap: 8px;
  position: sticky;
  top: 0;
  z-index: 2;
  padding-bottom: 6px;
  background: ${({ theme }) => theme.color.bg};
`;

export const ColumnHead = styled.div<{ $over: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme, $over }) =>
    $over
      ? theme.color.danger
      : theme.mode === 'dark'
        ? theme.color.surface
        : theme.color.surface2};

  span {
    color: ${({ theme, $over }) => ($over ? theme.color.surface : theme.color.textMuted)};
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }

  small {
    color: ${({ theme, $over }) => ($over ? theme.color.surface : theme.color.textMuted)};
    font-size: 12px;
    font-weight: 600;
  }
`;

export const Lane = styled.section`
  display: flex;
  flex-direction: column;
  padding: 2px 0 8px;
  border-top: 1px solid ${({ theme }) => theme.color.border};
`;

export const LaneHead = styled.button<{ $open: boolean }>`
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  border: 0;
  background: none;
  padding: 8px 4px;
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  text-align: left;
  cursor: pointer;
  border-radius: ${({ theme }) => theme.radius.sm};

  svg {
    width: 16px;
    height: 16px;
    flex: none;
    color: ${({ theme }) => theme.color.textMuted};
    transform: rotate(${({ $open }) => ($open ? 90 : 0)}deg);
    transition: transform 0.12s ease;
  }

  strong {
    font-weight: 600;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
  }

  &:focus-visible {
    outline: 2px solid ${({ theme }) => theme.color.accent};
  }
`;

export const Row = styled.div`
  display: grid;
  gap: 8px;
  align-items: stretch;

  > section {
    min-height: 90px;
  }
`;
