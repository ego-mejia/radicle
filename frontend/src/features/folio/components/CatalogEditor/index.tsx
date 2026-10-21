import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Archive, ArchiveRestore, ArrowDown, ArrowUp, Pencil } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Badge } from '../../../../components/ui/Badge';
import { Button, IconButton } from '../../../../components/ui/Button';
import { Field } from '../../../../components/ui/Field';
import { Input } from '../../../../components/ui/Input';
import { SettingsCard, SettingsParts as P } from '../../../../components/ui/SettingsCard';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  type FolioCatalog,
  type FolioEntry,
  type FolioEntryPatch,
  createEntry,
  fetchCatalog,
  folioKeys,
  updateEntry,
} from '../../../../services/api/folio';
import * as S from './style';

type Props = { catalog: FolioCatalog };

function useCatalog(catalog: FolioCatalog) {
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: folioKeys.catalog(catalog) });
    void queryClient.invalidateQueries({ queryKey: folioKeys.schema });
  };
  const patch = useMutation({
    mutationFn: (changes: { key: string; body: FolioEntryPatch }[]) =>
      Promise.all(changes.map((c) => updateEntry(catalog, c.key, c.body))),
    onSuccess: refresh,
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  return { patch, refresh, toast, errorMessage };
}

function EntryRow({
  catalog,
  entry,
  above,
  below,
}: Props & {
  entry: FolioEntry;
  above?: FolioEntry;
  below?: FolioEntry;
}) {
  const { t } = useTranslation();
  const { patch } = useCatalog(catalog);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState(entry.name);
  const [description, setDescription] = useState(entry.description);
  // Moving swaps positions with the neighbor, so the order holds whatever the numbers are.
  const swap = (other: FolioEntry) =>
    patch.mutate([
      { key: entry.key, body: { position: other.position } },
      { key: other.key, body: { position: entry.position } },
    ]);
  const row = (
    <P.Row>
      {editing ? (
        <S.Edit
          onSubmit={(e) => {
            e.preventDefault();
            patch.mutate([{ key: entry.key, body: { name: name.trim(), description } }], {
              onSuccess: () => setEditing(false),
            });
          }}
        >
          <Field label={t('folio.catalogs.name')}>
            <Input value={name} onChange={(e) => setName(e.target.value)} />
          </Field>
          <Field label={t('folio.catalogs.description')}>
            <Input value={description} onChange={(e) => setDescription(e.target.value)} />
          </Field>
          <Button type="submit" size="sm" variant="primary" disabled={!name.trim()}>
            {t('common.save')}
          </Button>
          <Button size="sm" onClick={() => setEditing(false)}>
            {t('common.cancel')}
          </Button>
        </S.Edit>
      ) : (
        <P.Grow>
          <S.Name>
            <strong>{entry.name}</strong>
            {entry.description && <small>{entry.description}</small>}
          </S.Name>
          <S.Key>{entry.key}</S.Key>
          {entry.archived && <Badge>{t('folio.catalogs.archived')}</Badge>}
        </P.Grow>
      )}
      {!editing && (
        <>
          <IconButton
            label={t('folio.catalogs.up', { name: entry.name })}
            disabled={!above}
            onClick={() => above && swap(above)}
          >
            <ArrowUp />
          </IconButton>
          <IconButton
            label={t('folio.catalogs.down', { name: entry.name })}
            disabled={!below}
            onClick={() => below && swap(below)}
          >
            <ArrowDown />
          </IconButton>
          <IconButton
            label={t('folio.catalogs.edit', { name: entry.name })}
            onClick={() => setEditing(true)}
          >
            <Pencil />
          </IconButton>
          <IconButton
            label={t(entry.archived ? 'folio.catalogs.restore' : 'folio.catalogs.archive', {
              name: entry.name,
            })}
            onClick={() => patch.mutate([{ key: entry.key, body: { archived: !entry.archived } }])}
          >
            {entry.archived ? <ArchiveRestore /> : <Archive />}
          </IconButton>
        </>
      )}
    </P.Row>
  );
  return entry.archived && !editing ? <S.Archived>{row}</S.Archived> : row;
}

function AddEntry({ catalog }: Props) {
  const { t } = useTranslation();
  const { refresh, toast, errorMessage } = useCatalog(catalog);
  const [key, setKey] = useState('');
  const [name, setName] = useState('');
  const add = useMutation({
    mutationFn: () => createEntry(catalog, { key: key.trim(), name: name.trim() }),
    onSuccess: () => {
      setKey('');
      setName('');
      refresh();
      toast(t('folio.catalogs.added'));
    },
    onError: (e) => toast(errorMessage(e), 'error'),
  });
  const ready = key.trim() !== '' && name.trim() !== '';
  return (
    <P.Inline
      onSubmit={(e) => {
        e.preventDefault();
        if (ready) add.mutate();
      }}
    >
      <Field label={t('folio.catalogs.key')}>
        <Input value={key} onChange={(e) => setKey(e.target.value)} placeholder="how-to" />
      </Field>
      <Field label={t('folio.catalogs.name')}>
        <Input value={name} onChange={(e) => setName(e.target.value)} />
      </Field>
      <Button type="submit" size="sm" disabled={!ready || add.isPending}>
        {t('common.add')}
      </Button>
    </P.Inline>
  );
}

/** One metadata catalog (Folio 1.3): doc types, audiences or languages people pick from. */
export function CatalogEditor({ catalog }: Props) {
  const { t } = useTranslation();
  const { data: entries } = useQuery({
    queryKey: folioKeys.catalog(catalog),
    queryFn: () => fetchCatalog(catalog),
  });
  return (
    <SettingsCard
      title={t(`folio.catalogs.names.${catalog}`)}
      help={t(`folio.catalogs.help.${catalog}`)}
    >
      {entries ? (
        <P.Rows>
          {entries.map((entry, i) => (
            <EntryRow
              key={entry.key}
              catalog={catalog}
              entry={entry}
              above={entries[i - 1]}
              below={entries[i + 1]}
            />
          ))}
          {entries.length === 0 && <P.Muted>{t('folio.catalogs.none')}</P.Muted>}
          <AddEntry catalog={catalog} />
        </P.Rows>
      ) : (
        <PageSpinner />
      )}
    </SettingsCard>
  );
}
