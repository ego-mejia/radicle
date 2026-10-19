import { createContext } from 'react';

export type CreateTicketDefaults = {
  project?: string;
  parent?: string;
  area?: string | null;
  milestone?: string | null;
};

export const CreateTicketContext = createContext<(defaults?: CreateTicketDefaults) => void>(
  () => undefined,
);
