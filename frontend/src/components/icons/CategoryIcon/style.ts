import styled from 'styled-components';
import type { Category } from '../../../services/api/types';

export const Svg = styled.svg<{ $category: Category }>`
  flex: none;
  fill: none;
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke: ${({ theme, $category }) =>
    $category === 'todo' ? theme.color.textMuted : theme.color.accent};
`;
