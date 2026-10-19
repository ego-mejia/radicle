import styled from 'styled-components';

export const Wrapper = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  overflow-x: auto;
  padding: 0 ${({ theme }) => theme.space.xl} ${({ theme }) => theme.space.md};
`;

export const Header = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.md};
  position: sticky;
  top: 0;
  z-index: 2;
  background: ${({ theme }) => theme.color.bg};
`;

export const ColumnHead = styled.div<{ $over: boolean }>`
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 10px;
  font-weight: 700;
  border-bottom: 2px solid
    ${({ theme, $over }) => ($over ? theme.color.danger : theme.color.border)};

  small {
    margin-left: auto;
    font-weight: ${({ $over }) => ($over ? 700 : 400)};
    color: ${({ theme, $over }) => ($over ? theme.color.danger : theme.color.textMuted)};
  }
`;

export const Lane = styled.section`
  display: flex;
  flex-direction: column;
  gap: 6px;
`;

export const LaneHead = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  align-self: flex-start;
  border: 0;
  background: none;
  padding: 4px 0;
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-weight: 600;
  cursor: pointer;

  svg {
    width: 16px;
    height: 16px;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
    font-weight: 400;
  }
`;

export const Row = styled.div`
  display: grid;
  gap: ${({ theme }) => theme.space.md};
  align-items: start;

  > section {
    min-height: 80px;
  }
`;
