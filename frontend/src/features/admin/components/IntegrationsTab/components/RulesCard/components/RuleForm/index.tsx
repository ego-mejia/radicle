import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../../../components/ui/Button';
import { Field, FormError } from '../../../../../../../../components/ui/Field';
import { Input } from '../../../../../../../../components/ui/Input';
import type {
  AutomationExample,
  AutomationRuleInput,
} from '../../../../../../../../services/api/integrations';
import * as S from './style';

type Props = {
  examples: AutomationExample[];
  pending: boolean;
  error: string | null;
  onSave: (body: AutomationRuleInput) => void;
  onCancel: () => void;
};

const pretty = (value: unknown) => JSON.stringify(value, null, 2);

/** A rule from scratch or from an example: trigger and actions as JSON. */
export function RuleForm({ examples, pending, error, onSave, onCancel }: Props) {
  const { t } = useTranslation();
  const [name, setName] = useState('');
  const [space, setSpace] = useState('');
  const [trigger, setTrigger] = useState(pretty({ type: 'event', event: 'page.published' }));
  const [actions, setActions] = useState(pretty([]));
  const [invalid, setInvalid] = useState<string | null>(null);
  const start = (index: string) => {
    const example = examples[Number(index)];
    if (!example) return;
    setName(example.name);
    setTrigger(pretty(example.trigger));
    setActions(pretty(example.actions));
  };
  const submit = () => {
    try {
      const body: AutomationRuleInput = {
        name,
        trigger: JSON.parse(trigger) as AutomationRuleInput['trigger'],
        actions: JSON.parse(actions) as AutomationRuleInput['actions'],
        filter: space ? { space } : {},
        active: true,
      };
      setInvalid(null);
      onSave(body);
    } catch {
      setInvalid(t('integrations.badJson'));
    }
  };
  return (
    <S.Form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
    >
      <S.Grid>
        <Field label={t('integrations.startFrom')}>
          <S.Select defaultValue="" onChange={(e) => start(e.target.value)}>
            <option value="">{t('integrations.blankRule')}</option>
            {examples.map((x, i) => (
              <option key={x.name} value={i}>
                {x.name}
              </option>
            ))}
          </S.Select>
        </Field>
        <Field label={t('integrations.name')}>
          <Input value={name} onChange={(e) => setName(e.target.value)} />
        </Field>
        <Field label={t('integrations.space')} hint={t('integrations.spaceHint')}>
          <Input value={space} onChange={(e) => setSpace(e.target.value)} />
        </Field>
      </S.Grid>
      <Field label={t('integrations.trigger')} hint={t('integrations.triggerHint')}>
        <S.Code rows={4} value={trigger} onChange={(e) => setTrigger(e.target.value)} />
      </Field>
      <Field label={t('integrations.actions')} hint={t('integrations.actionsHint')}>
        <S.Code rows={6} value={actions} onChange={(e) => setActions(e.target.value)} />
      </Field>
      <FormError>{invalid ?? error}</FormError>
      <S.Row>
        <Button type="submit" variant="primary" disabled={pending || !name}>
          {t('common.save')}
        </Button>
        <Button onClick={onCancel}>{t('common.cancel')}</Button>
      </S.Row>
    </S.Form>
  );
}
