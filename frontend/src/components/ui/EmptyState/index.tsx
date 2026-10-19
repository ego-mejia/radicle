import { PlantIllustration, type Plant } from '../../icons/PlantIllustration';
import * as S from './style';

type Props = { title: string; text?: string; action?: React.ReactNode; plant?: Plant };

export function EmptyState({ title, text, action, plant = 'sprout' }: Props) {
  return (
    <S.Wrap>
      <PlantIllustration plant={plant} />
      <S.Title>{title}</S.Title>
      {text && <S.Text>{text}</S.Text>}
      {action}
    </S.Wrap>
  );
}
