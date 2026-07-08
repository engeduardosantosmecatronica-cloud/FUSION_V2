const STORAGE_PREFIX = 'fusion_frontend_';

function readList(name) {
  try {
    const raw = window.localStorage.getItem(`${STORAGE_PREFIX}${name}`);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function writeList(name, items) {
  window.localStorage.setItem(`${STORAGE_PREFIX}${name}`, JSON.stringify(items));
  notify(name, { type: 'change', data: null });
}

function normalizeSort(sort) {
  const value = String(sort || '').trim();
  return { desc: value.startsWith('-'), field: value.replace(/^-/, '') || 'created_date' };
}

function sortItems(items, sort) {
  const { field, desc } = normalizeSort(sort);
  return [...items].sort((a, b) => {
    const av = a?.[field] ?? '';
    const bv = b?.[field] ?? '';
    if (av === bv) return 0;
    return (av > bv ? 1 : -1) * (desc ? -1 : 1);
  });
}

function makeId(prefix) {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
}

const subscribers = new Map();

function notify(name, event) {
  const callbacks = subscribers.get(name) || [];
  callbacks.forEach(cb => {
    try { cb(event); } catch (error) { console.warn('[fusionLocalClient] subscriber error', error); }
  });
}

function entity(name) {
  return {
    async list(sort = '-created_date', limit = 100) {
      return sortItems(readList(name), sort).slice(0, limit || 100);
    },
    async create(payload) {
      const item = {
        id: payload?.id || makeId(name),
        created_date: payload?.created_date || new Date().toISOString(),
        ...payload,
      };
      const items = [item, ...readList(name)];
      writeList(name, items);
      notify(name, { type: 'create', data: item });
      return item;
    },
    async bulkCreate(payloads = []) {
      const now = new Date().toISOString();
      const created = payloads.map(payload => ({
        id: payload?.id || makeId(name),
        created_date: payload?.created_date || now,
        ...payload,
      }));
      writeList(name, [...created, ...readList(name)]);
      created.forEach(item => notify(name, { type: 'create', data: item }));
      return created;
    },
    async update(id, patch) {
      const items = readList(name);
      const idx = items.findIndex(item => item.id === id || item.ticket === id);
      if (idx < 0) return null;
      const updated = { ...items[idx], ...patch, updated_date: new Date().toISOString() };
      items[idx] = updated;
      writeList(name, items);
      notify(name, { type: 'update', data: updated });
      return updated;
    },
    async delete(id) {
      const before = readList(name);
      const after = before.filter(item => item.id !== id && item.ticket !== id);
      writeList(name, after);
      notify(name, { type: 'delete', data: { id } });
      return { id, deleted: before.length !== after.length };
    },
    subscribe(callback) {
      const callbacks = subscribers.get(name) || [];
      callbacks.push(callback);
      subscribers.set(name, callbacks);
      return () => {
        const current = subscribers.get(name) || [];
        subscribers.set(name, current.filter(cb => cb !== callback));
      };
    },
  };
}

function localUser() {
  try {
    const raw = window.localStorage.getItem('fusion_local_auth_session');
    const session = raw ? JSON.parse(raw) : null;
    return session?.user || null;
  } catch {
    return null;
  }
}

export const fusionLocalClient = {
  auth: {
    async me() {
      const user = localUser();
      if (!user) throw new Error('Sessao local nao encontrada.');
      return user;
    },
    logout() {
      window.localStorage.removeItem('fusion_local_auth_session');
    },
  },
  entities: {
    Candle: entity('candles'),
    Trade: entity('trades'),
    MT5Connection: entity('mt5_connections'),
  },
  integrations: {
    Core: {
      async UploadFile({ file }) {
        return { file_url: file?.name || 'local-file' };
      },
      async ExtractDataFromUploadedFile() {
        return { data: [] };
      },
    },
  },
};
