import styled, { keyframes } from 'styled-components';

const enter = keyframes`from { opacity: 0; transform: translateY(8px) } to { opacity: 1; transform: none }`;

export const Region = styled.div`
  position: fixed;
  right: 16px;
  bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  z-index: 60;
  max-width: min(380px, calc(100vw - 32px));
`;

export const Item = styled.div<{ $tone: 'info' | 'error' | 'warning' }>`
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid
    ${({ theme, $tone }) =>
      $tone === 'error'
        ? theme.color.danger
        : $tone === 'warning'
          ? theme.color.warning
          : theme.color.border};
  border-left-width: 4px;
  border-left-color: ${({ theme, $tone }) =>
    $tone === 'error'
      ? theme.color.danger
      : $tone === 'warning'
        ? theme.color.warning
        : theme.color.accentFill};
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.15);
  white-space: pre-line;
  animation: ${enter} 0.15s ease-out;
`;

export const Text = styled.div`
  flex: 1;
  font-size: ${({ theme }) => theme.fontSize.md};
`;
