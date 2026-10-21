import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  type HomeLayoutBlock,
  fetchHomeDraft,
  folioHomeKey,
  homeEditorKeys,
  publishHome,
  saveHomeDraft,
} from '../../../../services/api/folio';
import { BlockConfig } from './components/BlockConfig';
import { BlockPalette } from './components/BlockPalette';
import { EditorGrid } from './components/EditorGrid';
import { HomeHistory } from './components/HomeHistory';
import { HomePreview } from './components/HomePreview';
import { blockErrors } from './errors';
import { addBlock, applyPlacements, isDirty, removeBlock, setConfig } from './state';
import * as S from './style';

const MODES = ['edit', 'preview', 'history'] as const;
type Mode = (typeof MODES)[number];

/** Folio, Admin, Home (Folio 3.2): build the home on a 12-column grid, preview it as the
 * home would show it, save, publish, and bring back an earlier layout. */
export function HomeEditor() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const { data: draft } = useQuery({ queryKey: homeEditorKeys.draft, queryFn: fetchHomeDraft });
  const [edited, setEdited] = useState<HomeLayoutBlock[] | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [mode, setMode] = useState<Mode>('edit');

  const saved = (draft?.layout.blocks ?? []) as HomeLayoutBlock[];
  const blocks = edited ?? saved;
  const dirty = edited !== null && isDirty(saved, edited);

  const save = useMutation({
    mutationFn: (sent: HomeLayoutBlock[]) => saveHomeDraft({ columns: 12, blocks: sent }),
    onSuccess: (next) => {
      queryClient.setQueryData(homeEditorKeys.draft, next);
      setEdited(null);
      toast(t('folio.homeEditor.saved'));
    },
  });
  const publish = useMutation({
    mutationFn: publishHome,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: homeEditorKeys.draft });
      void queryClient.invalidateQueries({ queryKey: homeEditorKeys.history });
      void queryClient.invalidateQueries({ queryKey: folioHomeKey });
      toast(t('folio.homeEditor.published'));
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });

  if (!draft) return <PageSpinner />;
  // The 422 numbers blocks as they were sent, not as they are now.
  const errors = blockErrors(save.error, save.variables ?? blocks);
  const change = (next: HomeLayoutBlock[]) => setEdited(next);
  const current = blocks.find((b) => b.id === selected);

  return (
    <S.Wrap>
      <S.Toolbar>
        <S.Status role="status">
          {dirty
            ? t('folio.homeEditor.unsaved')
            : draft.saved
              ? t('folio.homeEditor.draftReady')
              : t('folio.homeEditor.showingPublished')}
        </S.Status>
        <S.Modes role="group" aria-label={t('folio.homeEditor.modes')}>
          {MODES.map((m) => (
            <Button
              key={m}
              size="sm"
              variant={mode === m ? 'primary' : 'ghost'}
              aria-pressed={mode === m}
              onClick={() => setMode(m)}
            >
              {t(`folio.homeEditor.${m}`)}
            </Button>
          ))}
        </S.Modes>
        <Button disabled={!dirty || save.isPending} onClick={() => save.mutate(blocks)}>
          {t('folio.homeEditor.save')}
        </Button>
        <Button
          variant="primary"
          disabled={dirty || !draft.saved || publish.isPending}
          onClick={() => publish.mutate()}
        >
          {t('folio.homeEditor.publish')}
        </Button>
      </S.Toolbar>
      {mode === 'preview' && <HomePreview blocks={blocks} />}
      {mode === 'history' && (
        <HomeHistory
          onRestored={() => {
            setEdited(null);
            setMode('edit');
          }}
        />
      )}
      {mode === 'edit' && (
        <>
          <BlockPalette
            onAdd={(type) => {
              const next = addBlock(blocks, type);
              change(next);
              setSelected(next[next.length - 1]?.id ?? null);
            }}
          />
          {save.error !== null && (
            <S.Errors role="alert">
              {errors.size === 0 ? (
                <li>{errorMessage(save.error)}</li>
              ) : (
                [...errors].flatMap(([id, list]) =>
                  list.map((e) => <li key={`${id}-${e.field}`}>{`${id}: ${e.message}`}</li>),
                )
              )}
            </S.Errors>
          )}
          <S.Body>
            <EditorGrid
              blocks={blocks}
              selected={selected}
              invalid={new Set(errors.keys())}
              onSelect={setSelected}
              onPlace={(placements) => change(applyPlacements(blocks, placements))}
              onRemove={(id) => change(removeBlock(blocks, id))}
            />
            {current ? (
              <BlockConfig
                key={current.id}
                block={current}
                errors={errors.get(current.id) ?? []}
                onChange={(config) => change(setConfig(blocks, current.id, config))}
              />
            ) : (
              <S.Hint>{t('folio.homeEditor.config.select')}</S.Hint>
            )}
          </S.Body>
        </>
      )}
    </S.Wrap>
  );
}
