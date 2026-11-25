/** Mobile SQLite offline store and idempotent sync outbox (Android/iOS). */

import * as SQLite from 'expo-sqlite';
import { api } from './api';
import { generateUuid } from '../utils/uuid';
import type { DailyDoseItem, PersonalMedicine, SyncBootstrapResponse } from '../types/api';

let dbPromise: Promise<SQLite.SQLiteDatabase> | null = null;

async function getDb(): Promise<SQLite.SQLiteDatabase> {
  if (!dbPromise) {
    dbPromise = (async () => {
      const db = await SQLite.openDatabaseAsync('nityamed.db');
      await db.execAsync(`
        CREATE TABLE IF NOT EXISTS local_medicines (
          id TEXT PRIMARY KEY,
          display_name TEXT NOT NULL,
          generic_name TEXT,
          strength TEXT NOT NULL,
          dosage_form TEXT NOT NULL,
          dose_per_intake TEXT NOT NULL,
          dose_unit TEXT NOT NULL,
          stock_unit TEXT NOT NULL,
          units_per_pack TEXT,
          confirmed_stock TEXT NOT NULL,
          instructions TEXT,
          status TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS local_dose_events (
          id TEXT PRIMARY KEY,
          personal_med_id TEXT NOT NULL,
          schedule_version_id TEXT NOT NULL,
          display_name TEXT NOT NULL,
          strength TEXT NOT NULL,
          dosage_form TEXT NOT NULL,
          dose_unit TEXT NOT NULL,
          instructions TEXT,
          confirmed_stock TEXT NOT NULL,
          scheduled_at TEXT NOT NULL,
          expected_qty TEXT NOT NULL,
          confirmed_qty TEXT NOT NULL,
          status TEXT NOT NULL,
          snoozed_until TEXT,
          actioned_at TEXT
        );
        CREATE TABLE IF NOT EXISTS sync_outbox (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          client_event_id TEXT NOT NULL UNIQUE,
          event_type TEXT NOT NULL,
          dose_event_id TEXT,
          personal_med_id TEXT,
          payload_json TEXT NOT NULL,
          created_at TEXT NOT NULL,
          synced_at TEXT
        );
      `);
      return db;
    })();
  }
  return dbPromise;
}

