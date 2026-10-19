import styled from 'styled-components';

export const Box = styled.section`
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: flex-start;
`;

export const Bar = styled.div<{ $over: boolean }>`
  position: relative;
  width: 100%;
  height: 8px;
  border-radius: ${({ theme }) => theme.radius.full};
  background: ${({ theme }) => theme.color.surface2};
  overflow: visible;

  > span {
    display: block;
    height: 100%;
    border-radius: inherit;
    background: ${({ theme, $over }) => ($over ? theme.color.warning : theme.color.accentFill)};
  }
`;

export const Mark = styled.i`
  position: absolute;
  top: -3px;
  width: 2px;
  height: 14px;
  background: ${({ theme }) => theme.color.textMuted};
`;

export const Numbers = styled.div`
  display: flex;
  justify-content: space-between;
  width: 100%;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};

  strong {
    color: ${({ theme }) => theme.color.text};
  }
`;

export const Remaining = styled.div`
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};

  input {
    width: 70px;
  }
`;

export const Auto = styled.span`
  font-size: ${({ theme }) => theme.fontSize.xs};
`;

export const Link = styled.button`
  border: 0;
  background: none;
  padding: 0;
  color: ${({ theme }) => theme.color.accent};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.xs};
  cursor: pointer;
`;

export const Warning = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.warning};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
