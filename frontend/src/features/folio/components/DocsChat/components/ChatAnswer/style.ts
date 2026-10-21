import styled from 'styled-components';

export const Answer = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  min-width: 0;
`;

export const Warning = styled.p`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.xs};
  margin: 0;
  color: ${({ theme }) => theme.color.warning};
  font-size: ${({ theme }) => theme.fontSize.sm};

  svg {
    width: 14px;
    height: 14px;
    flex: none;
  }
`;

export const Sources = styled.ol`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  margin: 0;
  padding: 0;
  list-style: none;
`;

export const Source = styled.li<{ $outdated: boolean }>`
  > a {
    display: flex;
    align-items: baseline;
    gap: ${({ theme }) => theme.space.sm};
    padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
    border: 1px solid
      ${({ theme, $outdated }) => ($outdated ? theme.color.warning : theme.color.border)};
    border-radius: ${({ theme }) => theme.radius.md};
    background: ${({ theme }) => theme.color.surface};
    color: ${({ theme }) => theme.color.text};
    font-size: ${({ theme }) => theme.fontSize.sm};
    text-decoration: none;
    overflow-wrap: anywhere;
  }

  > a:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }
`;

export const N = styled.span`
  flex: none;
  color: ${({ theme }) => theme.color.accent};
  font-family: ${({ theme }) => theme.fonts.mono};
  font-weight: 600;
`;

export const Section = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Feedback = styled.div`
  display: flex;
  gap: ${({ theme }) => theme.space.xs};
`;

export const Note = styled.form`
  display: flex;
  gap: ${({ theme }) => theme.space.sm};
`;

export const NoteInput = styled.input`
  flex: 1;
  min-width: 0;
  padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  font: inherit;
  font-size: ${({ theme }) => theme.fontSize.sm};
`;
