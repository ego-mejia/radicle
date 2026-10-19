import 'react-grid-layout/css/styles.css';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import GridLayout, { type Layout, WidthProvider } from 'react-grid-layout';
import { useTranslation } from 'react-i18next';
import { ConfirmDialog } from '../../../../components/ui/ConfirmDialog';
import { EmptyState } from '../../../../components/ui/EmptyState';
import { useErrorMessage } from '../../../../hooks/useErrorMessage';
import { useToast } from '../../../../hooks/useToast';
import {
  addWidget,
  dashboardKeys,
  deleteWidget,
  patchDashboard,
  patchWidget,
} from '../../../../services/api/dashboards';
import type { Dashboard, Widget, WidgetType } from '../../../../services/api/types';
import { WidgetCatalog } from '../WidgetCatalog';
import { WidgetConfigModal } from '../WidgetConfigModal';
import { WidgetFrame } from '../WidgetFrame';
import * as S from './style';

const Grid = WidthProvider(GridLayout);
const ROW = 40;

type Props = {
  dashboard: Dashboard;
  editing: boolean;
  catalog: boolean;
  onCloseCatalog: () => void;
};

type Editing = { type: WidgetType; widget?: Widget };

/** The 12-column grid. In edit mode widgets drag by their handle and resize from the corner. */
export function DashboardGrid({ dashboard, editing, catalog, onCloseCatalog }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const toast = useToast();
  const errorMessage = useErrorMessage();
  const [config, setConfig] = useState<Editing | null>(null);
  const [removing, setRemoving] = useState<Widget | null>(null);
  const refresh = () => queryClient.invalidateQueries({ queryKey: ['dashboards'] });
  const onError = (error: unknown) => toast(errorMessage(error), 'error');

  const saveLayout = useMutation({
    mutationFn: (layout: Layout[]) =>
      patchDashboard(dashboard.id, {
        layout: layout.map(({ i, x, y, w, h }) => ({ id: i, x, y, w, h })),
      }),
    onSuccess: refresh,
    onError,
  });
  const save = useMutation({
    mutationFn: async (v: { title: string; config: Record<string, unknown> }) => {
      if (config?.widget) {
        return patchWidget(dashboard.id, config.widget.id, v);
      }
      return addWidget(dashboard.id, { widget_type: config!.type, ...v });
    },
    onSuccess: (widget) => {
      setConfig(null);
      void refresh();
      void queryClient.invalidateQueries({ queryKey: dashboardKeys.widget(widget.id) });
    },
  });
  const remove = useMutation({
    mutationFn: (widget: Widget) => deleteWidget(dashboard.id, widget.id),
    onSuccess: refresh,
    onError,
  });

  const layout: Layout[] = dashboard.widgets.map((w) => ({
    i: w.id,
    x: w.layout.x ?? 0,
    y: w.layout.y ?? 0,
    w: w.layout.w ?? 6,
    h: w.layout.h ?? 4,
    minW: 2,
    minH: 2,
  }));
  const changed = (next: Layout[]) =>
    next.some((n) => {
      const old = layout.find((l) => l.i === n.i);
      return !old || old.x !== n.x || old.y !== n.y || old.w !== n.w || old.h !== n.h;
    });

  return (
    <S.Wrap $editing={editing}>
      {dashboard.widgets.length === 0 ? (
        <EmptyState
          plant="pot"
          title={t('dashboards.emptyTitle')}
          text={t('dashboards.emptyText')}
        />
      ) : (
        <Grid
          layout={layout}
          cols={12}
          rowHeight={ROW}
          margin={[12, 12]}
          containerPadding={[0, 0]}
          isDraggable={editing}
          isResizable={editing}
          draggableHandle=".widget-drag"
          onDragStop={(next) => changed(next) && saveLayout.mutate(next)}
          onResizeStop={(next) => changed(next) && saveLayout.mutate(next)}
        >
          {dashboard.widgets.map((widget) => (
            <div key={widget.id}>
              <WidgetFrame
                widget={widget}
                editing={editing}
                refreshSeconds={dashboard.refresh_seconds}
                onEdit={() => setConfig({ type: widget.widget_type as WidgetType, widget })}
                onDelete={() => setRemoving(widget)}
              />
            </div>
          ))}
        </Grid>
      )}
      {catalog && (
        <WidgetCatalog
          onClose={onCloseCatalog}
          onPick={(type) => {
            onCloseCatalog();
            setConfig({ type });
          }}
        />
      )}
      {config && (
        <WidgetConfigModal
          type={config.type}
          title={config.widget?.title}
          config={config.widget?.config}
          pending={save.isPending}
          error={save.error ? errorMessage(save.error) : null}
          onCancel={() => {
            save.reset();
            setConfig(null);
          }}
          onSave={(title, values) => save.mutate({ title, config: values })}
        />
      )}
      <ConfirmDialog
        open={Boolean(removing)}
        title={t('dashboards.removeWidget', { title: removing?.title ?? '' })}
        message={t('dashboards.removeConfirm')}
        confirmLabel={t('common.delete')}
        onConfirm={() => {
          if (removing) remove.mutate(removing);
          setRemoving(null);
        }}
        onCancel={() => setRemoving(null)}
      />
    </S.Wrap>
  );
}
