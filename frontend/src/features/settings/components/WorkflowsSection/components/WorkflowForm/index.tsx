import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { Tabs } from '../../../../../../components/ui/Tabs';
import { removedStatuses, toConf, workflowErrors } from '../../../../../../lib/workflow';
import { type Mappings, putWorkflow } from '../../../../../../services/api/templates';
import {
  TICKET_TYPES,
  type ProjectDetail,
  type TicketType,
  type WorkflowConf,
} from '../../../../../../services/api/types';
import { MappingDialog } from '../../../../../templates/components/MappingDialog';
import { WorkflowEditor } from '../../../../../templates/components/WorkflowEditor';
import { useSettingsMutation } from '../../../../hooks/useSettingsMutation';
import { useToast } from '../../../../../../hooks/useToast';
import * as S from './style';

function omit<T>(record: Record<string, T>, key: string): Record<string, T> {
  const next = { ...record };
  delete next[key];
  return next;
}

/** Workflow editor for an independent project: one type at a time, saved with PUT. */
export function WorkflowForm({ project }: { project: ProjectDetail }) {
  const { t } = useTranslation();
  const toast = useToast();
  const [type, setType] = useState<TicketType>('task');
  const original = toConf(project.workflows.find((w) => w.type === type)!);
  const [draft, setDraft] = useState<Record<string, WorkflowConf>>({});
  const value = draft[type] ?? original;
  const dirty = JSON.stringify(value) !== JSON.stringify(original);
  const [mapping, setMapping] = useState(false);
  const save = useSettingsMutation(
    project.key,
    (mappings: Mappings | null) => putWorkflow(project.key, type, value, mappings),
    () => {
      setMapping(false);
      setDraft((prev) => omit(prev, type));
      toast(t('profile.saved'));
    },
  );
  const removed = removedStatuses(original, value);

  return (
    <S.Stack>
      <Tabs
        label={t('settings.workflows')}
        value={type}
        onChange={setType}
        tabs={TICKET_TYPES.map((id) => ({ id, label: t(`ticket.types.${id}`) }))}
      />
      <WorkflowEditor
        key={type}
        value={value}
        onChange={(next) => setDraft({ ...draft, [type]: next })}
      />
      <S.Actions>
        <Button disabled={!dirty} onClick={() => setDraft((prev) => omit(prev, type))}>
          {t('templates.discard')}
        </Button>
        <Button
          variant="primary"
          disabled={!dirty || workflowErrors(value).length > 0 || save.isPending}
          onClick={() => (removed.length ? setMapping(true) : save.mutate(null))}
        >
          {t('common.save')}
        </Button>
      </S.Actions>
      {mapping && (
        <MappingDialog
          removed={removed.map((status) => ({ type, status }))}
          targets={{ [type]: value.statuses }}
          pending={save.isPending}
          onConfirm={(mappings) => save.mutate((mappings[type] as Record<string, string>) ?? {})}
          onClose={() => setMapping(false)}
        />
      )}
    </S.Stack>
  );
}
