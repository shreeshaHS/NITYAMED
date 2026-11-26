/** Visual Adherence Analytics Screen with Animated Progress Ring & Outcome Distribution Bars. */

import React from 'react';
import { ScrollView, Text, useWindowDimensions, View } from 'react-native';
import {
  AnimatedProgressBar,
  Card,
  CircularProgressRing,
  EmptyState,
  FadeSlideIn,
} from '../components/AccessibleUI';
import { ChartIcon } from '../components/Icons';
import { t } from '../i18n/translations';
import { Colors, FloatingShadow } from '../theme';
import type { AdherenceReport, SupportedLang } from '../types/api';

interface ReportsScreenProps {
  lang: SupportedLang;
  report: AdherenceReport | null;
}

export function ReportsScreen({ lang, report }: ReportsScreenProps) {
  const { width } = useWindowDimensions();
  const twoCol = width >= 900;

  if (!report) {
    return (
      <View className="flex-1 p-5">
        <Text className="text-[26px] font-extrabold text-ink mb-4 tracking-tight">
          {t(lang, 'adherenceReport')}
        </Text>
        <EmptyState
          title="Report Unavailable Offline"
          subtitle="Connect to the internet to load your transparent 30-day adherence analytics."
        />
      </View>
    );
  }

  const adherencePct = report.confirmed_adherence_rate ?? 0;
  const totalClosed = Math.max(1, report.closed_scheduled_count);
  const breakdownRows = [
    { label: 'On Time', count: report.taken_on_time, color: Colors.emerald },
    { label: 'Taken Late', count: report.taken_late, color: '#D97706' },
    { label: 'Partial', count: report.partially_taken, color: '#0284C7' },
    { label: 'Skipped', count: report.explicitly_skipped, color: '#64748B' },
    { label: 'Expired Unconfirmed', count: report.expired_unconfirmed, color: Colors.danger },
  ];

  return (
    <ScrollView className="flex-1" contentContainerStyle={{ padding: 20, paddingBottom: 48 }}>
      <View className="flex-row items-center mb-4">
        <View className="w-11 h-11 rounded-2xl bg-brand-soft items-center justify-center mr-3">
          <ChartIcon size={22} color={Colors.primary} />
        </View>
        <View>
          <Text className="text-[25px] font-extrabold text-ink tracking-tight">
            {t(lang, 'adherenceReport')}
          </Text>
          <Text className="text-[12.5px] font-medium text-ink-muted">
            {report.window_days}-day continuity breakdown ({report.closed_scheduled_count} closed doses)
          </Text>
        </View>
      </View>

      {/* Hero Ring + KPI Trio */}
      <FadeSlideIn>
        <View className="bg-brand-dark rounded-[28px] p-6 mb-4" style={FloatingShadow}>
          <View className="flex-row items-center justify-between gap-4">
            <View className="flex-1">
              <Text className="text-[12px] font-bold uppercase tracking-wider text-emerald-300">
                Confirmed Adherence
              </Text>
              <Text className="text-[32px] font-extrabold text-white mt-0.5">
                {report.confirmed_adherence_rate !== null
                  ? `${report.confirmed_adherence_rate}%`
                  : '—'}
              </Text>
              <Text className="text-[13.5px] text-teal-100 mt-1">
                On-Time: {report.on_time_rate !== null ? `${report.on_time_rate}%` : '—'} •
                Unconfirmed:{' '}
                {report.unconfirmed_rate !== null ? `${report.unconfirmed_rate}%` : '—'}
              </Text>
            </View>
            <CircularProgressRing
              progress={adherencePct / 100}
              size={92}
              strokeWidth={9}
              centerLabel={report.confirmed_adherence_rate !== null ? `${Math.round(adherencePct)}%` : '—'}
              centerSublabel="confirmed"
            />
          </View>
        </View>
      </FadeSlideIn>

      {/* Outcome Distribution Bar Chart */}
      <FadeSlideIn delay={50}>
        <Card>
          <Text className="text-[17px] font-extrabold text-ink mb-3">
            Dose Outcome Distribution
          </Text>
          <View className="gap-3">
            {breakdownRows.map((row) => {
              const ratio = report.closed_scheduled_count > 0 ? row.count / totalClosed : 0;
              return (
                <View key={row.label}>
                  <View className="flex-row items-center justify-between mb-1">
                    <Text className="text-[13.5px] font-semibold text-ink">{row.label}</Text>
                    <Text className="text-[13.5px] font-extrabold text-ink-muted">
                      {row.count} ({Math.round(ratio * 100)}%)
                    </Text>
                  </View>
                  <AnimatedProgressBar
                    progress={ratio}
                    height={9}
                    trackColor="#F1F5F9"
                    fillColor={row.color}
                  />
                </View>
              );
            })}
          </View>
        </Card>
      </FadeSlideIn>

      {report.irregular_patterns.length > 0 && (
        <Card accentColor="#D97706" className="bg-amber-50/70 border-amber-200">
          <Text className="text-[17px] font-extrabold text-amber-900 mb-1.5">
            Routine Pattern Notes
          </Text>
          {report.irregular_patterns.map((pat, idx) => (
            <Text key={idx} className="text-[14.5px] text-amber-950 leading-6 mt-1">
              • {pat}
            </Text>
          ))}
        </Card>
      )}

      <Text className="text-[20px] font-extrabold text-ink mb-3 mt-1">By Medicine</Text>
      <View className={twoCol ? 'flex-row flex-wrap -mx-2' : ''}>
        {report.per_medicine.map((m, idx) => {
          const medPct = m.confirmed_adherence_rate ?? 0;
          return (
            <FadeSlideIn
              key={m.personal_med_id}
              delay={Math.min(idx * 45, 180)}
              className={twoCol ? 'w-1/2 px-2' : 'w-full'}
            >
              <Card accentColor={medPct >= 80 ? Colors.emerald : Colors.primary}>
                <View className="flex-row items-center justify-between mb-2">
                  <Text className="text-[17.5px] font-extrabold text-ink flex-1 pr-2">
                    {m.display_name}
                  </Text>
                  <View className="bg-brand-soft px-3 py-1 rounded-full">
                    <Text className="text-[13px] font-extrabold text-brand-dark">
                      {m.confirmed_adherence_rate !== null ? `${m.confirmed_adherence_rate}%` : '—'}
                    </Text>
                  </View>
                </View>
                <AnimatedProgressBar
                  progress={medPct / 100}
                  height={8}
                  trackColor="#F1F5F9"
                  fillColor={medPct >= 80 ? Colors.emerald : '#D97706'}
                />
                <Text className="text-[12.5px] text-ink-muted mt-2.5">
                  On Time {m.taken_on_time} • Late {m.taken_late} • Skipped {m.explicitly_skipped} •
                  Unconfirmed {m.expired_unconfirmed}
                </Text>
              </Card>
            </FadeSlideIn>
          );
        })}
      </View>

      <Card className="bg-slate-50">
        <Text className="text-[16px] font-bold text-ink mb-1.5">How Metrics Are Calculated</Text>
        <Text className="text-[13.5px] text-ink-muted leading-5">
          • Confirmed Rate: {report.formula_notes.confirmed_adherence_rate}
        </Text>
        <Text className="text-[13.5px] text-ink-muted leading-5 mt-1">
          • Unconfirmed Policy: {report.formula_notes.policy}
        </Text>
        <Text className="text-[12.5px] text-ink-soft mt-2.5 italic leading-5">
          {report.disclaimer}
        </Text>
      </Card>
    </ScrollView>
  );
}
