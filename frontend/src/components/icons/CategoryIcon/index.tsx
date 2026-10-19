/**
 * Status category icons from the plant vocabulary: to do is a seed,
 * in progress a sprout, done a leaf.
 */
import type { Category } from '../../../services/api/types';
import { Svg } from './style';

type Props = { category: Category; size?: number; title?: string };

export function CategoryIcon({ category, size = 14, title }: Props) {
  return (
    <Svg
      $category={category}
      width={size}
      height={size}
      viewBox="0 0 16 16"
      role="img"
      aria-label={title ?? category}
    >
      {category === 'todo' && <ellipse cx="8" cy="8.5" rx="4.5" ry="5.5" />}
      {category === 'in_progress' && (
        <>
          <path d="M8 14V7" />
          <path d="M8 9c-3 0-4.5-2-4.5-4.5C6.5 4.5 8 6 8 9Z" />
          <path d="M8 7.5c0-3 1.8-4.5 4.5-4.5C12.5 6 11 7.5 8 7.5Z" />
        </>
      )}
      {category === 'done' && (
        <>
          <path d="M3 13C3 7 7 3 13 3c0 6-4 10-10 10Z" />
          <path d="M3 13 9 7" />
        </>
      )}
    </Svg>
  );
}
