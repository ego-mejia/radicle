import i18n from 'i18next';
import { beforeAll, describe, expect, it } from 'vitest';
import '../../../../i18n';
import { notificationTitle } from './title';

const base = { app: 'folio', title: "@luis commented on 'Guía'" };

describe('notification titles', () => {
  beforeAll(async () => {
    await i18n.changeLanguage('es');
  });

  it('writes the title in the reader language', () => {
    const n = {
      ...base,
      type: 'comment',
      params: { actor: '@luis', page: 'Guía', variant: 'comment' },
    };
    expect(notificationTitle(n, i18n.t)).toBe('@luis comentó en «Guía»');
    const reply = { ...n, params: { ...n.params, variant: 'reply' } };
    expect(notificationTitle(reply, i18n.t)).toBe('@luis respondió en un hilo de «Guía»');
    const published = { ...base, type: 'page_published', params: { page: 'Deploy', version: '3' } };
    expect(notificationTitle(published, i18n.t)).toBe('Alguien publicó «Deploy» (v3)');
  });

  it('keeps the server title without params or a wording', () => {
    expect(notificationTitle({ ...base, type: 'comment', params: {} }, i18n.t)).toBe(base.title);
    const unknown = { ...base, type: 'brand_new', params: { page: 'Guía' } };
    expect(notificationTitle(unknown, i18n.t)).toBe(base.title);
  });
});
