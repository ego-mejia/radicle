import { Puzzle } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { PageSpinner } from '../../../../components/ui/Spinner';
import { pluginCode } from '../../editor/pluginBlocks';
import { usePluginBlocks } from '../../hooks/usePluginBlocks';
import { VisualFrame } from '../VisualFrame';
import * as S from './style';

type Props = { plugin: string; block: string; data?: Record<string, string> | null };

/** A plugin's block (Folio 5.7) in the Visual's sandbox with its values; a notice when
 * the plugin is off or gone. */
export function PluginFrame({ plugin, block, data }: Props) {
  const { t } = useTranslation();
  const blocks = usePluginBlocks();
  if (blocks.isPending) return <PageSpinner />;
  const def = blocks.byId.get(`${plugin}/${block}`);
  if (!def)
    return (
      <S.Off role="note">
        <Puzzle aria-hidden />
        {t('folio.plugin.off', { plugin })}
      </S.Off>
    );
  return <VisualFrame code={pluginCode(def.html, data ?? {})} description={def.name} />;
}
