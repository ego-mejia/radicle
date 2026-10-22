// A plugin block as GET /folio/plugin-blocks returns it, for tests.

import type { PluginBlock } from '../../../../services/api/plugins';

export const COUNTDOWN: PluginBlock = {
  id: 'radicle.countdown/countdown',
  plugin: 'radicle.countdown',
  type: 'countdown',
  name: 'Cuenta regresiva',
  description: 'Cuántos días faltan',
  icon: '⏳',
  fields: [
    {
      key: 'title',
      label: 'Título',
      kind: 'text',
      required: false,
      default: 'Lanzamiento',
      options: [],
    },
    { key: 'date', label: 'Fecha', kind: 'date', required: true, default: '', options: [] },
    {
      key: 'size',
      label: 'Tamaño',
      kind: 'select',
      required: false,
      default: '',
      options: ['S', 'M'],
    },
  ],
  html: '<div id="out"></div>',
};
