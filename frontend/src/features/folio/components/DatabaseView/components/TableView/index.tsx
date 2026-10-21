import type { DbColumn, DbRow } from '../../../../../../services/api/folioDatabases';
import { DbValue } from '../../../DbValue';
import * as S from './style';

type Props = { columns: DbColumn[]; rows: DbRow[] };

/** Rows as a table, one column per visible column. */
export function TableView({ columns, rows }: Props) {
  return (
    <S.Scroll>
      <S.Table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col">
                {c.name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {columns.map((c) => (
                <td key={c.key}>
                  <DbValue column={c} value={row.values[c.key]} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </S.Table>
    </S.Scroll>
  );
}
