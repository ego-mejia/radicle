import styled from 'styled-components';

export const Pager = styled.nav`
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: ${({ theme }) => theme.space.md};
  margin-top: ${({ theme }) => theme.space.xxl};

  @media (max-width: 600px) {
    grid-template-columns: minmax(0, 1fr);
  }
`;

export const Card = styled.a<{ $end: boolean }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.lg}`};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface};
  color: ${({ theme }) => theme.color.text};
  text-align: ${({ $end }) => ($end ? 'right' : 'left')};
  text-decoration: none;

  &:hover {
    border-color: ${({ theme }) => theme.color.textMuted};
  }

  b {
    font-size: ${({ theme }) => theme.fontSize.lg};
    overflow-wrap: anywhere;
  }
`;

export const Label = styled.span`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: ${({ theme }) => theme.fontSize.xs};
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};
`;
