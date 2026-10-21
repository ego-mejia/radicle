import styled from 'styled-components';
import { type Tone, toned } from '../Inline/style';

export const Panel = styled.aside<{ $tone: Tone }>`
  ${toned};
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  background: ${({ theme, $tone }) =>
    $tone === 'accent' ? theme.color.accentSoft : theme.color.surface};
  border-radius: ${({ theme }) => theme.radius.lg};
  padding: ${({ theme }) => theme.space.lg};
  font-size: 0.94em;
`;

export const Expand = styled.details`
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  padding: ${({ theme }) => `${theme.space.md} ${theme.space.lg}`};

  summary {
    cursor: pointer;
    font-weight: 600;
  }

  &[open] summary {
    margin-bottom: ${({ theme }) => theme.space.sm};
  }
`;

const LAYOUTS: Record<string, string> = {
  two: '1fr 1fr',
  three: '1fr 1fr 1fr',
  sidebar_left: '1fr 2fr',
  sidebar_right: '2fr 1fr',
};

export const Columns = styled.div<{ $layout: string }>`
  display: grid;
  grid-template-columns: ${({ $layout }) => LAYOUTS[$layout] ?? '1fr 1fr'};
  gap: ${({ theme }) => theme.space.xl};

  @media (max-width: 720px) {
    grid-template-columns: 1fr;
  }
`;

const WIDTHS: Record<string, string> = { small: '40%', medium: '65%', large: '100%', full: '100%' };
const ALIGN: Record<string, string> = { left: 'flex-start', right: 'flex-end' };

export const Figure = styled.figure<{ $size: string; $align: string }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  align-items: ${({ $align }) => ALIGN[$align] ?? 'center'};

  img,
  video {
    max-width: ${({ $size }) => WIDTHS[$size] ?? '100%'};
    width: 100%;
    border-radius: ${({ theme }) => theme.radius.lg};
  }

  figcaption {
    font-size: ${({ theme }) => theme.fontSize.md};
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const File = styled.a`
  display: inline-flex;
  align-items: center;
  gap: ${({ theme }) => theme.space.sm};
  align-self: flex-start;
  min-height: 44px;
  padding: 0 ${({ theme }) => theme.space.lg};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  font-size: ${({ theme }) => theme.fontSize.lg};
  text-decoration: none;

  small {
    color: ${({ theme }) => theme.color.textMuted};
  }
`;

export const Toc = styled.nav`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.xs};
  padding: ${({ theme }) => theme.space.lg};
  background: ${({ theme }) => theme.color.surface2};
  border-radius: ${({ theme }) => theme.radius.lg};
  font-size: 0.9em;
`;

export const TocLink = styled.a<{ $depth: number }>`
  padding-left: ${({ $depth }) => `${$depth * 14}px`};
`;

export const Compare = styled.div<{ $sides: number }>`
  display: grid;
  grid-template-columns: repeat(${({ $sides }) => $sides}, minmax(0, 1fr));
  gap: ${({ theme }) => theme.space.md};

  section {
    padding: ${({ theme }) => theme.space.md};
    border: 1px solid ${({ theme }) => theme.color.border};
    border-radius: ${({ theme }) => theme.radius.md};
  }

  h4 {
    margin: 0 0 ${({ theme }) => theme.space.sm};
    padding-bottom: ${({ theme }) => theme.space.xs};
    border-bottom: 2px solid ${({ theme }) => theme.color.accentFill};
  }

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
  }
`;
