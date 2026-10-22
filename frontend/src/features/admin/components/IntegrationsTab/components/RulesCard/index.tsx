import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { History, Pause, Play, Plus, Trash2, Workflow } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../../../components/ui/Button';
import { SettingsCard, SettingsParts as P } from '../../../../../../components/ui/SettingsCard';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import {
  type AutomationRule,
  createRule,
  deleteRule,
  fetchExamples,
  fetchRules,
  fetchRuns,
  integrationKeys,
  updateRule,
} from '../../../../../../services/api/integrations';
import { RuleForm } from './components/RuleForm';
import * as S from './style';

function when(rule: AutomationRule) {
  const t = rule.trigger as { type?: string; event?: string; every?: string; select?: string };
  return t.type === 'schedule' ? `${t.every} · ${t.select}` : String(t.event);
}

function Runs({ rule }: { rule: AutomationRule }) {
  const { t } = useTranslation();
  const { data: runs = [] } = useQuery({
    queryKey: integrationKeys.runs(rule.id),
    queryFn: () => fetchRuns(rule.id),
  });
  if (!runs.length) return <P.Muted>{t('integrations.noRuns')}</P.Muted>;
  return (
    <S.Log aria-label={t('integrations.runs', { name: rule.name })}>
      {runs.map((r) => (
        <li key={r.id}>
          <Badge
            tone={r.status === 'sent' ? 'accent' : r.status === 'failed' ? 'danger' : 'neutral'}
          >
            {t(`integrations.runStatus.${r.status}`)}
          </Badge>
          <span>{r.log.join(' · ')}</span>
        </li>
      ))}
    </S.Log>
  );
}

/** Automation rules: on an event or a schedule, run actions as their author (Folio 5.6). */
export function RulesCard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const errorMessage = useErrorMessage();
  const [adding, setAdding] = useState(false);
  const [open, setOpen] = useState<string | null>(null);
  const { data: rules = [] } = useQuery({ queryKey: integrationKeys.rules, queryFn: fetchRules });
  const { data: examples = [] } = useQuery({
    queryKey: integrationKeys.examples,
    queryFn: fetchExamples,
  });
  const refresh = () => void queryClient.invalidateQueries({ queryKey: integrationKeys.rules });
  const create = useMutation({
    mutationFn: createRule,
    onSuccess: () => {
      setAdding(false);
      refresh();
    },
  });
  const toggle = useMutation({
    mutationFn: (r: AutomationRule) =>
      updateRule(r.id, {
        name: r.name,
        trigger: r.trigger,
        filter: r.filter,
        actions: r.actions,
        active: !r.active,
      }),
    onSuccess: refresh,
  });
  const remove = useMutation({ mutationFn: deleteRule, onSuccess: refresh });
  return (
    <SettingsCard title={t('integrations.rules')} help={t('integrations.rulesHelp')}>
      <P.Rows>
        {rules.map((r) => (
          <div key={r.id}>
            <P.Row>
              <P.Grow>
                <Workflow size={16} />
                <strong>{r.name}</strong>
                <code>{when(r)}</code>
                <small>{r.actions.map((a) => String(a.type)).join(', ')}</small>
                {!r.active && <Badge>{t('integrations.off')}</Badge>}
              </P.Grow>
              <IconButton
                label={t(r.active ? 'integrations.pause' : 'integrations.resume', { name: r.name })}
                onClick={() => toggle.mutate(r)}
              >
                {r.active ? <Pause /> : <Play />}
              </IconButton>
              <IconButton
                label={t('integrations.runs', { name: r.name })}
                onClick={() => setOpen(open === r.id ? null : r.id)}
              >
                <History />
              </IconButton>
              <IconButton
                label={t('integrations.delete', { name: r.name })}
                onClick={() => remove.mutate(r.id)}
              >
                <Trash2 />
              </IconButton>
            </P.Row>
            {open === r.id && <Runs rule={r} />}
          </div>
        ))}
      </P.Rows>
      {adding ? (
        <RuleForm
          examples={examples}
          pending={create.isPending}
          error={create.error ? errorMessage(create.error) : null}
          onCancel={() => setAdding(false)}
          onSave={(body) => create.mutate(body)}
        />
      ) : (
        <Button size="sm" onClick={() => setAdding(true)}>
          <Plus />
          {t('integrations.newRule')}
        </Button>
      )}
    </SettingsCard>
  );
}
