import styled, { keyframes } from 'styled-components';

// Staging: the panel grows out of Radi, with a little overshoot.
const popIn = keyframes`
  from { opacity: 0; transform: translateY(12px) scale(0.6); }
  70% { opacity: 1; transform: translateY(-2px) scale(1.02); }
  to { opacity: 1; transform: none; }
`;

export const Panel = styled.section`
  position: fixed;
  right: 20px;
  bottom: 96px;
  z-index: 60;
  display: flex;
  flex-direction: column;
  width: min(380px, calc(100vw - 32px));
  max-height: min(70vh, 620px);
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: 18px;
  background: ${({ theme }) => theme.color.surface};
  box-shadow: 0 20px 48px rgba(17, 24, 39, 0.22);
  transform-origin: calc(100% - 32px) calc(100% + 40px);
  animation: ${popIn} 0.32s cubic-bezier(0.2, 0.9, 0.3, 1.2);

  @media (prefers-reduced-motion: reduce) {
    animation: none;
  }
`;

export const Head = styled.header`
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid ${({ theme }) => theme.color.border};

  div {
    display: flex;
    flex-direction: column;
    line-height: 1.25;
  }

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Close = styled.button`
  display: grid;
  place-items: center;
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 50%;
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.text};
  cursor: pointer;
`;

export const Messages = styled.div`
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px 14px;
  overflow-y: auto;
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Bubble = styled.div<{ $mine: boolean }>`
  align-self: ${({ $mine }) => ($mine ? 'flex-end' : 'flex-start')};
  max-width: 88%;
  padding: 8px 12px;
  border-radius: 14px;
  border-bottom-right-radius: ${({ $mine }) => ($mine ? '4px' : '14px')};
  border-bottom-left-radius: ${({ $mine }) => ($mine ? '14px' : '4px')};
  background: ${({ theme, $mine }) => ($mine ? theme.color.accentFill : theme.color.surface2)};
  color: ${({ theme, $mine }) => ($mine ? theme.color.onAccent : theme.color.text)};
  overflow-wrap: anywhere;

  p,
  ol,
  ul {
    margin: 0 0 6px;
  }

  > :last-child,
  > div > :last-child {
    margin-bottom: 0;
  }
`;

export const Notice = styled.small`
  display: block;
  margin-top: 6px;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Typing = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-style: italic;
`;

export const Suggestions = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: 6px;

  button {
    font: inherit;
    font-size: ${({ theme }) => theme.fontSize.sm};
    padding: 4px 10px;
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: 999px;
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
    cursor: pointer;
  }

  button:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Composer = styled.form`
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 10px 12px;
  border-top: 1px solid ${({ theme }) => theme.color.border};

  textarea {
    flex: 1;
    resize: none;
    padding: 8px 10px;
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: 12px;
    background: ${({ theme }) => theme.color.bg};
    color: ${({ theme }) => theme.color.text};
    font: inherit;
  }

  textarea:focus {
    outline: none;
    border-color: ${({ theme }) => theme.color.accent};
  }
`;

export const Send = styled.button`
  display: grid;
  place-items: center;
  width: 38px;
  height: 38px;
  border: 0;
  border-radius: 50%;
  background: ${({ theme }) => theme.color.accentFill};
  color: ${({ theme }) => theme.color.onAccent};
  cursor: pointer;

  &:disabled {
    opacity: 0.5;
    cursor: default;
  }
`;

export const Hint = styled.p`
  margin: 4px 0 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const ShowMe = styled.button`
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-top: 8px;
  padding: 4px 12px;
  border: 0;
  border-radius: 999px;
  background: ${({ theme }) => theme.color.accentFill};
  color: ${({ theme }) => theme.color.onAccent};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  cursor: pointer;
`;
