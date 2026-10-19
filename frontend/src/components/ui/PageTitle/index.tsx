import { Head } from './style';

type Props = { title: string; subtitle?: string; actions?: React.ReactNode };

export function PageTitle({ title, subtitle, actions }: Props) {
  return (
    <Head>
      <div>
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {actions}
    </Head>
  );
}
