import styled from 'styled-components';

export const Toc = styled.nav`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Title = styled.span`
  font-size: ${({ theme }) => theme.fontSize.sm};
  font-weight: 600;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Item = styled.a<{ $depth: number }>`
  font-size: 14px;
  line-height: 1.4;
  text-decoration: none;
  color: ${({ theme }) => theme.color.textMuted};
  padding-left: ${({ $depth }) => `${12 + $depth * 12}px`};
  border-left: 2px solid transparent;

  &:hover {
    color: ${({ theme }) => theme.color.text};
  }

  &[aria-current='location'] {
    font-weight: 600;
    color: ${({ theme }) => theme.color.text};
    border-left-color: ${({ theme }) => theme.color.accent};
    padding-left: ${({ $depth }) => `${10 + $depth * 12}px`};
  }
`;
