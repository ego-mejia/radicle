import { useMutation, useQuery } from '@tanstack/react-query';
import { Download } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../components/ui/Button';
import { Menu } from '../../../../components/ui/Menu';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  createExport,
  type ExportFormat,
  exportKeys,
  type ExportTarget,
  fetchExport,
} from '../../../../services/api/folioExports';
import * as S from './style';

const FORMATS: ExportFormat[] = ['pdf', 'docx', 'html', 'markdown'];
export const POLL_MS = 1500;

/** Export a page or a space: pick a format, follow the worker's progress, and the file
 * downloads by itself once it is ready. */
export function ExportMenu({ target }: { target: ExportTarget }) {
  const { t } = useTranslation();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [id, setId] = useState<string | null>(null);
  const handled = useRef<string | null>(null);
  const start = useMutation({
    mutationFn: (format: ExportFormat) => createExport(target, format),
    onSuccess: (row) => setId(row.id),
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const job = useQuery({
    queryKey: exportKeys.one(id ?? ''),
    queryFn: () => fetchExport(id ?? ''),
    enabled: id !== null,
    refetchInterval: (q) =>
      ['done', 'failed'].includes(q.state.data?.status ?? '') ? false : POLL_MS,
  });
  const row = job.data;

  useEffect(() => {
    if (!row || handled.current === row.id) return;
    if (row.status === 'done' && row.download_url) {
      handled.current = row.id;
      const link = document.createElement('a');
      link.href = row.download_url;
      link.download = row.filename ?? '';
      document.body.append(link);
      link.click();
      link.remove();
      toast(t('folio.export.ready', { name: row.filename }));
      setId(null);
    } else if (row.status === 'failed') {
      handled.current = row.id;
      toast(String(row.stats.error ?? t('folio.export.failed')), 'error');
      setId(null);
    }
  }, [row, t, toast]);

  const busy = start.isPending || id !== null;
  return (
    <Menu
      align="end"
      trigger={
        <Button disabled={busy} aria-busy={busy}>
          <Download aria-hidden />
          {busy ? t('folio.export.working') : t('folio.export.button')}
        </Button>
      }
      items={FORMATS.map((format) => ({
        key: format,
        label: t(`folio.export.format.${format}`),
        hint: <S.Hint>{t(`folio.export.hint.${format}`)}</S.Hint>,
        onSelect: () => start.mutate(format),
      }))}
    />
  );
}
