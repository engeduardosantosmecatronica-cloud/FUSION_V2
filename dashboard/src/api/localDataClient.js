const STORAGE_PREFIX = "fusion_dashboard_";

function read(name) {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_PREFIX + name) || "[]");
  } catch {
    return [];
  }
}

function write(name, rows) {
  localStorage.setItem(STORAGE_PREFIX + name, JSON.stringify(rows));
}

function entity(name, defaults = []) {
  if (!localStorage.getItem(STORAGE_PREFIX + name) && defaults.length) write(name, defaults);

  return {
    async list(order = "-created_date", limit) {
      const rows = [...read(name)];
      const descending = String(order).startsWith("-");
      const field = String(order).replace(/^-/, "") || "created_date";
      rows.sort((a, b) => String(a[field] || "").localeCompare(String(b[field] || "")) * (descending ? -1 : 1));
      return Number.isFinite(limit) ? rows.slice(0, limit) : rows;
    },
    async filter(criteria = {}, order = "-created_date", limit) {
      const rows = await this.list(order);
      const filtered = rows.filter(row => Object.entries(criteria).every(([key, value]) => row[key] === value));
      return Number.isFinite(limit) ? filtered.slice(0, limit) : filtered;
    },
    async create(data) {
      const rows = read(name);
      const now = new Date().toISOString();
      const created = { ...data, id: crypto.randomUUID(), created_date: now, updated_date: now };
      rows.push(created);
      write(name, rows);
      return created;
    },
    async update(id, changes) {
      const rows = read(name);
      const index = rows.findIndex(row => row.id === id);
      if (index < 0) throw new Error(name + ": registro " + id + " não encontrado");
      rows[index] = { ...rows[index], ...changes, updated_date: new Date().toISOString() };
      write(name, rows);
      return rows[index];
    },
  };
}

const defaultRobot = {
  id: "local-robot-config",
  symbol: "AUDUSD",
  timeframe: "M15",
  robot_status: "stopped",
  created_date: new Date().toISOString(),
  updated_date: new Date().toISOString(),
};

export const fusionLocal = {
  entities: {
    RobotConfig: entity("RobotConfig", [defaultRobot]),
    TradeLog: entity("TradeLog"),
    EventLog: entity("EventLog"),
    Strategy: entity("Strategy"),
  },
};