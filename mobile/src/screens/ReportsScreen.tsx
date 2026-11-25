/** Elevated Adherence Analytics & Non-Diagnostic Pattern Summary Screen. */

import React from 'react';
import { ScrollView, Text, useWindowDimensions, View } from 'react-native';
import { Card, EmptyState, FadeSlideIn } from '../components/AccessibleUI';
import { ChartIcon } from '../components/Icons';
import { t } from '../i18n/translations';
import { Colors } from '../theme';
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

  return (
    <ScrollView className="flex-1" contentContainerStyle={{ padding: 20, paddingBottom: 48 }}>
      <View className="flex-row items-center mb-4">
        <View className="w-11 h-11 rounded-2xl bg-brand-soft items-center justify-center mr-3">
          <ChartIcon size={22} color={Colors.primary} />
        </View>
        <Text className="text-[26px] font-extrabold text-ink tracking-tight">
          {t(lang, 'adherenceReport')}
        </Text>
      </View>

      <FadeSlideIn>
        <Card>
          <View className="flex-row gap-3 flex-wrap">
            <View className="flex-1 min-w-[140px] bg-brand-soft/60 border border-brand/15 rounded-2xl p-4">
              <Text className="text-[12.5px] font-semibold text-brand-dark">Confirmed Adherence</Text>
              <Text className="text-[26px] font-extrabold text-brand-dark mt-1">
                {report.confirmed_adherence_rate !== null
                  ? `${report.confirmed_adherence_rate}%`
                  : '—'}
              </Text>
            </View>
            <View className="flex-1 min-w-[140px] bg-emerald-50 border border-emerald-200 rounded-2xl p-4">
              <Text className="text-[12.5px] font-semibold text-emerald-800">On-Time Rate</Text>
              <Text className="text-[26px] font-extrabold text-emerald-700 mt-1">
                {report.on_time_rate !== null ? `${report.on_time_rate}%` : '—'}
              </Text>
            </View>
            <View className="flex-1 min-w-[140px] bg-red-50 border border-red-200 rounded-2xl p-4">
              <Text className="text-[12.5px] font-semibold text-red-800">Unconfirmed Rate</Text>
              <Text className="text-[26px] font-extrabold text-red-700 mt-1">
                {report.unconfirmed_rate !== null ? `${report.unconfirmed_rate}%` : '—'}
              </Text>
            </View>
          </View>

          <View className="bg-slate-50 rounded-2xl p-3.5 mt-4 border border-slate-100">
            <Text className="text-[14.5px] font-medium text-ink">
              On Time: {report.taken_on_time} • Late: {report.taken_late} • Partial:{' '}
              {report.partially_taken}
            </Text>
            <Text className="text-[14.5px] font-medium text-ink-muted mt-1">
              Explicitly Skipped: {report.explicitly_skipped} • Expired Unconfirmed:{' '}
              {report.expired_unconfirmed}
            </Text>
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
        {report.per_medicine.map((m) => (
          <View key={m.personal_med_id} className={twoCol ? 'w-1/2 px-2' : 'w-full'}>
            <Card accentColor={Colors.primary}>
              <Text className="text-[17.5px] font-extrabold text-ink">{m.display_name}</Text>
              <Text className="text-[15px] font-bold text-brand-dark mt-1">
                Confirmed:{' '}
                {m.confirmed_adherence_rate !== null ? `${m.confirmed_adherence_rate}%` : '—'} (
                {m.closed_scheduled_count} closed)
              </Text>
              <Text className="text-[13px] text-ink-muted mt-1.5">
                On Time {m.taken_on_time} | Late {m.taken_late} | Skipped {m.explicitly_skipped} |
                Unconfirmed {m.expired_unconfirmed}
              </Text>
            </Card>
          </View>
        ))}
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
