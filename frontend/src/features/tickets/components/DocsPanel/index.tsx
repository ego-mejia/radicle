import { useQuery } from '@tanstack/react-query';
import { Link } from '@tanstack/react-router';
import { FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchTicketDocs, ticketKeys } from '../../../../services/api/folioTickets';
import { Section, SectionParts as S } from '../Section';
import * as D from './style';

/** The Folio docs linked to this ticket that you may see (Folio 4.1): they mention it,
 * created it from their text, or were linked by hand. Hidden without access to Folio. */
export function DocsPanel({ ticketKey }: { ticketKey: string }) {
  const { t } = useTranslation();
  const { data } = useQuery({
    queryKey: ticketKeys.docs(ticketKey),
    queryFn: () => fetchTicketDocs(ticketKey),
    retry: false,
  });
  if (!data) return null;
  return (
    <Section title={t('ticket.docs.title')}>
      {data.length === 0 ? <S.Muted>{t('ticket.docs.none')}</S.Muted> : null}
      {data.map((doc) => {
        const [path = '', hash] = doc.url.split('#');
        return (
          <S.Row key={`${doc.node.id}-${doc.kind}-${doc.anchor ?? ''}`}>
            <Link
              to="/folio/p/$page"
              params={{ page: path.replace(/^\/folio\/p\//, '') }}
              hash={hash}
            >
              <FileText size={14} aria-hidden />
              <span className="title">{doc.node.title}</span>
            </Link>
            <D.Meta>
              {doc.space} · {t(`ticket.docs.kinds.${doc.kind}`)}
            </D.Meta>
          </S.Row>
        );
      })}
    </Section>
  );
}
