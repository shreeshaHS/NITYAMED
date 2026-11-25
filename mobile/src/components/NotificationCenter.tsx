/** In-App Pop-up Reminder Modal & Notification Center Drawer for Web and Mobile. */

import React from 'react';
import { Modal, Platform, ScrollView, Text, TouchableOpacity, View } from 'react-native';
import { CardShadow, Colors } from '../theme';
import type { DailyDoseItem, NotificationItem, RefillPredictionItem } from '../types/api';
import { formatDoseNotificationText } from '../services/notifications';
import { PrimaryButton } from './AccessibleUI';
import { BellIcon, ClockIcon } from './Icons';

interface DosePopupModalProps {
  dose: DailyDoseItem | null;
  privacyMasked: boolean;
  busy: boolean;
  onConfirmTaken: (dose: DailyDoseItem) => Promise<void>;
  onSnooze: (dose: DailyDoseItem) => Promise<void>;
  onDismiss: (doseId: string) => void;
}

export function DosePopupModal({
  dose,
  privacyMasked,
  busy,
  onConfirmTaken,
  onSnooze,
  onDismiss,
}: DosePopupModalProps) {
  if (!dose) return null;

  const { title, body } = formatDoseNotificationText(dose, privacyMasked);
  const dueTime = new Date(dose.scheduled_at).toLocaleTimeString([], {
    hour: '2-digit',
    minute: '2-digit',
  });

  return (
    <Modal visible transparent animationType="fade">
      <View className="flex-1 bg-slate-900/45 items-center justify-center p-5">
        <View
          className="w-full max-w-md bg-white rounded-[28px] p-6 border border-slate-200"
          style={CardShadow}
        >
          <View className="flex-row items-center justify-between mb-3">
            <View className="flex-row items-center bg-brand-soft px-3 py-1.5 rounded-full">
              <BellIcon size={16} color={Colors.primary} />
              <Text className="text-[12.5px] font-extrabold text-brand-dark ml-1.5">
                Scheduled Dose Due • {dueTime}
              </Text>
            </View>
            <TouchableOpacity onPress={() => onDismiss(dose.id)} className="px-2 py-1">
              <Text className="text-[14px] font-bold text-ink-soft">Dismiss</Text>
            </TouchableOpacity>
          </View>

          <Text className="text-[22px] font-extrabold text-ink tracking-tight">{title}</Text>
          <Text className="text-[15.5px] text-ink-muted leading-6 mt-1.5 mb-5">{body}</Text>

          <View className="gap-2.5">
            <PrimaryButton
              title="Mark Taken Now"
              variant="emerald"
              loading={busy}
              onPress={() => onConfirmTaken(dose)}
            />
            <PrimaryButton
              title="Snooze 15 Minutes"
              variant="outline"
              loading={busy}
              onPress={() => onSnooze(dose)}
            />
          </View>
        </View>
      </View>
    </Modal>
  );
}

interface NotificationDrawerProps {
  visible: boolean;
  notifications: NotificationItem[];
  refills: RefillPredictionItem[];
  webPermission: 'granted' | 'denied' | 'default' | 'unsupported';
  onEnableWebPopups: () => Promise<void>;
  onCheckRefills: () => Promise<void>;
  onDismissNotif: (id: string) => Promise<void>;
  onClose: () => void;
}