export const offlineDb = {
  async hydrateFromBootstrap(snapshot: SyncBootstrapResponse): Promise<void> {
    const db = await getDb();
    await db.withTransactionAsync(async () => {
      await db.runAsync('DELETE FROM local_medicines');
      for (const m of snapshot.medicines) {
        await db.runAsync(
          `INSERT INTO local_medicines (
            id, display_name, generic_name, strength, dosage_form, dose_per_intake,
            dose_unit, stock_unit, units_per_pack, confirmed_stock, instructions, status
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [
            m.id,
            m.display_name,
            m.generic_name,
            m.strength,
            m.dosage_form,
            m.dose_per_intake,
            m.dose_unit,
            m.stock_unit,
            m.units_per_pack,
            m.confirmed_stock,
            m.instructions,
            m.status,
          ]
        );
      }

      await db.runAsync('DELETE FROM local_dose_events');
      for (const d of snapshot.dose_events) {
        await db.runAsync(
          `INSERT INTO local_dose_events (
            id, personal_med_id, schedule_version_id, display_name, strength, dosage_form,
            dose_unit, instructions, confirmed_stock, scheduled_at, expected_qty,
            confirmed_qty, status, snoozed_until, actioned_at
          ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
          [
            d.id,
            d.personal_med_id,
            d.schedule_version_id,
            d.display_name,
            d.strength,
            d.dosage_form,
            d.dose_unit,
            d.instructions,
            d.confirmed_stock,
            d.scheduled_at,
            d.expected_qty,
            d.confirmed_qty,
            d.status,
            d.snoozed_until,
            d.actioned_at,
          ]
        );
      }
    });
  },

  async getLocalMedicines(): Promise<PersonalMedicine[]> {
    const db = await getDb();
    const rows = await db.getAllAsync<PersonalMedicine>(
      "SELECT * FROM local_medicines WHERE status = 'active' ORDER BY display_name ASC"
    );
    return rows;
  },

  async getLocalDailyDoses(datePrefix: string): Promise<DailyDoseItem[]> {
    const db = await getDb();
    const rows = await db.getAllAsync<DailyDoseItem>(
      'SELECT * FROM local_dose_events WHERE scheduled_at LIKE ? ORDER BY scheduled_at ASC',
      [`${datePrefix}%`]
    );
    return rows;
  },

  async queueOfflineDoseAction(
    dose: DailyDoseItem,
    action: 'DOSE_CONFIRM' | 'DOSE_SKIP',
    actualQty?: string
  ): Promise<string> {
    const db = await getDb();
    const clientEventId = generateUuid();
    const nowIso = new Date().toISOString();
    const qtyNum = Number(actualQty ?? dose.expected_qty);
    const newStatus =
      action === 'DOSE_SKIP'
        ? 'explicitly_skipped'
        : qtyNum < Number(dose.expected_qty)
          ? 'partially_taken'
          : 'taken_on_time';

    await db.withTransactionAsync(async () => {
      await db.runAsync(
        'UPDATE local_dose_events SET status = ?, confirmed_qty = ?, actioned_at = ? WHERE id = ?',
        [newStatus, action === 'DOSE_SKIP' ? '0.00' : String(qtyNum), nowIso, dose.id]
      );

      if (action === 'DOSE_CONFIRM') {
        const med = await db.getFirstAsync<{ confirmed_stock: string }>(
          'SELECT confirmed_stock FROM local_medicines WHERE id = ?',
          [dose.personal_med_id]
        );
        if (med) {
          const nextStock = Math.max(0, Number(med.confirmed_stock) - qtyNum).toFixed(2);
          await db.runAsync('UPDATE local_medicines SET confirmed_stock = ? WHERE id = ?', [
            nextStock,
            dose.personal_med_id,
          ]);
        }
      }

      const payload =
        action === 'DOSE_CONFIRM'
          ? { actual_qty: String(qtyNum), actioned_at: nowIso }
          : {};

      await db.runAsync(
        `INSERT INTO sync_outbox (client_event_id, event_type, dose_event_id, personal_med_id, payload_json, created_at)
         VALUES (?, ?, ?, ?, ?, ?)`,
        [clientEventId, action, dose.id, dose.personal_med_id, JSON.stringify(payload), nowIso]
      );
    });

    return clientEventId;
  },

  async getPendingOutboxCount(): Promise<number> {
    const db = await getDb();
    const row = await db.getFirstAsync<{ cnt: number }>(
      'SELECT COUNT(*) as cnt FROM sync_outbox WHERE synced_at IS NULL'
    );
    return row?.cnt ?? 0;
  },

  async flushOutbox(): Promise<number> {
    const db = await getDb();
    const pending = await db.getAllAsync<{
      id: number;
      client_event_id: string;
      event_type: string;
      dose_event_id: string | null;
      personal_med_id: string | null;
      payload_json: string;
    }>('SELECT * FROM sync_outbox WHERE synced_at IS NULL ORDER BY id ASC LIMIT 50');

    if (pending.length === 0) return 0;

    const events = pending.map((row) => ({
      client_event_id: row.client_event_id,
      event_type: row.event_type,
      dose_event_id: row.dose_event_id,
      personal_med_id: row.personal_med_id,
      payload: JSON.parse(row.payload_json),
    }));

    await api.syncEvents(events);
    const nowIso = new Date().toISOString();
    await db.withTransactionAsync(async () => {
      for (const row of pending) {
        await db.runAsync('UPDATE sync_outbox SET synced_at = ? WHERE id = ?', [nowIso, row.id]);
      }
    });
    return pending.length;
  },

  async clearAll(): Promise<void> {
    const db = await getDb();
    await db.execAsync('DELETE FROM local_medicines; DELETE FROM local_dose_events; DELETE FROM sync_outbox;');
  },
};
