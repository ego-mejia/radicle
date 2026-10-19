/** Thin line plant drawings for empty states. */
import { Svg } from './style';

export type Plant = 'seed' | 'sprout' | 'pot';

export function PlantIllustration({
  plant = 'sprout',
  size = 96,
}: {
  plant?: Plant;
  size?: number;
}) {
  return (
    <Svg width={size} height={size} viewBox="0 0 96 96" aria-hidden>
      <path d="M14 78h68" />
      {plant === 'seed' && (
        <>
          <ellipse cx="48" cy="64" rx="10" ry="12" />
          <path className="accent" d="M48 76c0 4-2 6-1 9" />
          <path d="M42 60c2-3 5-4 8-3" />
        </>
      )}
      {plant === 'sprout' && (
        <>
          <path className="accent" d="M48 78V46" />
          <path className="accent" d="M48 56c-12 0-18-7-18-17 11 0 18 6 18 17Z" />
          <path className="accent" d="M48 50c0-12 7-19 19-19 0 11-7 19-19 19Z" />
          <path d="M40 78c0-4 3-7 8-7s8 3 8 7" />
        </>
      )}
      {plant === 'pot' && (
        <>
          <path d="M32 58h32l-4 20H36z" />
          <path d="M30 52h36v6H30z" />
          <path className="accent" d="M48 52V30" />
          <path className="accent" d="M48 40c-9 0-14-5-14-13 8 0 14 5 14 13Z" />
          <path className="accent" d="M48 34c0-8 5-13 13-13 0 8-5 13-13 13Z" />
        </>
      )}
    </Svg>
  );
}
