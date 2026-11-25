/** Cross-platform Notification Helper: Native Android Alarms + Web Browser Pop-up Alerts. */

import * as Notifications from 'expo-notifications';
import { Platform } from 'react-native';
import type { DailyDoseItem } from '../types/api';

const CHANNEL_ID = 'nityamed-reminders';

if (Platform.OS !== 'web') {
  Notifications.setNotificationHandler({
    handleNotification: async () => ({
      shouldShowBanner: true,
      shouldShowList: true,
      shouldPlaySound: true,
      shouldSetBadge: true,
    }),
  });
}

export async function initializeNotifications(): Promise<boolean> {
  if (Platform.OS === 'web') {
    return (await requestWebNotificationPermission()) === 'granted';
  }

  if (Platform.OS === 'android') {
    await Notifications.setNotificationChannelAsync(CHANNEL_ID, {
      name: 'Medication Reminders',
      importance: Notifications.AndroidImportance.MAX,
      vibrationPattern: [0, 300, 200, 300],
      lockscreenVisibility: Notifications.AndroidNotificationVisibility.PRIVATE,
    });
  }

  const existing = await Notifications.getPermissionsAsync();
  let status = existing.status;
  if (status !== 'granted') {
    const req = await Notifications.requestPermissionsAsync();
    status = req.status;
  }
  return status === 'granted';
}

export function getWebNotificationPermission(): 'granted' | 'denied' | 'default' | 'unsupported' {
  if (Platform.OS !== 'web' || typeof window === 'undefined' || !('Notification' in window)) {
    return 'unsupported';
  }
  return window.Notification.permission;
}

export async function requestWebNotificationPermission(): Promise<
  'granted' | 'denied' | 'default' | 'unsupported'
> {
  if (Platform.OS !== 'web' || typeof window === 'undefined' || !('Notification' in window)) {
    return 'unsupported';
  }
  if (window.Notification.permission === 'granted') {
    return 'granted';
  }
  try {
    return await window.Notification.requestPermission();
  } catch {
    return window.Notification.permission;
  }
}

export function showWebBrowserPopup(title: string, body: string): boolean {
  if (Platform.OS !== 'web' || typeof window === 'undefined' || !('Notification' in window)) {
    return false;
  }
  if (window.Notification.permission !== 'granted') {
    return false;
  }
  try {
    new window.Notification(title, {
      body,
      icon: '/favicon.ico',
      tag: `nityamed-${title}`,
    });
    return true;
  } catch {
    return false;
  }
}

export function formatDoseNotificationText(
  dose: DailyDoseItem,
  lockscreenPrivacy: boolean
): { title: string; body: string } {
  if (lockscreenPrivacy) {
    return {
      title: 'NityaMed Reminder',
      body: 'Time for your scheduled medicine. Open NityaMed to view and confirm.',
    };
  }
  return {
    title: `Time for ${dose.display_name}`,
    body: `Take ${dose.expected_qty} ${dose.dose_unit}${dose.instructions ? ` (${dose.instructions})` : ''}`,
  };
}

export async function rescheduleLocalDoseAlarms(
  doses: DailyDoseItem[],
  lockscreenPrivacy: boolean
): Promise<number> {
  if (Platform.OS === 'web') return 0;

  const granted = await initializeNotifications();
  if (!granted) return 0;

  await Notifications.cancelAllScheduledNotificationsAsync();
  const nowMs = Date.now();
  let scheduled = 0;

  for (const dose of doses) {
    if (dose.status !== 'pending' && dose.status !== 'snoozed') continue;
    const triggerMs = new Date(dose.scheduled_at).getTime();
    if (Number.isNaN(triggerMs) || triggerMs <= nowMs + 5000) continue;

    const { title, body } = formatDoseNotificationText(dose, lockscreenPrivacy);

    await Notifications.scheduleNotificationAsync({
      content: {
        title,
        body,
        data: { dose_event_id: dose.id, personal_med_id: dose.personal_med_id },
      },
      trigger: {
        type: Notifications.SchedulableTriggerInputTypes.DATE,
        date: new Date(triggerMs),
        channelId: Platform.OS === 'android' ? CHANNEL_ID : undefined,
      },
    });
    scheduled += 1;
  }

  return scheduled;
}
