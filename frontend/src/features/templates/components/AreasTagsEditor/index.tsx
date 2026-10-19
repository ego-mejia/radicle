import { Plus, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input, Select } from '../../../../components/ui/Input';
import type { BlockedPolicy, TemplateConfig } from '../../../../services/api/types';
import * as S from './style';

type Props = {
  config: TemplateConfig;
  onChange: (config: TemplateConfig) => void;
  readOnly: boolean;
};

/** Areas and tags the template adds to its projects. Projects keep their own extras. */
export function AreasTagsEditor({ config, onChange, readOnly }: Props) {
  const { t } = useTranslation();
  const [area, setArea] = useState('');
  const [tag, setTag] = useState('');
  const areas = config.areas ?? [];
  const tags = config.tags ?? [];
  return (
    <S.Columns>
      <Field label={t('settings.areas')} hint={t('templates.areasHint')} group>
        <S.Chips>
          {areas.map((a) => (
            <S.Chip key={a.name}>
              <S.Swatch
                type="color"
                aria-label={`${t('settings.color')} ${a.name}`}
                value={a.color ?? '#9CA3AF'}
                disabled={readOnly}
                onChange={(e) =>
                  onChange({
                    ...config,
                    areas: areas.map((x) =>
                      x.name === a.name ? { ...x, color: e.target.value.toUpperCase() } : x,
                    ),
                  })
                }
              />
              {a.name}
              {!readOnly && (
                <IconButton
                  label={`${t('common.remove')} ${a.name}`}
                  onClick={() =>
                    onChange({ ...config, areas: areas.filter((x) => x.name !== a.name) })
                  }
                >
                  <X />
                </IconButton>
              )}
            </S.Chip>
          ))}
        </S.Chips>
        {!readOnly && (
          <S.Add
            onSubmit={(e) => {
              e.preventDefault();
              const name = area.trim();
              if (!name || areas.some((x) => x.name.toLowerCase() === name.toLowerCase())) return;
              onChange({ ...config, areas: [...areas, { name, color: null }] });
              setArea('');
            }}
          >
            <Input
              aria-label={t('settings.newArea')}
              placeholder={t('settings.newArea')}
              value={area}
              onChange={(e) => setArea(e.target.value)}
            />
            <Button type="submit" size="sm">
              <Plus />
              {t('common.add')}
            </Button>
          </S.Add>
        )}
      </Field>
      <Field label={t('templates.tags')} hint={t('templates.tagsHint')} group>
        <S.Chips>
          {tags.map((x) => (
            <S.Chip key={x}>
              #{x}
              {!readOnly && (
                <IconButton
                  label={`${t('common.remove')} #${x}`}
                  onClick={() => onChange({ ...config, tags: tags.filter((y) => y !== x) })}
                >
                  <X />
                </IconButton>
              )}
            </S.Chip>
          ))}
        </S.Chips>
        {!readOnly && (
          <S.Add
            onSubmit={(e) => {
              e.preventDefault();
              const value = tag.trim().replace(/^#/, '').toLowerCase();
              if (!value || tags.includes(value)) return;
              onChange({ ...config, tags: [...tags, value] });
              setTag('');
            }}
          >
            <Input
              aria-label={t('templates.newTag')}
              placeholder="backlog"
              value={tag}
              onChange={(e) => setTag(e.target.value)}
            />
            <Button type="submit" size="sm">
              <Plus />
              {t('common.add')}
            </Button>
          </S.Add>
        )}
      </Field>
      <Field label={t('templates.blockedPolicy')} hint={t('templates.blockedPolicyHint')}>
        <Select
          value={config.settings?.blocked_policy ?? 'warn'}
          disabled={readOnly}
          onChange={(e) =>
            onChange({
              ...config,
              settings: { ...config.settings, blocked_policy: e.target.value as BlockedPolicy },
            })
          }
        >
          <option value="warn">{t('templates.policy.warn')}</option>
          <option value="enforce">{t('templates.policy.enforce')}</option>
        </Select>
      </Field>
    </S.Columns>
  );
}
