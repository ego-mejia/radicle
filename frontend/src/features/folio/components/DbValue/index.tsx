import { Link } from '@tanstack/react-router';
import { Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Avatar } from '../../../../components/ui/Avatar';
import { formatDate } from '../../../../lib/format';
import type { DbColumn } from '../../../../services/api/folioDatabases';
import * as S from './style';

/** The chip of a select's choice, in its color. */
export function Choice({ column, value }: { column: DbColumn; value: string }) {
  const color = column.options.choices?.find((c) => c.value === value)?.color ?? 'grey';
  return <S.Chip $color={color}>{value}</S.Chip>;
}

function host(url: string): string {
  try {
    return new URL(url).host;
  } catch {
    return url;
  }
}

/** A row's value for a column, shown by its type. Empty values show nothing. */
export function DbValue({ column, value }: { column: DbColumn; value: unknown }) {
  const { t } = useTranslation();
  if (value === null || value === undefined || value === '') return null;
  switch (column.type) {
    case 'number':
      return <S.Num>{Number(value).toLocaleString()}</S.Num>;
    case 'date':
      return <>{formatDate(String(value))}</>;
    case 'select':
      return <Choice column={column} value={String(value)} />;
    case 'multi_select':
      return (
        <S.Chips>
          {(value as string[]).map((v) => (
            <Choice key={v} column={column} value={v} />
          ))}
        </S.Chips>
      );
    case 'person':
      return (
        <S.Person>
          <Avatar handle={String(value)} size={18} />@{String(value)}
        </S.Person>
      );
    case 'checkbox':
      return value ? <Check aria-label={t('folio.db.checked')} /> : null;
    case 'url':
      return (
        <a href={String(value)} target="_blank" rel="noreferrer">
          {host(String(value))}
        </a>
      );
    case 'page':
      return (
        <Link to="/folio/p/$page" params={{ page: String(value) }}>
          {t('folio.db.openPage')}
        </Link>
      );
    default:
      return <>{String(value)}</>;
  }
}
