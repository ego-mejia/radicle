import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { ArrowDown, ArrowUp } from 'lucide-react';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Spinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  fetchSpaceOverview,
  setSpaceSections,
  spaceKeys,
  type SpaceSection,
} from '../../../../services/api/folioSpaces';
import * as S from './style';

/** The space admin chooses which sections its portada shows, and in what order (RAD-57). */
export function SpaceSectionsEditor({ space }: { space: string }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const client = useQueryClient();
  const overview = useQuery({
    queryKey: spaceKeys.overview(space),
    queryFn: () => fetchSpaceOverview(space),
  });
  const [rows, setRows] = useState<SpaceSection[]>([]);
  useEffect(() => {
    if (overview.data) setRows(overview.data.sections);
  }, [overview.data]);
  const save = useMutation({
    mutationFn: () =>
      setSpaceSections(
        space,
        rows.map((r) => ({ key: r.key, visible: r.visible })),
      ),
    onSuccess: () => {
      void client.invalidateQueries({ queryKey: spaceKeys.overview(space) });
      toast(t('folio.sectionsEditor.saved'));
    },
  });

  if (!overview.data) return <Spinner />;
  const move = (i: number, by: number) => {
    const next = [...rows];
    const [row] = next.splice(i, 1);
    if (!row) return;
    next.splice(i + by, 0, row);
    setRows(next);
  };
  const toggle = (i: number) =>
    setRows(rows.map((r, j) => (j === i ? { ...r, visible: !r.visible } : r)));

  return (
    <S.Card>
      <S.Intro>
        <b>{t('folio.sectionsEditor.title')}</b>
        <span>{t('folio.sectionsEditor.hint')}</span>
      </S.Intro>
      <S.List>
        {rows.map((row, i) => (
          <li key={row.key}>
            <S.Check>
              <input
                id={`section-${row.key}`}
                type="checkbox"
                checked={row.visible}
                onChange={() => toggle(i)}
              />
              <label htmlFor={`section-${row.key}`}>{t(`folio.sections.${row.key}.label`)}</label>
            </S.Check>
            <small>{t('folio.sectionsEditor.count', { count: row.count })}</small>
            <S.Moves>
              <S.Move
                type="button"
                disabled={i === 0}
                aria-label={t('folio.sectionsEditor.up', {
                  name: t(`folio.sections.${row.key}.label`),
                })}
                onClick={() => move(i, -1)}
              >
                <ArrowUp aria-hidden />
              </S.Move>
              <S.Move
                type="button"
                disabled={i === rows.length - 1}
                aria-label={t('folio.sectionsEditor.down', {
                  name: t(`folio.sections.${row.key}.label`),
                })}
                onClick={() => move(i, 1)}
              >
                <ArrowDown aria-hidden />
              </S.Move>
            </S.Moves>
          </li>
        ))}
      </S.List>
      {save.error && <S.Error role="alert">{errorMessage(save.error)}</S.Error>}
      <div>
        <Button variant="primary" onClick={() => save.mutate()} disabled={save.isPending}>
          {t('folio.sectionsEditor.save')}
        </Button>
      </div>
    </S.Card>
  );
}
