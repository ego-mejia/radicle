import styled from 'styled-components';
import { themes, type ThemeMode } from '../../../../../../styles/theme';

export const Row = styled.div`
  display: grid;
  grid-template-columns: 1fr 120px;
  gap: ${({ theme }) => theme.space.md};
`;

export const Split = styled.div`
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: ${({ theme }) => theme.space.md};

  @media (max-width: 720px) {
    grid-template-columns: 1fr;
  }
`;

export const Code = styled.textarea`
  width: 100%;
  min-height: 360px;
  padding: ${({ theme }) => theme.space.sm};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ theme }) => theme.color.surface2};
  color: ${({ theme }) => theme.color.text};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.sm};
  resize: vertical;
`;

export const Preview = styled.div`
  display: grid;
  align-content: start;
  gap: ${({ theme }) => theme.space.xs};
`;

export const PreviewBar = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
`;

export const Modes = styled.div`
  display: flex;
  gap: 2px;

  button {
    padding: 2px ${({ theme }) => theme.space.sm};
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.sm};
    background: transparent;
    color: ${({ theme }) => theme.color.textMuted};
    font-size: ${({ theme }) => theme.fontSize.xs};
    cursor: pointer;
  }

  button[aria-pressed='true'] {
    background: ${({ theme }) => theme.color.accentSoft};
    color: ${({ theme }) => theme.color.text};
  }
`;

// The preview's backdrop is the page in the chosen mode, not the panel's.
export const Stage = styled.div<{ $mode: ThemeMode }>`
  padding: ${({ theme }) => theme.space.sm};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.sm};
  background: ${({ $mode }) => themes[$mode].color.bg};
  max-height: 520px;
  overflow: auto;
`;

export const Size = styled.p<{ $over: boolean }>`
  margin: 0;
  color: ${({ theme, $over }) => ($over ? theme.color.danger : theme.color.textMuted)};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Notes = styled.ul<{ $tone: 'danger' | 'warning' }>`
  margin: 0;
  padding-left: ${({ theme }) => theme.space.lg};
  color: ${({ theme, $tone }) => theme.color[$tone]};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Ok = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.accent};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
