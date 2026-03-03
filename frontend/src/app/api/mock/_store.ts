import { readFileSync, writeFileSync } from "fs";
import { join } from "path";
import type { Profile } from "@/lib/types";

export type UserRecord = {
  userId: string;
  email?: string;
  createdAt: string;
};

// ── File-based persistence ────────────────────────────────────────────────────

const DB_PATH = join(process.cwd(), ".mock-db.json");

type DbData = {
  users: Record<string, UserRecord>;
  profiles: Record<string, Profile>;
};

function loadDb(): DbData {
  try {
    const raw = readFileSync(DB_PATH, "utf8");
    return JSON.parse(raw) as DbData;
  } catch {
    return { users: {}, profiles: {} };
  }
}

export function persistStore() {
  try {
    const data: DbData = {
      users: Object.fromEntries(users),
      profiles: Object.fromEntries(profiles),
    };
    writeFileSync(DB_PATH, JSON.stringify(data, null, 2), "utf8");
  } catch {
    // ignore write errors in dev
  }
}

// ── In-memory store (hydrated from file on startup) ──────────────────────────

const db = loadDb();
export const users = new Map<string, UserRecord>(Object.entries(db.users));
export const profiles = new Map<string, Profile>(Object.entries(db.profiles));

// ── Default profile ───────────────────────────────────────────────────────────

export function makeDefaultProfile(): Profile {
  return {
    profileVersion: 1,
    updatedAt: new Date().toISOString(),
    jurisdiction: "MY",
    assessmentYear: 2025,
    presence: { trips: [] },
    incomeTypes: {
      employment: false,
      contractor: false,
      passive: false,
      crypto: false,
    },
    advisorContext: {
      filesTaxElsewhere: false,
      citizenships: [],
      visaDeclaredIncome: { provided: false },
    },
    dataQuality: {
      mrdComplete: false,
      intakeCompleted: false,
      missingFields: [],
      completenessScore: 0,
    },
  };
}
