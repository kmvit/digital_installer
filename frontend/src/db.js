import Dexie from 'dexie';

/**
 * Локальная база данных (IndexedDB) для офлайн-режима.
 *
 * pendingRequests — очередь запросов, не отправленных на сервер.
 * cachedObjects   — кэш объектов бригады.
 * cachedPriceItems — кэш позиций прайса.
 * cachedBrigade   — кэш данных бригады.
 * cachedWorkday   — кэш текущего рабочего дня.
 */
const db = new Dexie('DigitalInstallerDB');

db.version(1).stores({
  // Очередь отложенных запросов
  // id — auto-increment, createdAt — для сортировки
  pendingRequests: '++id, createdAt, url, method, status',

  // Кэш справочников
  cachedObjects: 'id, name',
  cachedPriceItems: 'id, name',
  cachedBrigade: 'id',

  // Кэш текущего рабочего дня
  cachedWorkday: 'id',
});

export default db;
