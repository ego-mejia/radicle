import type { TFunction } from 'i18next';
import type { DbColumn, DbView } from '../../../../services/api/folioDatabases';

/** The server names a new database's first view and column in English; until someone
 * renames them, show those defaults in the reader's language. */
export function viewName(view: Pick<DbView, 'id' | 'name'>, t: TFunction): string {
  return view.id === 'table' && view.name === 'Table' ? t('folio.db.defaultView') : view.name;
}

export function columnName(column: Pick<DbColumn, 'key' | 'name'>, t: TFunction): string {
  return column.key === 'name' && column.name === 'Name'
    ? t('folio.db.defaultColumn')
    : column.name;
}
