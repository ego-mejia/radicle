import * as S from './style';

export type Card = { label: string; value: React.ReactNode; tone?: 'warning' | 'accent' };

/** Big numbers: the summary of a report. */
export function SummaryCards({ cards }: { cards: Card[] }) {
  return (
    <S.Grid>
      {cards.map((c) => (
        <S.Card key={c.label} $tone={c.tone}>
          <dt>{c.label}</dt>
          <dd>{c.value}</dd>
        </S.Card>
      ))}
    </S.Grid>
  );
}
