import { Key, Pill, type Tone } from './style';

type Props = { tone?: Tone; mono?: boolean; children: React.ReactNode; title?: string };

export function Badge({ tone = 'neutral', mono = false, children, title }: Props) {
  return (
    <Pill $tone={tone} $mono={mono} title={title}>
      {children}
    </Pill>
  );
}

/** Ticket key in mono and lime, e.g. PA-4. */
export function TicketKey({ children }: { children: React.ReactNode }) {
  return <Key>{children}</Key>;
}
