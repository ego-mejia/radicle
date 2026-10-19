import { useQueryClient } from '@tanstack/react-query';
import { GripVertical, Pencil, RefreshCw, Trash2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { IconButton } from '../../../../components/ui/Button';
import { dashboardKeys } from '../../../../services/api/dashboards';
import type { Widget } from '../../../../services/api/types';
import { WidgetBody } from '../WidgetBody';
import * as S from './style';

type Props = {
  widget: Widget;
  editing: boolean;
  refreshSeconds: number;
  onEdit: () => void;
  onDelete: () => void;
};

/** Title bar with refresh (and edit, delete and a drag handle in edit mode) around a widget. */
export function WidgetFrame({ widget, editing, refreshSeconds, onEdit, onDelete }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  return (
    <S.Frame aria-label={widget.title} data-testid={`widget-${widget.title}`}>
      <S.Head>
        {editing && (
          <S.Handle className="widget-drag" aria-hidden>
            <GripVertical />
          </S.Handle>
        )}
        <h3>{widget.title}</h3>
        <IconButton
          label={t('dashboards.refreshWidget', { title: widget.title })}
          onClick={() =>
            void queryClient.invalidateQueries({ queryKey: dashboardKeys.widget(widget.id) })
          }
        >
          <RefreshCw />
        </IconButton>
        {editing && (
          <>
            <IconButton
              label={t('dashboards.editWidget', { title: widget.title })}
              onClick={onEdit}
            >
              <Pencil />
            </IconButton>
            <IconButton
              label={t('dashboards.removeWidget', { title: widget.title })}
              onClick={onDelete}
            >
              <Trash2 />
            </IconButton>
          </>
        )}
      </S.Head>
      <S.Body>
        <WidgetBody widget={widget} refreshSeconds={refreshSeconds} />
      </S.Body>
    </S.Frame>
  );
}
