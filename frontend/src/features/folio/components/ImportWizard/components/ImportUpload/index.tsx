import { useMutation, useQuery } from '@tanstack/react-query';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button } from '../../../../../../components/ui/Button';
import { Field } from '../../../../../../components/ui/Field';
import { Select } from '../../../../../../components/ui/Input';
import { useErrorMessage } from '../../../../../../hooks/useErrorMessage';
import { fetchSpaces, folioKeys } from '../../../../../../services/api/folio';
import {
  createImport,
  type FolioImport,
  type FolioImportSource,
} from '../../../../../../services/api/folioImports';
import * as S from './style';

const SOURCES: FolioImportSource[] = ['confluence', 'notion', 'word', 'markdown'];

type Props = { onUploaded: (item: FolioImport) => void };

/** Step 1: where it comes from, the file, and the space it goes into. */
export function ImportUpload({ onUploaded }: Props) {
  const { t } = useTranslation();
  const errorMessage = useErrorMessage();
  const { data: spaces } = useQuery({ queryKey: folioKeys.spaces, queryFn: fetchSpaces });
  const mine = (spaces ?? []).filter((s) => s.kind === 'team' && s.permissions.includes('admin'));
  const [source, setSource] = useState<FolioImportSource>('confluence');
  const [space, setSpace] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const upload = useMutation({
    mutationFn: () => createImport(space || mine[0]?.key || '', source, file as File),
    onSuccess: (item) => onUploaded(item),
  });
  const target = space || mine[0]?.key || '';
  return (
    <S.Form
      onSubmit={(e) => {
        e.preventDefault();
        if (file && target) upload.mutate();
      }}
    >
      <S.Grid>
        <Field label={t('folio.imports.source')} hint={t(`folio.imports.sourceHint.${source}`)}>
          <Select value={source} onChange={(e) => setSource(e.target.value as FolioImportSource)}>
            {SOURCES.map((s) => (
              <option key={s} value={s}>
                {t(`folio.imports.sources.${s}`)}
              </option>
            ))}
          </Select>
        </Field>
        <Field label={t('folio.imports.space')}>
          <Select value={target} onChange={(e) => setSpace(e.target.value)}>
            {mine.map((s) => (
              <option key={s.key} value={s.key}>
                {s.name}
              </option>
            ))}
          </Select>
        </Field>
      </S.Grid>
      <Field label={t('folio.imports.file')} hint={t('folio.imports.fileHint')}>
        <input
          type="file"
          accept=".zip,.docx,.md,.markdown"
          onChange={(e) => setFile(e.target.files?.[0] ?? null)}
        />
      </Field>
      {mine.length === 0 && spaces && <S.Muted>{t('folio.imports.noSpaces')}</S.Muted>}
      {upload.error && <S.Error role="alert">{errorMessage(upload.error)}</S.Error>}
      <div>
        <Button type="submit" disabled={!file || !target || upload.isPending}>
          {upload.isPending ? t('folio.imports.uploading') : t('folio.imports.upload')}
        </Button>
      </div>
    </S.Form>
  );
}
