import { Link } from '@tanstack/react-router';
import { Table2 } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import type { FolioNode } from '../../../../services/api/folio';
import { DatabaseView } from '../DatabaseView';
import { NodeMenu } from '../NodeMenu';
import * as S from './style';

/** A database's own page: its path, its title and its views. */
export function DatabasePage({ node, spaceName }: { node: FolioNode; spaceName?: string }) {
  const { t } = useTranslation();
  return (
    <S.Page>
      <S.Bar>
        <S.Crumbs aria-label={t('folio.reader.path')}>
          <Link to="/folio/s/$key" params={{ key: node.space }}>
            {spaceName ?? node.space}
          </Link>
          {node.breadcrumbs.map((b) => (
            <span key={b.id}>
              <span aria-hidden>/</span>
              <Link to="/folio/p/$page" params={{ page: `${b.id}-${b.slug}` }}>
                {b.title}
              </Link>
            </span>
          ))}
        </S.Crumbs>
        {node.can_edit && <NodeMenu node={node} />}
      </S.Bar>
      <S.Body>
        <S.Title>
          {node.icon ? <span aria-hidden>{node.icon}</span> : <Table2 aria-hidden />}
          {node.title}
        </S.Title>
        <DatabaseView nodeId={node.id} />
      </S.Body>
    </S.Page>
  );
}
