import { Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../../../components/ui/Button';
import type { DbColumn, DbRow } from '../../../../../../services/api/folioDatabases';
import { DbCell } from '../../../DbCell';
import * as S from './style';
import { columnName } from '../../labels';

type Props = {
  columns: DbColumn[];
  rows: DbRow[];
  /** Editors change values in place and delete rows; readers only see them. */
  onChange?: (row: DbRow, key: string, value: unknown) => void;
  onDelete?: (row: DbRow) => void;
};

/** Rows as a table, one column per visible column. */
export function TableView({ columns, rows, onChange, onDelete }: Props) {
  const { t } = useTranslation();
  return (
    <S.Scroll>
      <S.Table>
        <thead>
          <tr>
            {columns.map((c) => (
              <th key={c.key} scope="col">
                {columnName(c, t)}
              </th>
            ))}
            {onDelete && <th aria-label={t('folio.db.actions')} />}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.id}>
              {columns.map((c) => (
                <td key={c.key}>
                  <DbCell
                    column={c}
                    value={row.values[c.key]}
                    onChange={onChange && ((value) => onChange(row, c.key, value))}
                  />
                </td>
              ))}
              {onDelete && (
                <S.Actions>
                  <IconButton label={t('folio.db.deleteRow')} onClick={() => onDelete(row)}>
                    <Trash2 />
                  </IconButton>
                </S.Actions>
              )}
            </tr>
          ))}
        </tbody>
      </S.Table>
    </S.Scroll>
  );
}
