import styled from 'styled-components';

export const Page = styled.main`
  min-height: 100%;
  display: grid;
  place-items: center;
  padding: ${({ theme }) => theme.space.lg};
`;

export const Card = styled.section`
  width: 100%;
  max-width: 440px;
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  padding: ${({ theme }) => theme.space.xl};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
`;

export const Brand = styled.div`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
`;

export const Title = styled.h1`
  margin: 0;
  font-size: ${({ theme }) => theme.fontSize.xl};
  font-weight: 700;
`;

export const Tagline = styled.p`
  margin: 0;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const StatusLine = styled.p<{ $tone: 'ok' | 'error' | 'muted' }>`
  margin: 0;
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  color: ${({ theme, $tone }) => ($tone === 'error' ? theme.color.danger : theme.color.text)};

  &::before {
    content: '';
    width: 8px;
    height: 8px;
    border-radius: ${({ theme }) => theme.radius.full};
    background: ${({ theme, $tone }) =>
      $tone === 'ok'
        ? theme.color.accentFill
        : $tone === 'error'
          ? theme.color.danger
          : theme.color.border};
  }
`;

export const Controls = styled.div`
  display: flex;
  flex-wrap: wrap;
  gap: ${({ theme }) => theme.space.lg};
  padding-top: ${({ theme }) => theme.space.md};
  border-top: 1px solid ${({ theme }) => theme.color.border};
`;

export const Label = styled.label`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
`;

export const Select = styled.select`
  font: inherit;
  color: ${({ theme }) => theme.color.text};
  background: ${({ theme }) => theme.color.surface2};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.md};
  padding: ${({ theme }) => `${theme.space.xs} ${theme.space.sm}`};
`;
