import styled from 'styled-components';

export const Doc = styled.div<{ $size: 'regular' | 'large' }>`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.lg};
  min-width: 0;
  color: ${({ theme }) => theme.color.text};
  font-size: ${({ $size }) => ($size === 'large' ? '19px' : '17px')};
  line-height: 1.75;

  /* The section a chat citation or a search result opened (useCitedSection). */
  [data-cited='true'] {
    border-radius: ${({ theme }) => theme.radius.md};
    background: ${({ theme }) => theme.color.accentSoft};
    box-shadow: 0 0 0 6px ${({ theme }) => theme.color.accentSoft};
    transition: background 0.4s ease;
  }

  p,
  ul,
  ol,
  blockquote,
  pre,
  figure,
  table {
    margin: 0;
  }

  a {
    color: ${({ theme }) => theme.color.accent};
  }
`;

export const Flow = styled.div`
  display: flex;
  flex-direction: column;
  gap: ${({ theme }) => theme.space.sm};
  min-width: 0;
`;

export const Heading = styled.h2<{ $level: number }>`
  margin: ${({ theme }) => theme.space.lg} 0 0;
  font-weight: 700;
  letter-spacing: -0.015em;
  line-height: 1.25;
  scroll-margin-top: 80px;
  font-size: ${({ $level }) => ['34px', '26px', '21px', '18px'][$level - 1] ?? '18px'};
`;

export const Quote = styled.blockquote`
  padding-left: ${({ theme }) => theme.space.lg};
  border-left: 3px solid ${({ theme }) => theme.color.accent};
  color: ${({ theme }) => theme.color.textMuted};
`;

export const Pre = styled.pre`
  font-family: ${({ theme }) => theme.fonts.mono};
  font-size: 14px;
  line-height: 1.7;
  background: ${({ theme }) => theme.color.surface2};
  border: 1px solid ${({ theme }) => theme.color.border};
  border-radius: ${({ theme }) => theme.radius.lg};
  padding: ${({ theme }) => `${theme.space.lg} ${theme.space.xl}`};
  overflow-x: auto;
`;

export const Rule = styled.hr`
  width: 100%;
  border: 0;
  border-top: 1px solid ${({ theme }) => theme.color.border};
`;

export const TableWrap = styled.div`
  overflow-x: auto;
`;

export const Table = styled.table`
  border-collapse: collapse;
  width: 100%;
  font-size: 0.9em;

  th,
  td {
    border: 1px solid ${({ theme }) => theme.color.border};
    padding: ${({ theme }) => `${theme.space.sm} ${theme.space.md}`};
    text-align: left;
    vertical-align: top;
  }

  th {
    background: ${({ theme }) => theme.color.surface2};
    font-weight: 600;
  }
`;

export const Tasks = styled.ul`
  list-style: none;
  padding-left: 0;

  li {
    display: flex;
    gap: ${({ theme }) => theme.space.sm};
    align-items: baseline;
  }
`;
