import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Field } from '../../../../../../components/ui/Field';
import { Input, Select } from '../../../../../../components/ui/Input';
import type { ChartData } from '../../../ChartBlock/tableData';
import type { TimelineItem } from '../../../Timeline';
import { chartToText, textToChart, textToTimeline, timelineToText } from './text';
import * as S from './style';

type Attrs = Record<string, unknown>;
type Props = { type: string; attrs: Attrs; onChange: (next: Attrs) => void };

/** The fields of a diagram, formula, chart, timeline, page list or ticket table in the side
 * panel. */
export function BlockFields({ type, attrs, onChange }: Props) {
  const { t } = useTranslation();
  const k = (key: string) => t(`folio.editor.panel.${key}`);
  // Kept as typed; the block gets what the text parses to.
  const [table, setTable] = useState(() => chartToText(attrs.data as ChartData));
  const [milestones, setMilestones] = useState(() => timelineToText(attrs.items as TimelineItem[]));
  const str = (key: string) => (attrs[key] == null ? '' : String(attrs[key]));
  const set = (key: string) => (e: { target: { value: string } }) =>
    onChange({ [key]: e.target.value || null });

  switch (type) {
    case 'diagram':
      return (
        <>
          <Field label={k('source')} hint={k('sourceHint')}>
            <S.Code rows={14} value={str('source')} onChange={set('source')} />
          </Field>
          <Field label={k('caption')}>
            <Input value={str('caption')} onChange={set('caption')} />
          </Field>
        </>
      );
    case 'formula':
    case 'inlineFormula':
      return (
        <Field label={k('latex')}>
          <S.Code rows={4} value={str('latex')} onChange={set('latex')} />
        </Field>
      );
    case 'chart':
      return (
        <>
          <S.Row>
            <Field label={k('title')}>
              <Input value={str('title')} onChange={set('title')} />
            </Field>
            <Field label={k('kind')}>
              <Select value={str('kind')} onChange={set('kind')}>
                {['bar', 'line', 'area', 'pie'].map((kind) => (
                  <option key={kind} value={kind}>
                    {k(`kinds.${kind}`)}
                  </option>
                ))}
              </Select>
            </Field>
          </S.Row>
          <Field label={k('dataFrom')}>
            <Select
              value={attrs.source === 'table' ? 'table' : 'own'}
              onChange={(e) =>
                onChange(
                  e.target.value === 'table'
                    ? { source: 'table', data: null }
                    : { source: null, data: textToChart(table) },
                )
              }
            >
              <option value="own">{k('dataOwn')}</option>
              <option value="table">{k('dataTable')}</option>
            </Select>
          </Field>
          {attrs.source === 'table' ? null : (
            <Field label={k('data')} hint={k('dataHint')}>
              <S.Code
                rows={8}
                value={table}
                onChange={(e) => {
                  setTable(e.target.value);
                  onChange({ data: textToChart(e.target.value) });
                }}
              />
            </Field>
          )}
        </>
      );
    case 'timeline':
      return (
        <Field label={k('milestones')} hint={k('milestonesHint')}>
          <S.Code
            rows={10}
            value={milestones}
            onChange={(e) => {
              setMilestones(e.target.value);
              onChange({ items: textToTimeline(e.target.value) });
            }}
          />
        </Field>
      );
    case 'pageList':
      return (
        <>
          <Field label={k('label')}>
            <Input
              value={str('label')}
              onChange={(e) => onChange({ label: e.target.value.replace(/^#/, '').toLowerCase() })}
            />
          </Field>
          <Field label={k('space')} hint={k('spaceHint')}>
            <Input value={str('space')} onChange={set('space')} />
          </Field>
          <S.Row>
            <Field label={k('order')}>
              <Select value={str('order') || 'newest'} onChange={set('order')}>
                <option value="newest">{k('newest')}</option>
                <option value="title">{k('byTitle')}</option>
              </Select>
            </Field>
            <Field label={k('limit')}>
              <Input
                type="number"
                min={1}
                max={50}
                value={str('limit')}
                onChange={(e) =>
                  onChange({
                    limit: e.target.value ? Math.min(50, Math.max(1, +e.target.value)) : null,
                  })
                }
              />
            </Field>
          </S.Row>
        </>
      );
    case 'ticketProgress':
      return (
        <Field label={k('title')}>
          <Input value={str('title')} onChange={set('title')} />
        </Field>
      );
    case 'ticketTable':
      return (
        <>
          <Field label={k('title')}>
            <Input value={str('title')} onChange={set('title')} />
          </Field>
          <Field label={k('rql')} hint={k('rqlHint')}>
            <S.Code
              rows={3}
              value={str('rql')}
              onChange={(e) => onChange({ rql: e.target.value })}
            />
          </Field>
          <Field label={k('limit')}>
            <Input
              type="number"
              min={1}
              max={100}
              value={str('limit')}
              onChange={(e) =>
                onChange({
                  limit: e.target.value ? Math.min(100, Math.max(1, +e.target.value)) : null,
                })
              }
            />
          </Field>
        </>
      );
    default:
      return null;
  }
}
