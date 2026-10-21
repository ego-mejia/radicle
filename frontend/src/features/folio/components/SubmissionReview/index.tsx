import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Check, X } from 'lucide-react';
import { Fragment, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Textarea } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  type FolioSubmissionDetail,
  approveSubmission,
  fetchSubmission,
  folioKeys,
  rejectSubmission,
} from '../../../../services/api/folio';
import { Tabs } from '../../../../components/ui/Tabs';
import { DiffView } from '../DiffView';
import { DocContent } from '../DocContent';
import type { DocNode } from '../DocContent/anchors';
import { valueText } from '../DiffView/text';
import * as S from './style';

const SHOWN = ['description', 'doc_type', 'labels', 'owner', 'audiences', 'language'];

type Props = { id: string; canDecide: boolean };

function asDiff(s: FolioSubmissionDetail) {
  const title = s.changes.find((c) => c.field === 'title') ?? null;
  return {
    from_version: s.current_version ?? 0,
    to_version: s.version ?? (s.current_version ?? 0) + 1,
    title,
    metadata: s.changes.filter((c) => c.field !== 'title'),
    blocks: s.blocks,
  };
}

/** One submission: what the agent sent, against what is published, and the decision. */
export function SubmissionReview({ id, canDecide }: Props) {
  const { t, i18n } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const queryClient = useQueryClient();
  const [rejecting, setRejecting] = useState(false);
  const [view, setView] = useState<'changes' | 'preview'>('changes');
  const [comment, setComment] = useState('');
  const { data: s } = useQuery({
    queryKey: folioKeys.submission(id),
    queryFn: () => fetchSubmission(id),
  });
  const done = (message: string) => {
    void queryClient.invalidateQueries({ queryKey: ['folio', 'submissions'] });
    void queryClient.invalidateQueries({ queryKey: folioKeys.submission(id) });
    toast(message);
  };
  const approve = useMutation({
    mutationFn: () => approveSubmission(id),
    onSuccess: (v) => done(t('folio.approvals.approved', { number: v.number })),
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const reject = useMutation({
    mutationFn: () => rejectSubmission(id, comment.trim()),
    onSuccess: () => {
      setRejecting(false);
      setComment('');
      done(t('folio.approvals.rejected'));
    },
  });

  if (!s) return <PageSpinner />;
  const date = (iso: string) =>
    new Date(iso).toLocaleString(i18n.language, { dateStyle: 'medium', timeStyle: 'short' });
  return (
    <S.Panel aria-label={s.title}>
      <h2>{s.title}</h2>
      <S.Meta>
        {t('folio.approvals.sentBy', { who: s.submitted_by, date: date(s.created_at) })}{' '}
        <Badge tone={s.status === 'pending' ? 'warning' : 'neutral'}>
          {t(`folio.approvals.status.${s.status}`)}
        </Badge>
      </S.Meta>
      {s.change_note && <S.Note>{s.change_note}</S.Note>}
      {s.review_comment && (
        <S.Note>
          {t('folio.approvals.reviewComment', { who: s.reviewed_by ?? '' })} {s.review_comment}
        </S.Note>
      )}
      <S.Fields>
        {SHOWN.map((field) => (
          <Fragment key={field}>
            <dt>{t(`folio.history.fields.${field}`)}</dt>
            <dd>{valueText(s.metadata[field])}</dd>
          </Fragment>
        ))}
      </S.Fields>
      <S.Meta>
        {s.current_version
          ? t('folio.approvals.against', { number: s.current_version })
          : t('folio.approvals.firstVersion')}
      </S.Meta>
      <Tabs
        label={t('folio.approvals.view')}
        value={view}
        onChange={setView}
        tabs={[
          { id: 'changes', label: t('folio.approvals.changes') },
          { id: 'preview', label: t('folio.approvals.preview') },
        ]}
      />
      {view === 'changes' ? (
        <DiffView diff={asDiff(s)} />
      ) : (
        <DocContent doc={s.content_json as DocNode} />
      )}
      {canDecide && s.status === 'pending' && (
        <S.Actions>
          <Button variant="primary" onClick={() => approve.mutate()} disabled={approve.isPending}>
            <Check aria-hidden />
            {t('folio.approvals.approve')}
          </Button>
          <Button variant="danger" onClick={() => setRejecting(true)}>
            <X aria-hidden />
            {t('folio.approvals.reject')}
          </Button>
        </S.Actions>
      )}
      <Modal
        open={rejecting}
        onOpenChange={setRejecting}
        title={t('folio.approvals.rejectTitle')}
        footer={
          <>
            <Button onClick={() => setRejecting(false)}>{t('common.cancel')}</Button>
            <Button
              variant="danger"
              disabled={!comment.trim() || reject.isPending}
              onClick={() => reject.mutate()}
            >
              {t('folio.approvals.reject')}
            </Button>
          </>
        }
      >
        <Field label={t('folio.approvals.comment')} hint={t('folio.approvals.commentHint')}>
          <Textarea value={comment} onChange={(e) => setComment(e.target.value)} rows={4} />
        </Field>
        {reject.error && <S.Error role="alert">{errorMessage(reject.error)}</S.Error>}
      </Modal>
    </S.Panel>
  );
}
