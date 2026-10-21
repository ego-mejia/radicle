import type { DbColumn, DbRow } from '../../../../../../services/api/folioDatabases';
import { DbValue } from '../../../DbValue';
import * as S from './style';

type Props = { columns: DbColumn[]; rows: DbRow[] };

/** One row's card: the first column as its title, the rest below with their names. */
export function RowCard({ columns, row }: { columns: DbColumn[]; row: DbRow }) {
  const [first, ...rest] = columns;
  return (
    <>
      {first && (
        <S.Title>
          <DbValue column={first} value={row.values[first.key]} />
        </S.Title>
      )}
      <S.Fields>
        {rest
          .filter((c) => row.values[c.key] != null && row.values[c.key] !== '')
          .map((c) => (
            <div key={c.key}>
              <dt>{c.name}</dt>
              <dd>
                <DbValue column={c} value={row.values[c.key]} />
              </dd>
            </div>
          ))}
      </S.Fields>
    </>
  );
}

/** Rows as a grid of cards. */
export function CardsView({ columns, rows }: Props) {
  return (
    <S.Grid>
      {rows.map((row) => (
        <S.Card key={row.id}>
          <RowCard columns={columns} row={row} />
        </S.Card>
      ))}
    </S.Grid>
  );
}
