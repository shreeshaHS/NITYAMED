/** Web companion fallback for offlineDb (browsers run online against Render FastAPI). */

import type { DailyDoseItem, PersonalMedicine, SyncBootstrapResponse } from '../types/api';
import { getLocalDateString } from '../utils/date';

let cachedMeds: PersonalMedicine[] = [];
let cachedDoses: DailyDoseItem[] = [];

export const offlineDb = {
  async hydrateFromBootstrap(snapshot: SyncBootstrapResponse): Promise<void> {
    cachedMeds = snapshot.medicines;
    cachedDoses = snapshot.dose_events;
  },
  async getLocalMedicines(): Promise<PersonalMedicine[]> {
    return cachedMeds;
  },
  async getLocalDailyDoses(datePrefix: string): Promise<DailyDoseItem[]> {
    return cachedDoses.filter((d) => {
      const parsed = new Date(d.scheduled_at);
      return !Number.isNaN(parsed.getTime())
        ? getLocalDateString(parsed) === datePrefix
        : d.scheduled_at.startsWith(datePrefix);
    });
  },
  async queueOfflineDoseAction(): Promise<string> {
    return '';
  },
  async getPendingOutboxCount(): Promise<number> {
    return 0;
  },
  async flushOutbox(): Promise<number> {
    return 0;
  },
  async clearAll(): Promise<void> {
    cachedMeds = [];
    cachedDoses = [];
  },
};
