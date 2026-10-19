import styled from 'styled-components';

export const Circle = styled.span<{ $size: number; $hue: number; $agent: boolean }>`
  display: inline-grid;
  place-items: center;
  flex: none;
  width: ${({ $size }) => $size}px;
  height: ${({ $size }) => $size}px;
  border-radius: ${({ $agent, theme }) => ($agent ? theme.radius.sm : theme.radius.full)};
  background: hsl(
    ${({ $hue }) => $hue} 45% ${({ theme }) => (theme.mode === 'dark' ? '28%' : '86%')}
  );
  color: hsl(${({ $hue }) => $hue} 50% ${({ theme }) => (theme.mode === 'dark' ? '82%' : '28%')});
  font-size: ${({ $size }) => Math.round($size * 0.42)}px;
  font-weight: 700;
  line-height: 1;
  text-transform: uppercase;

  svg {
    width: ${({ $size }) => Math.round($size * 0.6)}px;
    height: ${({ $size }) => Math.round($size * 0.6)}px;
  }
`;