export function NotificationDrawerModal({
  visible,
  notifications,
  refills,
  webPermission,
  onEnableWebPopups,
  onCheckRefills,
  onDismissNotif,
  onClose,
}: NotificationDrawerProps) {
  const lowStockRefills = refills.filter((r) => r.should_alert_now);

  return (
    <Modal visible={visible} animationType="slide" transparent>
      <View className="flex-1 bg-slate-900/45 justify-end md:justify-center md:items-center">
        <View
          className="bg-surface-canvas w-full md:max-w-lg md:rounded-[28px] rounded-t-[28px] max-h-[86%] overflow-hidden border border-slate-200"
          style={CardShadow}
        >
          {/* Header */}
          <View className="bg-white px-5 py-4 border-b border-slate-200 flex-row items-center justify-between">
            <View className="flex-row items-center">
              <BellIcon size={20} color={Colors.primary} />
              <Text className="text-[19px] font-extrabold text-ink ml-2">
                Alerts & Reminders
              </Text>
            </View>
            <TouchableOpacity
              onPress={onClose}
              className="bg-slate-100 px-3.5 py-1.5 rounded-full"
            >
              <Text className="text-[13.5px] font-bold text-ink">Close</Text>
            </TouchableOpacity>
          </View>

          <ScrollView contentContainerStyle={{ padding: 18, paddingBottom: 28 }}>
            {Platform.OS === 'web' && webPermission !== 'unsupported' && (
              <View className="bg-white rounded-2xl p-4 border border-slate-200 mb-4">
                <Text className="text-[15.5px] font-bold text-ink">
                  Browser Desktop Pop-up Alerts
                </Text>
                <Text className="text-[13.5px] text-ink-muted mt-1 leading-5">
                  {webPermission === 'granted'
                    ? 'Browser pop-ups are enabled! Due dose alerts will appear even if this tab is in the background.'
                    : webPermission === 'denied'
                      ? 'Browser notifications are currently blocked in site permissions. In-app pop-up modals will still alert you.'
                      : 'Allow browser pop-up notifications so NityaMed alerts you cleanly on desktop/web.'}
                </Text>
                {webPermission === 'default' && (
                  <PrimaryButton
                    title="Enable Browser Pop-ups"
                    variant="emerald"
                    onPress={onEnableWebPopups}
                    className="mt-3"
                  />
                )}
              </View>
            )}

            {lowStockRefills.length > 0 && (
              <View className="mb-4">
                <Text className="text-[14px] font-extrabold text-amber-800 uppercase tracking-wide mb-2">
                  Refill Attention Needed
                </Text>
                {lowStockRefills.map((r) => (
                  <View
                    key={r.personal_med_id}
                    className="bg-amber-50 border border-amber-200 rounded-2xl p-3.5 mb-2"
                  >
                    <Text className="text-[15.5px] font-bold text-amber-950">
                      {r.display_name} • {r.confirmed_stock} {r.stock_unit} left
                    </Text>
                    <Text className="text-[13.5px] text-amber-900 mt-0.5">{r.reason}</Text>
                  </View>
                ))}
              </View>
            )}

            <View className="flex-row items-center justify-between mb-2.5">
              <Text className="text-[14px] font-extrabold text-ink-muted uppercase tracking-wide">
                Recent Alert History
              </Text>
              <TouchableOpacity onPress={onCheckRefills}>
                <Text className="text-[13.5px] font-bold text-brand">Check Refills</Text>
              </TouchableOpacity>
            </View>

            {notifications.length === 0 ? (
              <View className="bg-white rounded-2xl p-5 border border-slate-200 items-center">
                <ClockIcon size={24} color={Colors.textMuted} />
                <Text className="text-[15px] font-bold text-ink mt-2">No Alerts Yet</Text>
                <Text className="text-[13.5px] text-ink-muted text-center mt-1">
                  Due dose pop-ups and low-stock refill notifications will appear here.
                </Text>
              </View>
            ) : (
              notifications.map((n) => (
                <View
                  key={n.id}
                  className="bg-white rounded-2xl p-3.5 border border-slate-200 mb-2.5"
                >
                  <View className="flex-row items-center justify-between mb-1">
                    <Text className="text-[12px] font-extrabold uppercase text-brand">
                      {n.notif_type.replace('_', ' ')}
                    </Text>
                    <Text className="text-[12px] font-semibold text-ink-soft">
                      {new Date(n.scheduled_for).toLocaleString()}
                    </Text>
                  </View>
                  <Text className="text-[14.5px] text-ink leading-5">{n.payload_preview}</Text>
                  {n.delivery_status !== 'dismissed' && (
                    <TouchableOpacity
                      onPress={() => onDismissNotif(n.id)}
                      className="self-end mt-2 px-3 py-1 bg-slate-100 rounded-full"
                    >
                      <Text className="text-[12px] font-bold text-ink-muted">Dismiss</Text>
                    </TouchableOpacity>
                  )}
                </View>
              ))
            )}
          </ScrollView>
        </View>
      </View>
    </Modal>
  );
}
