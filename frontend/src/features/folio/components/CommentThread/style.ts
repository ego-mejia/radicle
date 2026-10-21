import styled, { css } from 'styled-components';

export const Thread = styled.article<{ $resolved: boolean }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.lg};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  opacity: ${({ $resolved }) => ($resolved ? 0.75 : 1)};
`;

export const Quote = styled.blockquote<{ $orphaned: boolean }>`
  margin: 0;
  padding: ${({ theme }) => `${theme.space.xs} ${theme.space.md}`};
  border-left: 3px solid
    ${({ theme, $orphaned }) => ($orphaned ? theme.color.warning : theme.color.accent)};
  background: ${({ theme }) => theme.color.accentSoft};
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ theme }) => theme.fontSize.md};
  ${({ $orphaned }) =>
    $orphaned &&
    css`
      text-decoration: line-through;
    `}
`;

export const Orphan = styled.span`
  display: block;
  margin-bottom: ${({ theme }) => theme.space.xs};
  color: ${({ theme }) => theme.color.warning};
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  text-decoration: none;
`;

export const Comment = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  font-size: ${({ theme }) => theme.fontSize.lg};
`;

export const Head = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const When = styled.time`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Tools = styled.span`
  margin-left: auto;
  display: inline-flex;
  gap: ${({ theme }) => theme.space.xs};
`;

export const Icon = styled.button`
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: ${({ theme }) => theme.radius.md};
  background: transparent;
  color: ${({ theme }) => theme.color.textMuted};
  cursor: pointer;

  &:hover {
    background: ${({ theme }) => theme.color.surface2};
    color: ${({ theme }) => theme.color.text};
  }

  svg {
    width: 14px;
    height: 14px;
  }
`;

export const Compose = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
`;

export const Row = styled.div`
  display: flex;
  justify-content: flex-end;
  gap: ${({ theme }) => theme.space.sm};

  svg {
    width: 14px;
    height: 14px;
  }
`;

export const Note = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
