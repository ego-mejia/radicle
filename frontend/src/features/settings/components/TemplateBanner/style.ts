import styled from 'styled-components';

export const Banner = styled.div<{ $linked: boolean }>`
  display: flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.md};
  padding: ${({ theme }) => theme.space.md} ${({ theme }) => theme.space.lg};
  border-radius: ${({ theme }) => theme.radius.lg};
  border: 1px solid ${({ theme, $linked }) => ($linked ? theme.color.accent : theme.color.border)};
  background: ${({ theme, $linked }) => ($linked ? theme.color.accentSoft : theme.color.surface)};

  @media (max-width: 640px) {
    flex-direction: column;
    align-items: flex-start;
  }
`;

export const Text = styled.div`
  flex: 1;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 4px;

  a {
    font-weight: 600;
    color: inherit;
  }
`;

export const Muted = styled.span`
  color: ${({ theme }) => theme.color.textMuted};
  font-size: ${({ theme }) => theme.fontSize.sm};
  width: 100%;

  &:first-of-type {
    width: auto;
  }
`;
