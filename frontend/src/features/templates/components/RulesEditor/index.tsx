import { Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input, Select, Textarea } from '../../../../components/ui/Input';
import {
  RULE_CATALOG,
  RULE_FIELDS,
  RULE_KINDS,
  defaultConfig,
  type RuleKind,
} from '../../../../lib/rules';
import type { TransitionConf } from '../../../../services/api/types';
import * as S from './style';

type Rule = NonNullable<TransitionConf['rules']>[number];

type Props = {
  rules: Rule[];
  onChange: (rules: Rule[]) => void;
  readOnly: boolean;
  /** Custom field keys offered for field rules, e.g. ["environment"]. */
  customFields: string[];
};

/** Conditions, validators and post-functions of one transition, from the catalog. */
export function RulesEditor({ rules, onChange, readOnly, customFields }: Props) {
  const { t } = useTranslation();
  const fields = [...RULE_FIELDS, ...customFields.map((k) => `cf.${k}`)];
  const update = (index: number, next: Rule) =>
    onChange(rules.map((r, i) => (i === index ? next : r)));
  const add = (kind: RuleKind, ruleType: string) =>
    onChange([...rules, { kind, rule_type: ruleType, config: defaultConfig(ruleType) }]);

  return (
    <S.Wrapper>
      {RULE_KINDS.map((kind) => {
        const types = Object.entries(RULE_CATALOG).filter(([, spec]) => spec.kind === kind);
        return (
          <Field
            key={kind}
            label={t(`rules.kinds.${kind}`)}
            hint={t(`rules.kindHelp.${kind}`)}
            group
          >
            <S.List>
              {rules.map((rule, index) =>
                rule.kind !== kind ? null : (
                  <S.Rule key={index}>
                    <S.Head>
                      <strong>{t(`rules.types.${rule.rule_type}`)}</strong>
                      {!readOnly && (
                        <IconButton
                          label={t('common.remove')}
                          onClick={() => onChange(rules.filter((_, i) => i !== index))}
                        >
                          <Trash2 />
                        </IconButton>
                      )}
                    </S.Head>
                    <RuleConfig
                      rule={rule}
                      fields={fields}
                      readOnly={readOnly}
                      onChange={(config) => update(index, { ...rule, config })}
                    />
                  </S.Rule>
                ),
              )}
              {!readOnly && (
                <S.Add>
                  <Select
                    aria-label={t('rules.add', { kind: t(`rules.kinds.${kind}`) })}
                    value=""
                    onChange={(e) => e.target.value && add(kind, e.target.value)}
                  >
                    <option value="">+ {t('rules.addOne')}</option>
                    {types.map(([type]) => (
                      <option key={type} value={type}>
                        {t(`rules.types.${type}`)}
                      </option>
                    ))}
                  </Select>
                </S.Add>
              )}
            </S.List>
          </Field>
        );
      })}
    </S.Wrapper>
  );
}

type ConfigProps = {
  rule: Rule;
  fields: string[];
  readOnly: boolean;
  onChange: (config: Record<string, unknown>) => void;
};

function RuleConfig({ rule, fields, readOnly, onChange }: ConfigProps) {
  const { t } = useTranslation();
  const config = (rule.config ?? {}) as Record<string, unknown>;
  const params = RULE_CATALOG[rule.rule_type]?.params ?? [];
  const set = (key: string, value: unknown) => onChange({ ...config, [key]: value });
  if (!params.length) return <S.Muted>{t(`rules.help.${rule.rule_type}`)}</S.Muted>;
  return (
    <S.Params>
      {params.includes('roles') && (
        <S.Checks>
          {['admin', 'member', 'viewer'].map((role) => {
            const roles = (config.roles as string[]) ?? [];
            return (
              <label key={role}>
                <input
                  type="checkbox"
                  disabled={readOnly}
                  checked={roles.includes(role)}
                  onChange={() =>
                    set(
                      'roles',
                      roles.includes(role) ? roles.filter((r) => r !== role) : [...roles, role],
                    )
                  }
                />
                {t(`projects.roles.${role}`)}
              </label>
            );
          })}
        </S.Checks>
      )}
      {params.includes('kind') && (
        <Select
          aria-label={t('rules.userKind')}
          value={String(config.kind ?? 'human')}
          disabled={readOnly}
          onChange={(e) => set('kind', e.target.value)}
        >
          <option value="human">{t('rules.humans')}</option>
          <option value="agent">{t('rules.agents')}</option>
        </Select>
      )}
      {params.includes('field') && (
        <Select
          aria-label={t('rules.field')}
          value={String(config.field ?? '')}
          disabled={readOnly}
          onChange={(e) => set('field', e.target.value)}
        >
          {fields.map((f) => (
            <option key={f} value={f}>
              {f.startsWith('cf.') ? f : t(`rules.fields.${f}`)}
            </option>
          ))}
        </Select>
      )}
      {params.includes('value') && (
        <Input
          aria-label={t('rules.value')}
          placeholder={t('rules.value')}
          value={String(config.value ?? '')}
          disabled={readOnly}
          onChange={(e) => set('value', e.target.value)}
        />
      )}
      {params.includes('tag') && (
        <Input
          aria-label={t('rules.tag')}
          placeholder="tag"
          value={String(config.tag ?? '')}
          disabled={readOnly}
          onChange={(e) => set('tag', e.target.value)}
        />
      )}
      {params.includes('template') && (
        <Textarea
          aria-label={t('rules.template')}
          rows={2}
          value={String(config.template ?? '')}
          disabled={readOnly}
          onChange={(e) => set('template', e.target.value)}
        />
      )}
    </S.Params>
  );
}
