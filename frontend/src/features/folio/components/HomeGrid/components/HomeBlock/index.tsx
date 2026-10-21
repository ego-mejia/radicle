import { useTranslation } from 'react-i18next';
import { MarkdownView } from '../../../../../../components/Markdown/MarkdownView';
import type { FolioHomeBlock } from '../../../../../../services/api/folio';
import { DocList } from '../DocList';
import { Featured } from '../Featured';
import { SearchBox } from '../SearchBox';
import { SpaceList } from '../SpaceList';
import { Spotlight } from '../Spotlight';
import * as S from './style';

const LIST_TITLES: Record<string, string> = {
  posts: 'folio.home.latestPosts',
  query: 'folio.home.docsTitle',
  for_you: 'folio.home.forYou',
  most_read: 'folio.home.mostRead',
};

/** One block of the home, drawn by its type with what the API resolved for it. */
export function HomeBlock({ block }: { block: FolioHomeBlock }) {
  const { t } = useTranslation();
  const fallback = LIST_TITLES[block.type];
  const title = block.title || (fallback ? t(fallback) : '');
  const [first] = block.cards;

  switch (block.type) {
    case 'featured':
      return first ? <Featured doc={first} /> : null;
    case 'announcement':
      return first ? (
        <Spotlight tone="accent" label={title || t('folio.home.announcement')} doc={first} />
      ) : null;
    case 'posts':
    case 'query':
    case 'for_you':
    case 'most_read':
      return <DocList title={title} docs={block.cards} numbered={block.type === 'most_read'} />;
    case 'spaces':
      return <SpaceList title={title || t('folio.home.spaces')} spaces={block.spaces} />;
    case 'text':
      return (
        <S.Text aria-label={title || undefined}>
          {title && <S.Heading>{title}</S.Heading>}
          <MarkdownView readOnly>{block.markdown}</MarkdownView>
        </S.Text>
      );
    case 'search':
      return <SearchBox label={title || t('folio.search')} />;
    default:
      return null; // chat waits for phase 4; a type this build doesn't know stays out
  }
}
