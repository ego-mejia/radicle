import { useEffect, useId, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useTheme } from 'styled-components';
import { toMermaid } from '../../../../../../lib/workflow';
import type { WorkflowConf } from '../../../../../../services/api/types';
import * as S from './style';

/** State diagram generated from the workflow. Mermaid loads only when this is shown. */
export function WorkflowDiagram({ workflow }: { workflow: WorkflowConf }) {
  const { t } = useTranslation();
  const theme = useTheme();
  const id = useId().replace(/[^a-zA-Z0-9]/g, '');
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const source = toMermaid(workflow, t('settings.anyStatus'));

  useEffect(() => {
    let cancelled = false;
    const timer = setTimeout(() => {
      void import('mermaid')
        .then(async ({ default: mermaid }) => {
          mermaid.initialize({
            startOnLoad: false,
            theme: theme.mode === 'dark' ? 'dark' : 'neutral',
            securityLevel: 'strict',
            fontFamily: theme.fonts.ui,
          });
          const { svg: rendered } = await mermaid.render(`wf${id}`, source);
          if (!cancelled) {
            setSvg(rendered);
            setFailed(false);
          }
        })
        .catch(() => !cancelled && setFailed(true));
    }, 250);
    return () => {
      cancelled = true;
      clearTimeout(timer);
    };
  }, [source, id, theme.mode, theme.fonts.ui]);

  if (failed) return <S.Box>{t('workflow.diagramFailed')}</S.Box>;
  return (
    <S.Box
      aria-label={t('workflow.diagram')}
      role="img"
      // Mermaid output with securityLevel strict: labels are escaped, no scripts or links.
      dangerouslySetInnerHTML={svg ? { __html: svg } : undefined}
    />
  );
}
