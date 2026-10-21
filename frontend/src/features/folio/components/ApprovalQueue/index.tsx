import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { PageTitle } from '../../../../components/ui/PageTitle';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { Tabs } from '../../../../components/ui/Tabs';
import {
  type SubmissionStatus,
  fetchFolioMe,
  fetchSubmissions,
  folioKeys,
} from '../../../../services/api/folio';
import { SubmissionReview } from '../SubmissionReview';
import * as S from './style';

const STATUSES: SubmissionStatus[] = ['pending', 'approved', 'rejected', 'superseded'];

/** The approval queue (Folio 1.5): admins decide what agents sent; agents see their own. */
export function ApprovalQueue() {
  const { t } = useTranslation();
  const { data: me } = useQuery({ queryKey: folioKeys.me, queryFn: fetchFolioMe });
  const isAdmin = me?.role === 'admin';
  const [status, setStatus] = useState<SubmissionStatus>('pending');
  const [picked, setPicked] = useState<string | null>(null);
  const { data: items } = useQuery({
    queryKey: folioKeys.submissions(status),
    queryFn: () => fetchSubmissions(status),
  });
  const selected = items?.find((s) => s.id === picked) ?? items?.[0];

  return (
    <>
      <PageTitle
        title={t('folio.approvals.title')}
        subtitle={t(isAdmin ? 'folio.approvals.subtitleAdmin' : 'folio.approvals.subtitleMine')}
      />
      <Tabs
        label={t('folio.approvals.filter')}
        value={status}
        onChange={(next) => {
          setStatus(next);
          setPicked(null);
        }}
        tabs={STATUSES.map((s) => ({ id: s, label: t(`folio.approvals.status.${s}`) }))}
      />
      {!items ? (
        <PageSpinner />
      ) : items.length === 0 ? (
        <EmptyState plant="seed" title={t(`folio.approvals.empty.${status}`)} />
      ) : (
        <S.Layout>
          <S.List aria-label={t('folio.approvals.list')}>
            {items.map((s) => (
              <li key={s.id}>
                <S.Item
                  $selected={s.id === selected?.id}
                  aria-current={s.id === selected?.id ? 'true' : undefined}
                  onClick={() => setPicked(s.id)}
                >
                  <strong>{s.title}</strong>
                  <small>
                    {s.submitted_by}
                    {s.change_note && ` · ${s.change_note}`}
                  </small>
                </S.Item>
              </li>
            ))}
          </S.List>
          {selected && <SubmissionReview key={selected.id} id={selected.id} canDecide={isAdmin} />}
        </S.Layout>
      )}
    </>
  );
}
