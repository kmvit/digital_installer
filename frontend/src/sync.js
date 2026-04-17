import db from './db';
import api from './api';

/**
 * Статусы pending-запросов.
 */
const STATUS = {
  PENDING: 'pending',
  SENDING: 'sending',
  FAILED: 'failed',
};

/**
 * Добавить запрос в офлайн-очередь.
 * Вызывается когда сеть недоступна.
 *
 * @param {string} method - HTTP метод (POST, PATCH, DELETE)
 * @param {string} url - относительный URL (/workday/clock-in/)
 * @param {object|FormData} data - тело запроса
 * @param {boolean} hasFile - содержит ли файлы (FormData)
 */
export async function enqueueRequest(method, url, data, hasFile = false) {
  let serializedData = data;

  // FormData нельзя сохранить в IndexedDB напрямую — конвертируем
  if (hasFile && data instanceof FormData) {
    const entries = {};
    const files = {};

    for (const [key, value] of data.entries()) {
      if (value instanceof File) {
        // Сохраняем файл как ArrayBuffer + метаданные
        const buffer = await value.arrayBuffer();
        files[key] = {
          buffer,
          name: value.name,
          type: value.type,
        };
      } else {
        // Обычные поля могут повторяться (workers_present)
        if (entries[key] !== undefined) {
          if (!Array.isArray(entries[key])) entries[key] = [entries[key]];
          entries[key].push(value);
        } else {
          entries[key] = value;
        }
      }
    }
    serializedData = { _fields: entries, _files: files };
  }

  await db.pendingRequests.add({
    method,
    url,
    data: serializedData,
    hasFile,
    status: STATUS.PENDING,
    createdAt: new Date().toISOString(),
  });
}

/**
 * Десериализовать данные обратно в FormData (для файлов).
 */
function deserializeToFormData(data) {
  const fd = new FormData();

  // Обычные поля
  if (data._fields) {
    for (const [key, value] of Object.entries(data._fields)) {
      if (Array.isArray(value)) {
        value.forEach((v) => fd.append(key, v));
      } else {
        fd.append(key, value);
      }
    }
  }

  // Файлы
  if (data._files) {
    for (const [key, fileMeta] of Object.entries(data._files)) {
      const blob = new Blob([fileMeta.buffer], { type: fileMeta.type });
      fd.append(key, blob, fileMeta.name);
    }
  }

  return fd;
}

/**
 * Получить количество ожидающих запросов.
 */
export async function getPendingCount() {
  return db.pendingRequests
    .where('status')
    .anyOf(STATUS.PENDING, STATUS.FAILED)
    .count();
}

/**
 * Отправить все ожидающие запросы на сервер.
 * Вызывается при восстановлении сети.
 */
export async function syncPendingRequests() {
  const pending = await db.pendingRequests
    .where('status')
    .anyOf(STATUS.PENDING, STATUS.FAILED)
    .sortBy('createdAt');

  let synced = 0;
  let failed = 0;

  for (const req of pending) {
    // Пометить как отправляемый
    await db.pendingRequests.update(req.id, { status: STATUS.SENDING });

    try {
      let requestData = req.data;
      const config = {};

      if (req.hasFile) {
        requestData = deserializeToFormData(req.data);
        config.headers = { 'Content-Type': 'multipart/form-data' };
      }

      await api({
        method: req.method,
        url: req.url,
        data: requestData,
        ...config,
      });

      // Успешно — удалить из очереди
      await db.pendingRequests.delete(req.id);
      synced++;
    } catch (err) {
      // Если сервер вернул 4xx — ошибка данных, не повторять бесконечно
      if (err.response && err.response.status >= 400 && err.response.status < 500) {
        await db.pendingRequests.update(req.id, {
          status: STATUS.FAILED,
          error: JSON.stringify(err.response.data),
        });
      } else {
        // Сетевая ошибка — оставить как pending для повтора
        await db.pendingRequests.update(req.id, { status: STATUS.PENDING });
      }
      failed++;
    }
  }

  return { synced, failed, remaining: await getPendingCount() };
}

/**
 * Кэшировать справочные данные для офлайн-доступа.
 */
export async function cacheReferenceData(objects, priceItems, brigade) {
  if (objects?.length) {
    await db.cachedObjects.clear();
    await db.cachedObjects.bulkAdd(objects);
  }
  if (priceItems?.length) {
    await db.cachedPriceItems.clear();
    await db.cachedPriceItems.bulkAdd(priceItems);
  }
  if (brigade) {
    await db.cachedBrigade.clear();
    await db.cachedBrigade.add(brigade);
  }
}

/**
 * Получить кэшированные справочники.
 */
export async function getCachedObjects() {
  return db.cachedObjects.toArray();
}

export async function getCachedPriceItems() {
  return db.cachedPriceItems.toArray();
}

export async function getCachedBrigade() {
  return db.cachedBrigade.toCollection().first();
}

/**
 * Кэшировать текущий рабочий день.
 */
export async function cacheWorkday(workday) {
  await db.cachedWorkday.clear();
  if (workday) {
    await db.cachedWorkday.add(workday);
  }
}

export async function getCachedWorkday() {
  return db.cachedWorkday.toCollection().first();
}

/**
 * Очистить все кэши.
 */
export async function clearAllCaches() {
  await Promise.all([
    db.cachedObjects.clear(),
    db.cachedPriceItems.clear(),
    db.cachedBrigade.clear(),
    db.cachedWorkday.clear(),
  ]);
}
