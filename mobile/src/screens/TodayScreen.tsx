/** Elevated Today Continuity Dashboard with Hero Progress Banner, 2-Column Web Grid & Dose Actions. */

import React, { useState } from 'react';
import {
  Platform,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import {
  AnimatedProgressBar,
  Card,
  EmptyState,
  FadeSlideIn,
  FormIconBadge,
  PrimaryButton,
  StatusBadge,
} from '../components/AccessibleUI';
import { ClockIcon } from '../components/Icons';
import { t } from '../i18n/translations';
import { api } from '../services/api';
import { offlineDb } from '../services/offlineDb';
import { CardShadow, Colors } from '../theme';
import type { DailyDoseItem, DoseStatus, SupportedLang } from '../types/api';
import { getLocalDateString } from '../utils/date';
import { generateUuid } from '../utils/uuid';

interface TodayScreenProps {
  lang: SupportedLang;
  displayName?: string;
  doses: DailyDoseItem[];
  selectedDate: string;
  onSelectDate: (dateStr: string) => void;
  isOnline: boolean;
  pendingSyncCount: number;
  onRefresh: () => Promise<void>;
  onSyncNow: () => Promise<void>;
}

function shiftLocalDate(offsetDays: number): string {
  const dt = new Date();
  dt.setDate(dt.getDate() + offsetDays);
  return getLocalDateString(dt);
}

type DayBucket = 'morning' | 'afternoon' | 'evening' | 'night';

function getDayBucket(isoDate: string): DayBucket {
  const hr = new Date(isoDate).getHours();
  if (hr >= 5 && hr < 12) return 'morning';
  if (hr >= 12 && hr < 17) return 'afternoon';
  if (hr >= 17 && hr < 22) return 'evening';
  return 'night';
}

function getBucketMeta(bucket: DayBucket): { label: string; bg: string; fg: string } {
  const map: Record<DayBucket, { label: string; bg: string; fg: string }> = {
    morning: { label: 'Morning', bg: Colors.morningBg, fg: Colors.morningText },
    afternoon: { label: 'Afternoon', bg: Colors.afternoonBg, fg: Colors.afternoonText },
    evening: { label: 'Evening', bg: Colors.eveningBg, fg: Colors.eveningText },
    night: { label: 'Night', bg: Colors.nightBg, fg: Colors.nightText },
  };
  return map[bucket];
}

function getStatusAccent(status: DoseStatus): string {
  if (status === 'taken_on_time') return Colors.emerald;
  if (status === 'taken_late' || status === 'partially_taken' || status === 'snoozed') {
    return '#D97706';
  }
  if (status === 'expired_unconfirmed') return Colors.danger;
  if (status === 'explicitly_skipped') return Colors.border;
  return Colors.primary;
}

export function TodayScreen({
  lang,
  displayName,
  doses,
  selectedDate,
  onSelectDate,
  isOnline,
  pendingSyncCount,
  onRefresh,
  onSyncNow,
}: TodayScreenProps) {
  const { width } = useWindowDimensions();
  const twoCol = width >= 900;

  const [partialTargetId, setPartialTargetId] = useState<string | null>(null);
  const [partialQty, setPartialQty] = useState('');
  const [correctTargetId, setCorrectTargetId] = useState<string | null>(null);
  const [correctReason, setCorrectReason] = useState('Accidental tap');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [feedback, setFeedback] = useState<string | null>(null);

  const takenCount = doses.filter(
    (d) =>
      d.status === 'taken_on_time' ||
      d.status === 'taken_late' ||
      d.status === 'partially_taken'
  ).length;
  const pendingCount = doses.filter(
    (d) => d.status === 'pending' || d.status === 'snoozed'
  ).length;
  const totalCount = doses.length;
  const progress = totalCount > 0 ? takenCount / totalCount : 0;

  const handleConfirm = async (dose: DailyDoseItem, qty: string) => {
    setBusyId(dose.id);
    setFeedback(null);
    try {
      if (isOnline) {
        await api.confirmDose(dose.id, qty, generateUuid());
      } else if (Platform.OS !== 'web') {
        await offlineDb.queueOfflineDoseAction(dose, 'DOSE_CONFIRM', qty);
      } else {
        throw new Error('Offline dose confirmation requires the Android app.');
      }
      setPartialTargetId(null);
      setPartialQty('');
      await onRefresh();
    } catch (err) {
      if (Platform.OS !== 'web') {
        await offlineDb.queueOfflineDoseAction(dose, 'DOSE_CONFIRM', qty);
        await onRefresh();
      } else {
        setFeedback(err instanceof Error ? err.message : 'Unable to confirm dose');
      }
    } finally {
      setBusyId(null);
    }
  };

  const handleSkip = async (dose: DailyDoseItem) => {
    setBusyId(dose.id);
    setFeedback(null);
    try {
      if (isOnline) {
        await api.skipDose(dose.id, generateUuid());
      } else if (Platform.OS !== 'web') {
        await offlineDb.queueOfflineDoseAction(dose, 'DOSE_SKIP');
      } else {
        throw new Error('Offline dose skip requires the Android app.');
      }
      await onRefresh();
    } catch (err) {
      if (Platform.OS !== 'web') {
        await offlineDb.queueOfflineDoseAction(dose, 'DOSE_SKIP');
        await onRefresh();
      } else {
        setFeedback(err instanceof Error ? err.message : 'Unable to skip dose.');
      }
    } finally {
      setBusyId(null);
    }
  };

  const handleSnooze = async (dose: DailyDoseItem) => {
    setBusyId(dose.id);
    setFeedback(null);
    try {
      if (isOnline) {
        await api.snoozeDose(dose.id, 15);
        await onRefresh();
      } else {
        setFeedback('Snooze saved locally; alarm will remind you shortly.');
      }
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : 'Unable to snooze dose right now.');
    } finally {
      setBusyId(null);
    }
  };

  const handleCorrectToSkipped = async (dose: DailyDoseItem) => {
    setBusyId(dose.id);
    try {
      await api.correctDose(
        dose.id,
        'explicitly_skipped',
        '0',
        correctReason.trim() || 'Accidental confirmation corrected'
      );
      setCorrectTargetId(null);
      await onRefresh();
    } catch (err) {
      setFeedback(err instanceof Error ? err.message : 'Correction requires internet connection.');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <ScrollView className="flex-1" contentContainerStyle={{ padding: 20, paddingBottom: 48 }}>
      {!isOnline && (
        <View className="bg-amber-50 border border-amber-200 rounded-2xl p-3.5 mb-4">
          <Text className="text-[14.5px] font-bold text-amber-800">{t(lang, 'offlineBanner')}</Text>
        </View>
      )}

      {/* Hero Continuity Banner */}
      <FadeSlideIn>
        <View
          className="bg-brand-dark rounded-[28px] p-6 mb-4"
          style={CardShadow}
        >
          <View className="flex-row items-start justify-between mb-4">
            <View className="flex-1 pr-3">
              <Text className="text-[12.5px] font-bold text-emerald-300 uppercase tracking-wider mb-1">
                {new Date(`${selectedDate}T12:00:00`).toLocaleDateString(undefined, {
                  weekday: 'long',
                  month: 'short',
                  day: 'numeric',
                })}
              </Text>
              <Text className="text-[26px] font-extrabold text-white tracking-tight">
                {displayName ? `Hello, ${displayName}` : t(lang, 'todayDoses')}
              </Text>
            </View>

            <View className="bg-white/15 border border-white/20 px-4 py-2 rounded-2xl items-center">
              <Text className="text-[20px] font-extrabold text-white">
                {takenCount}/{totalCount}
              </Text>
              <Text className="text-[11px] font-semibold text-emerald-200">
                {t(lang, 'confirmedLabel')}
              </Text>
            </View>
          </View>

          <AnimatedProgressBar progress={progress} height={11} />

          <View className="flex-row items-center justify-between mt-3">
            <Text className="text-[14.5px] font-semibold text-teal-50">
              {totalCount === 0
                ? t(lang, 'noDosesToday')
                : `${takenCount} of ${totalCount} scheduled doses confirmed`}
            </Text>
            {pendingCount > 0 && (
              <View className="bg-emerald-400/20 px-3 py-1 rounded-full">
                <Text className="text-[12.5px] font-bold text-emerald-200">
                  {pendingCount} due
                </Text>
              </View>
            )}
          </View>
        </View>
      </FadeSlideIn>

      {/* Yesterday / Today / Tomorrow Switcher */}
      <View className="flex-row gap-2 mb-4">
        {(
          [
            { dateStr: shiftLocalDate(-1), label: t(lang, 'yesterdayLabel') },
            { dateStr: shiftLocalDate(0), label: t(lang, 'todayLabel') },
            { dateStr: shiftLocalDate(1), label: t(lang, 'tomorrowLabel') },
          ] as const
        ).map((dayOpt) => {
          const active = selectedDate === dayOpt.dateStr;
          return (
            <TouchableOpacity
              key={dayOpt.label}
              onPress={() => onSelectDate(dayOpt.dateStr)}
              className={`flex-1 py-2.5 px-3 rounded-2xl border items-center ${
                active ? 'bg-brand border-brand' : 'bg-white border-slate-200'
              }`}
            >
              <Text
                className={`text-[13.5px] font-bold ${
                  active ? 'text-white' : 'text-ink-muted'
                }`}
              >
                {dayOpt.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>

      {pendingSyncCount > 0 && (
        <FadeSlideIn delay={60}>
          <Card accentColor={Colors.accent} className="bg-sky-50/70">
            <View className="flex-row items-center justify-between flex-wrap gap-3">
              <Text className="text-[15.5px] font-bold text-ink">
                {t(lang, 'pendingSync')}: {pendingSyncCount} offline update(s)
              </Text>
              {isOnline && (
                <PrimaryButton title={t(lang, 'syncNow')} onPress={onSyncNow} />
              )}
            </View>
          </Card>
        </FadeSlideIn>
      )}

      {feedback && (
        <View className="bg-red-50 border border-red-200 rounded-2xl p-3.5 mb-4">
          <Text className="text-[14.5px] font-semibold text-red-700">{feedback}</Text>
        </View>
      )}

      {doses.length === 0 ? (
        <FadeSlideIn delay={100}>
          <EmptyState
            title="All Clear for Today"
            subtitle={`${t(lang, 'noDosesToday')} Open Medicines to search the catalogue or add your daily schedule.`}
          />
        </FadeSlideIn>
      ) : (
        <View className={twoCol ? 'flex-row flex-wrap -mx-2' : ''}>
          {doses.map((dose, idx) => {
            const timeStr = new Date(dose.scheduled_at).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            });
            const bucketMeta = getBucketMeta(getDayBucket(dose.scheduled_at));
            const canAct =
              dose.status === 'pending' ||
              dose.status === 'snoozed' ||
              dose.status === 'expired_unconfirmed';
            const isConfirmed =
              dose.status === 'taken_on_time' ||
              dose.status === 'taken_late' ||
              dose.status === 'partially_taken';

            return (
              <FadeSlideIn
                key={dose.id}
                delay={Math.min(idx * 50, 220)}
                className={twoCol ? 'w-1/2 px-2' : 'w-full'}
              >
                <Card accentColor={getStatusAccent(dose.status)}>
                  <View className="flex-row items-start">
                    <FormIconBadge form={dose.dosage_form} />
                    <View className="flex-1">
                      <View className="flex-row flex-wrap items-center gap-2">
                        <View
                          className="flex-row items-center px-2.5 py-1 rounded-full"
                          style={{ backgroundColor: bucketMeta.bg }}
                        >
                          <ClockIcon size={13} color={bucketMeta.fg} />
                          <Text
                            className="text-[12.5px] font-bold ml-1"
                            style={{ color: bucketMeta.fg }}
                          >
                            {bucketMeta.label} • {timeStr}
                          </Text>
                        </View>
                        <StatusBadge status={dose.status} />
                      </View>

                      <Text className="text-[19px] font-extrabold text-ink mt-2 tracking-tight">
                        {dose.display_name}
                      </Text>
                      <Text className="text-[14.5px] font-medium text-ink-muted mt-0.5">
                        Take {dose.expected_qty} {dose.dose_unit} • {dose.strength}
                      </Text>
                    </View>
                  </View>

                  {dose.instructions && (
                    <View className="bg-slate-50 border border-slate-100 rounded-2xl px-3.5 py-2.5 mt-3">
                      <Text className="text-[13.5px] text-ink-muted">
                        Note: {dose.instructions}
                      </Text>
                    </View>
                  )}

                  <Text className="text-[13.5px] font-semibold text-ink-soft mt-3">
                    {t(lang, 'confirmedStock')}: {dose.confirmed_stock} {dose.dose_unit}(s)
                  </Text>

                  {canAct && (
                    <View className="mt-4 gap-2.5">
                      <View className="flex-row gap-2.5">
                        <View className="flex-[1.3]">
                          <PrimaryButton
                            title={t(lang, 'taken')}
                            variant="emerald"
                            loading={busyId === dose.id}
                            onPress={() => handleConfirm(dose, dose.expected_qty)}
                          />
                        </View>
                        <View className="flex-1">
                          <PrimaryButton
                            title={t(lang, 'partial')}
                            variant="secondary"
                            onPress={() => {
                              setPartialTargetId(dose.id);
                              setPartialQty(dose.expected_qty);
                            }}
                          />
                        </View>
                      </View>

                      <View className="flex-row gap-2.5">
                        <View className="flex-1">
                          <PrimaryButton
                            title={t(lang, 'snooze')}
                            variant="outline"
                            onPress={() => handleSnooze(dose)}
                          />
                        </View>
                        <View className="flex-1">
                          <PrimaryButton
                            title={t(lang, 'skip')}
                            variant="outline"
                            onPress={() => handleSkip(dose)}
                          />
                        </View>
                      </View>
                    </View>
                  )}

                  {partialTargetId === dose.id && (
                    <View className="mt-3 p-3.5 bg-slate-50 rounded-2xl border border-slate-200 gap-2.5">
                      <Text className="text-[13.5px] font-semibold text-ink">
                        Enter actual {dose.dose_unit}s taken:
                      </Text>
                      <TextInput
                        className="border border-slate-300 rounded-xl px-3.5 py-2.5 text-[16px] bg-white text-ink"
                        keyboardType="decimal-pad"
                        value={partialQty}
                        onChangeText={setPartialQty}
                      />
                      <PrimaryButton
                        title={`Save ${partialQty || '0'} ${dose.dose_unit}`}
                        onPress={() => handleConfirm(dose, partialQty)}
                      />
                    </View>
                  )}

                  {isConfirmed && (
                    <View className="mt-3.5">
                      <PrimaryButton
                        title={t(lang, 'correct')}
                        variant="outline"
                        onPress={() => setCorrectTargetId(dose.id)}
                      />
                      {correctTargetId === dose.id && (
                        <View className="mt-3 p-3.5 bg-slate-50 rounded-2xl border border-slate-200 gap-2.5">
                          <Text className="text-[13.5px] font-semibold text-ink">
                            Reason for correction (audited):
                          </Text>
                          <TextInput
                            className="border border-slate-300 rounded-xl px-3.5 py-2.5 text-[15.5px] bg-white text-ink"
                            value={correctReason}
                            onChangeText={setCorrectReason}
                          />
                          <PrimaryButton
                            title="Undo Confirmation (Mark Skipped)"
                            variant="danger"
                            loading={busyId === dose.id}
                            onPress={() => handleCorrectToSkipped(dose)}
                          />
                        </View>
                      )}
                    </View>
                  )}
                </Card>
              </FadeSlideIn>
            );
          })}
        </View>
      )}
    </ScrollView>
  );
}
