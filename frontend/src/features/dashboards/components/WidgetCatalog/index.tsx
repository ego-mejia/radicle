import { useTranslation } from 'react-i18next';
import { Modal } from '../../../../components/ui/Modal';
import { WIDGET_TYPES, type WidgetType } from '../../../../services/api/types';
import * as S from './style';

type Props = { onPick: (type: WidgetType) => void; onClose: () => void };

/** Widget catalog: one card per widget type. */
export function WidgetCatalog({ onPick, onClose }: Props) {
  const { t } = useTranslation();
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('dashboards.addWidget')}
      width={640}
    >
      <S.Grid>
        {WIDGET_TYPES.map((type) => (
          <button key={type} type="button" onClick={() => onPick(type)}>
            <strong>{t(`dashboards.widgets.${type}.name`)}</strong>
            <span>{t(`dashboards.widgets.${type}.help`)}</span>
          </button>
        ))}
      </S.Grid>
    </Modal>
  );
}
