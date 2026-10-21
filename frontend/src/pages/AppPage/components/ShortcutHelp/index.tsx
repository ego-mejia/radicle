import { useTranslation } from 'react-i18next';
import { Modal } from '../../../../components/ui/Modal';
import * as S from './style';

const GROUPS: { title: string; keys: [string[], string][] }[] = [
  {
    title: 'global',
    keys: [
      [['c'], 'create'],
      [['/'], 'search'],
      [['⌘', 'K'], 'palette'],
      [['?'], 'help'],
      [['g', 'p'], 'projects'],
      [['g', 'm'], 'myTickets'],
      [['g', 'd'], 'docket'],
      [['g', 'f'], 'folio'],
      [['Esc'], 'close'],
    ],
  },
  {
    title: 'lists',
    keys: [
      [['j'], 'next'],
      [['k'], 'previous'],
      [['Enter'], 'open'],
    ],
  },
  {
    title: 'ticket',
    keys: [
      [['e'], 'editTitle'],
      [['a'], 'assignMe'],
      [['m'], 'move'],
      [['l'], 'tags'],
      [['p'], 'priority'],
    ],
  },
];

/** The `?` overlay listing every shortcut. */
export function ShortcutHelp({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  return (
    <Modal
      open
      onOpenChange={(open) => !open && onClose()}
      title={t('shortcuts.title')}
      width={560}
    >
      <S.Grid>
        {GROUPS.map((group) => (
          <section key={group.title}>
            <h3>{t(`shortcuts.groups.${group.title}`)}</h3>
            <dl>
              {group.keys.map(([keys, action]) => (
                <S.Row key={action}>
                  <dt>
                    {keys.map((k, i) => (
                      <kbd key={i}>{k}</kbd>
                    ))}
                  </dt>
                  <dd>{t(`shortcuts.actions.${action}`)}</dd>
                </S.Row>
              ))}
            </dl>
          </section>
        ))}
      </S.Grid>
      <S.Note>{t('shortcuts.note')}</S.Note>
    </Modal>
  );
}
