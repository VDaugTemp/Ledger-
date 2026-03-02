import type { Profile } from "@/lib/types";

export type UserRecord = {
  userId: string;
  email?: string;
  createdAt: string;
};

// Module-level in-memory store (resets on server restart — fine for prototype)
export const users = new Map<string, UserRecord>();
export const profiles = new Map<string, Profile>();

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
      missingFields: [],
      completenessScore: 0,
    },
  };
}
