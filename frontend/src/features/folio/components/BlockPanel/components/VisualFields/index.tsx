import { useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Field } from '../../../../../../components/ui/Field';
import { Input, Select, Textarea } from '../../../../../../components/ui/Input';
import { useDebounced } from '../../../../../../hooks/useDebounced';
import { checkVisual } from '../../../../../../services/api/folio';
import type { ThemeMode } from '../../../../../../styles/theme';
import { VisualFrame } from '../../../VisualFrame';
import * as S from './style';

export type VisualAttrs = {
  format: 'svg' | 'html';
  code: string;
  title: string | null;
  description: string;
};

type Props = { attrs: VisualAttrs; onChange: (next: Partial<VisualAttrs>) => void };

const LIMIT = 512 * 1024;

/** A visual's editor: code and preview side by side, the preview in light or dark, the
 * size against the 512 KB limit, and what the sandbox would block (from the server). */
export function VisualFields({ attrs, onChange }: Props) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<ThemeMode>('light');
  const size = new TextEncoder().encode(attrs.code).length;
  const checked = useDebounced(attrs, 400);
  const { data: report } = useQuery({
    queryKey: ['folio', 'visual-check', checked],
    queryFn: () => checkVisual({ ...checked, title: checked.title ?? null }),
    retry: false,
  });

  return (
    <>
      <S.Row>
        <Field label={t('folio.editor.panel.title')}>
          <Input
            value={attrs.title ?? ''}
            onChange={(e) => onChange({ title: e.target.value || null })}
          />
        </Field>
        <Field label={t('folio.editor.panel.format')}>
          <Select
            value={attrs.format}
            onChange={(e) => onChange({ format: e.target.value as VisualAttrs['format'] })}
          >
            <option value="svg">SVG</option>
            <option value="html">HTML</option>
          </Select>
        </Field>
      </S.Row>
      <Field
        label={t('folio.editor.panel.description')}
        hint={t('folio.editor.panel.descriptionHint')}
      >
        <Textarea
          rows={2}
          value={attrs.description}
          onChange={(e) => onChange({ description: e.target.value })}
        />
      </Field>
      <S.Split>
        <Field label={t('folio.editor.panel.code')}>
          <S.Code
            spellCheck={false}
            value={attrs.code}
            onChange={(e) => onChange({ code: e.target.value })}
          />
        </Field>
        <S.Preview>
          <S.PreviewBar>
            <span>{t('folio.editor.panel.preview')}</span>
            <S.Modes role="group" aria-label={t('folio.editor.panel.previewMode')}>
              {(['light', 'dark'] as const).map((m) => (
                <button key={m} type="button" aria-pressed={mode === m} onClick={() => setMode(m)}>
                  {t(`folio.editor.panel.${m}`)}
                </button>
              ))}
            </S.Modes>
          </S.PreviewBar>
          <S.Stage $mode={mode}>
            <VisualFrame
              code={attrs.code}
              title={attrs.title}
              description={attrs.description}
              mode={mode}
            />
          </S.Stage>
        </S.Preview>
      </S.Split>
      <S.Size $over={size > LIMIT}>
        {t('folio.editor.panel.size', { size: (size / 1024).toFixed(1), limit: LIMIT / 1024 })}
      </S.Size>
      {report?.problems.length ? (
        <S.Notes $tone="danger" aria-label={t('folio.editor.panel.problems')}>
          {report.problems.map((p) => (
            <li key={p}>{p}</li>
          ))}
        </S.Notes>
      ) : report ? (
        <S.Ok role="status">{t('folio.editor.panel.sandboxOk')}</S.Ok>
      ) : null}
      {report?.warnings.length ? (
        <S.Notes $tone="warning" aria-label={t('folio.editor.panel.warnings')}>
          {report.warnings.map((w) => (
            <li key={w}>{w}</li>
          ))}
        </S.Notes>
      ) : null}
    </>
  );
}
