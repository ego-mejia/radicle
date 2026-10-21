import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import { Modal } from '../../../../components/ui/Modal';
import { useToast } from '../../../../hooks/useToast';
import { isApiError } from '../../../../services/api/client';
import { createTicketFromText, ticketKeys } from '../../../../services/api/folioTickets';
import { fetchProject, fetchProjects, projectKeys } from '../../../../services/api/projects';
import * as S from './style';

type Props = {
  nodeId: string;
  /** The selection or action item the ticket is made from. */
  text: string;
  /** The heading anchor of its section, so the ticket links right there. */
  anchor: string | null;
  onClose: () => void;
};

const firstLine = (text: string) => (text.trim().split('\n')[0] ?? '').slice(0, 120);

/** Create a Docket ticket from text in a doc (Folio 4.2): the ticket quotes it and links
 * back to its section, and the doc lists it among its tickets. */
export function CreateTicketDialog({ nodeId, text, anchor, onClose }: Props) {
  const { t } = useTranslation();
  const toast = useToast();
  const queryClient = useQueryClient();
  const [project, setProject] = useState('');
  const [title, setTitle] = useState(() => firstLine(text));
  const [type, setType] = useState<'task' | 'bug' | 'draft'>('task');
  const [area, setArea] = useState('');
  const [milestone, setMilestone] = useState('');
  const projects = useQuery({ queryKey: projectKeys.list(false), queryFn: () => fetchProjects() });
  const chosen = project || projects.data?.[0]?.key || '';
  const detail = useQuery({
    queryKey: projectKeys.detail(chosen),
    queryFn: () => fetchProject(chosen),
    enabled: !!chosen,
  });
  const create = useMutation({
    mutationFn: () =>
      createTicketFromText(nodeId, {
        text,
        anchor,
        project: chosen,
        title: title.trim() || null,
        type,
        area: area || null,
        milestone: milestone || null,
      }),
    onSuccess: (link) => {
      void queryClient.invalidateQueries({ queryKey: ticketKeys.links(nodeId) });
      toast(t('folio.tickets.created', { key: link.ticket?.key ?? '' }));
      onClose();
    },
  });
  const areas = (detail.data?.areas ?? []).filter((a) => !a.archived);
  const milestones = (detail.data?.milestones ?? []).filter((m) => m.status === 'open');

  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('folio.tickets.create')}
      footer={
        <>
          <Button onClick={onClose}>{t('common.cancel')}</Button>
          <Button
            variant="primary"
            disabled={!chosen || create.isPending}
            onClick={() => create.mutate()}
          >
            {t('folio.tickets.createButton')}
          </Button>
        </>
      }
    >
      <S.Form>
        <S.Quote>“{text.trim()}”</S.Quote>
        <Field label={t('folio.tickets.title')}>
          <Input value={title} maxLength={255} onChange={(e) => setTitle(e.target.value)} />
        </Field>
        <S.Row>
          <Field label={t('folio.tickets.project')}>
            <Select
              value={chosen}
              onChange={(e) => {
                setProject(e.target.value);
                setArea('');
                setMilestone('');
              }}
            >
              {(projects.data ?? []).map((p) => (
                <option key={p.key} value={p.key}>
                  {p.key} · {p.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('folio.tickets.type')}>
            <Select value={type} onChange={(e) => setType(e.target.value as typeof type)}>
              {(['task', 'bug', 'draft'] as const).map((kind) => (
                <option key={kind} value={kind}>
                  {t(`folio.tickets.types.${kind}`)}
                </option>
              ))}
            </Select>
          </Field>
        </S.Row>
        <S.Row>
          <Field label={t('folio.tickets.area')} hint={t('folio.tickets.areaHint')}>
            <Select value={area} onChange={(e) => setArea(e.target.value)}>
              <option value="">{t('folio.tickets.none')}</option>
              {areas.map((a) => (
                <option key={a.name} value={a.name}>
                  {a.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('folio.tickets.milestone')}>
            <Select value={milestone} onChange={(e) => setMilestone(e.target.value)}>
              <option value="">{t('folio.tickets.none')}</option>
              {milestones.map((m) => (
                <option key={m.name} value={m.name}>
                  {m.name}
                </option>
              ))}
            </Select>
          </Field>
        </S.Row>
        {create.error ? (
          <S.Error role="alert">
            {isApiError(create.error) ? create.error.message : t('folio.tickets.createFailed')}
          </S.Error>
        ) : null}
      </S.Form>
    </Modal>
  );
}
