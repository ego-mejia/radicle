import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchMilestoneDocs, ticketKeys } from '../../../../services/api/folioTickets';
import * as S from './style';

type Props = { project: string; milestone: string };

/** The Folio docs that name this milestone in their metadata (Folio 4.4), as far as you
 * may see them. Hidden when there are none or you have no access to Folio. */
export function MilestoneDocs({ project, milestone }: Props) {
  const { t } = useTranslation();
  const { data } = useQuery({
    queryKey: ticketKeys.milestoneDocs(`${project}:${milestone}`),
    queryFn: () => fetchMilestoneDocs(project, milestone),
    retry: false,
  });
  if (!data?.length) return null;
  return (
    <S.Box aria-label={t('milestones.docs', { name: milestone })}>
      <S.Title>{t('milestones.docsTitle', { count: data.length })}</S.Title>
      <S.List>
        {data.map((doc) => (
          <li key={doc.node.id}>
            <Link
              to="/folio/p/$page"
              params={{ page: doc.url.replace(/^\/folio\/p\//, '') }}
              title={doc.description ?? undefined}
            >
              <FileText size={14} aria-hidden />
              <span>{doc.node.title}</span>
            </Link>
            <S.Meta>{doc.space}</S.Meta>
          </li>
        ))}
      </S.List>
    </S.Box>
  );
}
