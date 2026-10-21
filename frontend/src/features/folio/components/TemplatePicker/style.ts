import styled, { css } from 'styled-components';

export const Wrap = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.md};
`;

export const Grid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: ${({ theme }) => theme.space.sm};
`;

export const Card = styled.button<{ $active: boolean }>`
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: ${({ theme }) => theme.space.xs};
  min-height: 96px;
  padding: ${({ theme }) => theme.space.md};
  text-align: left;
  font: inherit;
  color: ${({ theme }) => theme.color.text};
  background: ${({ theme }) => theme.color.surface};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  cursor: pointer;

  &:hover {
    border-color: ${({ theme }) => theme.color.accent};
  }
  ${({ $active, theme }) =>
    $active &&
    css`
      border-color: ${theme.color.accent};
      background: ${theme.color.accentSoft};
    `}
`;

export const Icon = styled.span`
  font-size: ${({ theme }) => theme.fontSize.xl};
  line-height: 1;
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Name = styled.span`
  font-weight: 600;
  font-size: ${({ theme }) => theme.fontSize.md};
`;

export const Description = styled.span`
  font-size: ${({ theme }) => theme.fontSize.sm};
  color: ${({ theme }) => theme.color.textMuted};
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
`;

export const Preview = styled.section`
  max-height: 260px;
  overflow: auto;
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.lg}`};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  background: ${({ theme }) => theme.color.surface2};
`;

export const Outline = styled.ul`
  margin: 0;
  padding-left: ${({ theme }) => theme.space.lg};
  list-style: none;
  font-size: ${({ theme }) => theme.fontSize.sm};
  line-height: 1.8;

  ${Preview} > & {
    padding-left: 0;
  }
`;
