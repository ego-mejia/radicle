import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button } from '../../../../components/ui/Button';
import { SettingsCard } from '../../../../components/ui/SettingsCard';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import {
  dryRunImport,
  fetchImport,
  fetchImports,
  type FolioImport,
  importKeys,
} from '../../../../services/api/folioImports';
import { ImportOutcome } from './components/ImportOutcome';
import { ImportPlanView } from './components/ImportPlanView';
import { ImportUpload } from './components/ImportUpload';
import * as S from './style';

const POLL_MS = 2000;

/** Folio, Admin, Import (Folio 5.3): upload an export from Confluence, Notion, Word or
 * Markdown, review its dry run (tree, authors, files, problems), then run it. */
export function ImportWizard() {
  const { t } = useTranslation();
  const client = useQueryClient();
  const [openId, setOpenId] = useState<string | null>(null);
  const history = useQuery({ queryKey: importKeys.all, queryFn: fetchImports });
  const current = useQuery({
    queryKey: importKeys.one(openId ?? ''),
    queryFn: () => fetchImport(openId as string),
    enabled: openId !== null,
    refetchInterval: (q) => (q.state.data?.status === 'running' ? POLL_MS : false),
  });
  const show = (item: FolioImport) => {
    client.setQueryData(importKeys.one(item.id), item);
    void client.invalidateQueries({ queryKey: importKeys.all });
    setOpenId(item.id);
  };
  const item = current.data;

  return (
    <S.Wizard>
      {openId === null || !item ? (
        <SettingsCard title={t('folio.imports.title')} help={t('folio.imports.help')}>
          <ImportUpload onUploaded={show} />
        </SettingsCard>
      ) : (
        <>
          <S.Head>
            <div>
              <strong>{item.filename}</strong>
              <small>
                {t(`folio.imports.sources.${item.source}`)} → {item.space}
              </small>
            </div>
            <Button size="sm" onClick={() => setOpenId(null)}>
              {t('folio.imports.another')}
            </Button>
          </S.Head>
          {item.status === 'uploaded' ? (
            <AutoCheck item={item} onChecked={show} />
          ) : item.status === 'checked' ? (
            <ImportPlanView item={item} onChange={show} />
          ) : (
            <ImportOutcome item={item} />
          )}
        </>
      )}
      {(history.data ?? []).length > 0 && (
        <SettingsCard title={t('folio.imports.history')}>
          <S.History>
            {history.data?.map((h) => (
              <li key={h.id}>
                <button type="button" onClick={() => setOpenId(h.id)}>
                  {h.filename}
                </button>
                <small>
                  {t(`folio.imports.sources.${h.source}`)} → {h.space}
                </small>
                <Badge
                  tone={
                    h.status === 'failed' ? 'danger' : h.status === 'done' ? 'accent' : 'neutral'
                  }
                >
                  {t(`folio.imports.statuses.${h.status}`)}
                </Badge>
              </li>
            ))}
          </S.History>
        </SettingsCard>
      )}
    </S.Wizard>
  );
}

/** A fresh upload gets its first dry run right away, with no options. */
function AutoCheck({
  item,
  onChecked,
}: {
  item: FolioImport;
  onChecked: (i: FolioImport) => void;
}) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const { mutate, error } = useMutation({
    mutationFn: () => dryRunImport(item.id, {}),
    onSuccess: onChecked,
  });
  useEffect(() => mutate(), [item.id, mutate]);
  if (error) return <S.Problem role="alert">{errorMessage(error)}</S.Problem>;
  return <S.Muted>{t('folio.imports.checking')}</S.Muted>;
}
