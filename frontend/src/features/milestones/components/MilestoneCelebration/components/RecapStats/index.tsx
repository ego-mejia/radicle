import { Avatar } from '../../../../../../components/ui/Avatar';
import type { MilestoneRecap } from '../../../../../../services/api/types';
import type { CardStat } from '../../../../lib/celebrate';
import * as S from './style';

type Props = { recap: MilestoneRecap; stats: CardStat[]; team: string };

/** The milestone's numbers as tiles, and the faces behind them. */
export function RecapStats({ recap, stats, team }: Props) {
  return (
    <>
      <S.Grid>
        {stats.map((stat, i) => (
          <S.Tile key={stat.label} $lead={i === 0}>
            <S.Value>{stat.value}</S.Value>
            <S.Label>{stat.label}</S.Label>
          </S.Tile>
        ))}
      </S.Grid>
      <S.Team>
        <S.Faces>
          {recap.people.map((p) => (
            <Avatar
              key={p.handle}
              handle={p.handle}
              name={p.display_name}
              kind={p.kind}
              size={28}
            />
          ))}
        </S.Faces>
        <span>{team}</span>
      </S.Team>
    </>
  );
}
