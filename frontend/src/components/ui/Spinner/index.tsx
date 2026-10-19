import { Center, Ring } from './style';

export function Spinner({ size = 18 }: { size?: number }) {
  return <Ring $size={size} role="status" aria-label="Loading" />;
}

export function PageSpinner() {
  return (
    <Center>
      <Spinner size={22} />
    </Center>
  );
}
