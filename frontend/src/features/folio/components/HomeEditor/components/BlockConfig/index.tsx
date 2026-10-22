import { useQuery } from '@tanstack/react-query';
import { useTranslation } from 'react-i18next';
import { Field } from '../../../../../../components/ui/Field';
import { Input, Select, Textarea } from '../../../../../../components/ui/Input';
import { type HomeLayoutBlock, fetchSpaces, folioKeys } from '../../../../../../services/api/folio';
import { calendarKeys, fetchCalendars } from '../../../../../../services/api/folioCalendars';
import type { BlockError } from '../../errors';
import { NodePicker } from './components/NodePicker';
import * as S from './style';

const LIMITS: Record<string, number> = { posts: 12, query: 20, for_you: 12, most_read: 12 };
const TITLED = ['posts', 'query', 'for_you', 'most_read', 'spaces'];

type Props = {
  block: HomeLayoutBlock;
  errors: BlockError[];
  onChange: (config: Record<string, unknown>) => void;
};

/** The selected block's source: its page, space, label, RQL, how many, or its text. */
export function BlockConfig({ block, errors, onChange }: Props) {
  const { t } = useTranslation();
  const config = block.config as Record<string, unknown>;
  const { data: spaces = [] } = useQuery({
    queryKey: folioKeys.spaces,
    queryFn: fetchSpaces,
    enabled: block.type === 'posts',
  });
  const { data: calendars = [] } = useQuery({
    queryKey: calendarKeys.list(null),
    queryFn: () => fetchCalendars(),
    enabled: block.type === 'calendar',
  });
  const text = (key: string) => (typeof config[key] === 'string' ? (config[key] as string) : '');
  const error = (field: string) => {
    const found = errors.find((e) => e.field === `config.${field}`);
    if (!found) return null;
    return found.position === undefined
      ? found.message
      : t('folio.homeEditor.config.at', { message: found.message, at: found.position + 1 });
  };
  const name = t(`folio.homeEditor.types.${block.type}`);

  return (
    <S.Panel aria-label={t('folio.homeEditor.config.title', { name })}>
      <S.Heading>{t('folio.homeEditor.config.title', { name })}</S.Heading>
      {errors
        .filter((e) => !e.field.startsWith('config.'))
        .map((e) => (
          <S.Problem key={e.message} role="alert">
            {e.message}
          </S.Problem>
        ))}
      {(block.type === 'featured' || block.type === 'announcement') && (
        <NodePicker
          node={text('node') || null}
          error={error('node')}
          onPick={(node) => onChange({ node })}
        />
      )}
      {TITLED.includes(block.type) && (
        <Field label={t('folio.homeEditor.config.blockTitle')}>
          <Input value={text('title')} onChange={(e) => onChange({ title: e.target.value })} />
        </Field>
      )}
      {block.type === 'posts' && (
        <>
          <Field label={t('folio.homeEditor.config.space')}>
            <Select
              value={text('space')}
              onChange={(e) => onChange({ space: e.target.value || null })}
            >
              <option value="">{t('folio.homeEditor.config.anySpace')}</option>
              {spaces.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.name}
                </option>
              ))}
            </Select>
          </Field>
          <Field
            label={t('folio.homeEditor.config.label')}
            hint={t('folio.homeEditor.config.labelHint')}
          >
            <Input
              value={text('label')}
              onChange={(e) => onChange({ label: e.target.value || null })}
            />
          </Field>
          <Field label={t('folio.homeEditor.config.kind')}>
            <Select
              value={config.kind === 'all' ? 'all' : 'posts'}
              onChange={(e) => onChange({ kind: e.target.value })}
            >
              <option value="posts">{t('folio.homeEditor.config.kinds.posts')}</option>
              <option value="all">{t('folio.homeEditor.config.kinds.all')}</option>
            </Select>
          </Field>
        </>
      )}
      {block.type === 'query' && (
        <Field
          label={t('folio.homeEditor.config.rql')}
          hint={t('folio.homeEditor.config.rqlHint')}
          error={error('rql')}
        >
          <Textarea
            rows={3}
            spellCheck={false}
            invalid={Boolean(error('rql'))}
            value={text('rql')}
            onChange={(e) => onChange({ rql: e.target.value })}
          />
        </Field>
      )}
      {LIMITS[block.type] !== undefined && (
        <Field
          label={t('folio.homeEditor.config.limit', { most: LIMITS[block.type] })}
          error={error('limit')}
        >
          <Input
            type="number"
            min={1}
            max={LIMITS[block.type]}
            value={typeof config.limit === 'number' ? config.limit : ''}
            onChange={(e) =>
              onChange({ limit: e.target.value ? Number(e.target.value) : undefined })
            }
          />
        </Field>
      )}
      {block.type === 'text' && (
        <Field label={t('folio.homeEditor.config.markdown')} error={error('markdown')}>
          <Textarea
            rows={8}
            value={text('markdown')}
            onChange={(e) => onChange({ markdown: e.target.value })}
          />
        </Field>
      )}
      {block.type === 'calendar' && (
        <>
          <Field label={t('folio.calendar.block.choose')} error={error('calendar')}>
            <Select
              value={text('calendar')}
              onChange={(e) => onChange({ calendar: e.target.value })}
            >
              <option value="">{t('folio.calendar.block.choose')}</option>
              {calendars.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} · {c.space}
                </option>
              ))}
            </Select>
          </Field>
          <Field label={t('folio.calendar.block.view')}>
            <Select
              value={text('view') || 'month'}
              onChange={(e) => onChange({ view: e.target.value })}
            >
              <option value="month">{t('folio.calendar.show.month')}</option>
              <option value="week">{t('folio.calendar.show.week')}</option>
            </Select>
          </Field>
        </>
      )}
      {block.type === 'search' && <S.Muted>{t('folio.homeEditor.config.nothing')}</S.Muted>}
    </S.Panel>
  );
}
