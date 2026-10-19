import { Pencil, Tag, ArrowRightLeft, UserRound, X } from 'lucide-react';
import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Button, IconButton } from '../../../../components/ui/Button';
import type { ProjectDetail } from '../../../../services/api/types';
import { BulkDialog, type BulkAction } from './components/BulkDialog';
import * as S from './style';

type Props = { project: ProjectDetail; keys: string[]; onClear: () => void; onDone: () => void };

const ACTIONS: { id: BulkAction; icon: React.ReactNode }[] = [
  { id: 'field', icon: <Pencil /> },
  { id: 'tags', icon: <Tag /> },
  { id: 'status', icon: <ArrowRightLeft /> },
  { id: 'assign', icon: <UserRound /> },
];

/** Shown while tickets are selected in the list: edit a field, tags, status or assignee. */
export function BulkBar({ project, keys, onClear, onDone }: Props) {
  const { t } = useTranslation();
  const [action, setAction] = useState<BulkAction | null>(null);
  if (!keys.length) return null;
  return (
    <S.Bar role="toolbar" aria-label={t('bulk.toolbar')}>
      <strong>{t('bulk.selected', { count: keys.length })}</strong>
      {ACTIONS.map(({ id, icon }) => (
        <Button key={id} size="sm" onClick={() => setAction(id)}>
          {icon}
          {t(`bulk.actions.${id}`)}
        </Button>
      ))}
      <S.Spacer />
      <IconButton label={t('bulk.clear')} onClick={onClear}>
        <X />
      </IconButton>
      {action && (
        <BulkDialog
          project={project}
          keys={keys}
          action={action}
          onClose={() => setAction(null)}
          onDone={() => {
            setAction(null);
            onDone();
          }}
        />
      )}
    </S.Bar>
  );
}
