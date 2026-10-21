import { useTranslation } from 'react-i18next';
import * as S from './style';

export type TimelineItem = {
  date?: string;
  title: string;
  text?: string;
  status?: 'done' | 'in_progress' | 'planned';
};

/** A timeline block (Folio 3.4): milestones on a horizontal line, each with its date,
 * its status and what it is. */
export function Timeline({ items }: { items: TimelineItem[] }) {
  const { t } = useTranslation();
  return (
    <S.Line aria-label={t('folio.reader.timeline')}>
      {items.map((item, i) => (
        <S.Item key={i} $status={item.status}>
          <S.Dot aria-hidden />
          {item.date ? <S.Date>{item.date}</S.Date> : null}
          <S.Title>{item.title}</S.Title>
          {item.status ? (
            <S.Status $status={item.status}>{t(`folio.reader.milestone.${item.status}`)}</S.Status>
          ) : null}
          {item.text ? <S.Text>{item.text}</S.Text> : null}
        </S.Item>
      ))}
    </S.Line>
  );
}
