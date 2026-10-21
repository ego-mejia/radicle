import { useTranslation } from 'react-i18next';
import type { FolioDiff } from '../../../../services/api/folio';
import { DocContent } from '../DocContent';
import type { DocNode } from '../DocContent/anchors';
import { valueText } from './text';
import * as S from './style';

const SIGN = { equal: '', added: '+', removed: '−' } as const;

type Props = { diff: FolioDiff };

/** What changed between two versions: the title, the metadata fields and block by block. */
export function DiffView({ diff }: Props) {
  const { t } = useTranslation();
  const fields = diff.title ? [diff.title, ...diff.metadata] : diff.metadata;
  const changed = diff.blocks.some((b) => b.op !== 'equal');
  return (
    <S.Wrap>
      <S.Section>
        <h3>{t('folio.history.metadata')}</h3>
        {fields.length ? (
          <S.Table>
            <thead>
              <tr>
                <th>{t('folio.history.field')}</th>
                <th>{t('folio.history.before')}</th>
                <th>{t('folio.history.after')}</th>
              </tr>
            </thead>
            <tbody>
              {fields.map((f) => (
                <tr key={f.field}>
                  <td>{t(`folio.history.fields.${f.field}`, { defaultValue: f.field })}</td>
                  <S.Before>{valueText(f.before)}</S.Before>
                  <td>{valueText(f.after)}</td>
                </tr>
              ))}
            </tbody>
          </S.Table>
        ) : (
          <S.Muted>{t('folio.history.sameMetadata')}</S.Muted>
        )}
      </S.Section>
      <S.Section>
        <h3>{t('folio.history.content')}</h3>
        {!changed && <S.Muted>{t('folio.history.sameContent')}</S.Muted>}
        {diff.blocks.map((b, i) => (
          <S.Block
            key={i}
            $op={b.op}
            aria-label={b.op === 'equal' ? undefined : t(`folio.history.ops.${b.op}`)}
          >
            <S.Sign aria-hidden>{SIGN[b.op]}</S.Sign>
            <S.Rendered>
              <DocContent doc={{ type: 'doc', content: [b.block as DocNode] }} />
            </S.Rendered>
          </S.Block>
        ))}
      </S.Section>
    </S.Wrap>
  );
}
