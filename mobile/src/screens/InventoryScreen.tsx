/** Elevated Inventory Screen (Confirmed vs Projected Estimate) & Refill Prediction Cards. */

import React, { useState } from 'react';
import { ScrollView, Text, TextInput, useWindowDimensions, View } from 'react-native';
import { Card, EmptyState, FadeSlideIn, PrimaryButton } from '../components/AccessibleUI';
import { BellIcon, PackageIcon } from '../components/Icons';
import { t } from '../i18n/translations';
import { api } from '../services/api';
import { Colors } from '../theme';
import type { InventorySummaryItem, RefillPredictionItem, SupportedLang } from '../types/api';
import { generateUuid } from '../utils/uuid';

interface InventoryScreenProps {
  lang: SupportedLang;
  inventory: InventorySummaryItem[];
  refills: RefillPredictionItem[];
  isOnline: boolean;
  onRefresh: () => Promise<void>;
}

export function InventoryScreen({
  lang,
  inventory,
  refills,
  isOnline,
  onRefresh,
}: InventoryScreenProps) {
  const { width } = useWindowDimensions();
  const twoCol = width >= 900;

  const [reconcileMedId, setReconcileMedId] = useState<string | null>(null);
  const [countedVal, setCountedVal] = useState('');
  const [busyId, setBusyId] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  const handleAddOnePack = async (medId: string) => {
    setBusyId(medId);
    setMessage(null);
    try {
      await api.purchaseStock(medId, 1, '0', generateUuid());
      await onRefresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Unable to add pack.');
    } finally {
      setBusyId(null);
    }
  };

  const handleReconcile = async (medId: string) => {
    setBusyId(medId);
    setMessage(null);
    try {
      await api.reconcileStock(medId, countedVal, generateUuid());
      setReconcileMedId(null);
      setCountedVal('');
      await onRefresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Unable to reconcile physical count.');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <ScrollView className="flex-1" contentContainerStyle={{ padding: 20, paddingBottom: 48 }}>
      <Text className="text-[26px] font-extrabold text-ink mb-4 tracking-tight">
        {t(lang, 'tabInventory')}
      </Text>

      {message && (
        <View className="bg-red-50 border border-red-200 rounded-2xl p-3.5 mb-4">
          <Text className="text-[14.5px] font-semibold text-red-700">{message}</Text>
        </View>
      )}

      {inventory.length === 0 ? (
        <EmptyState
          title="No Stock Records Yet"
          subtitle="Once you add medicines and packs, confirmed and projected balances appear here."
        />
      ) : (
        <View className={twoCol ? 'flex-row flex-wrap -mx-2' : ''}>
          {inventory.map((item, idx) => (
            <FadeSlideIn
              key={item.personal_med_id}
              delay={Math.min(idx * 45, 200)}
              className={twoCol ? 'w-1/2 px-2' : 'w-full'}
            >
              <Card accentColor={Colors.primary}>
                <View className="flex-row items-center mb-3">
                  <View className="w-10 h-10 rounded-xl bg-brand-soft items-center justify-center mr-3">
                    <PackageIcon size={20} color={Colors.primary} />
                  </View>
                  <Text className="text-[18.5px] font-extrabold text-ink flex-1">
                    {item.display_name}
                  </Text>
                </View>

                <View className="flex-row gap-2.5 mb-4">
                  <View className="flex-1 bg-brand-soft/60 border border-brand/15 rounded-2xl p-3.5">
                    <Text className="text-[12.5px] font-semibold text-brand-dark">
                      {t(lang, 'confirmedStock')}
                    </Text>
                    <Text className="text-[20px] font-extrabold text-brand-dark mt-1">
                      {item.confirmed_stock} {item.stock_unit}
                    </Text>
                  </View>
                  <View className="flex-1 bg-slate-50 border border-slate-200/80 rounded-2xl p-3.5">
                    <Text className="text-[12.5px] font-semibold text-ink-soft">
                      {t(lang, 'projectedEstimate')} ({item.projection_horizon_days}d)
                    </Text>
                    <Text className="text-[20px] font-bold text-ink-muted mt-1">
                      {item.projected_stock_balance} {item.stock_unit}
                    </Text>
                  </View>
                </View>

                {isOnline && (
                  <View className="flex-row gap-2.5">
                    <View className="flex-1">
                      <PrimaryButton
                        title={t(lang, 'addStrip')}
                        variant="emerald"
                        loading={busyId === item.personal_med_id}
                        onPress={() => handleAddOnePack(item.personal_med_id)}
                      />
                    </View>
                    <View className="flex-1">
                      <PrimaryButton
                        title={t(lang, 'reconcile')}
                        variant="outline"
                        onPress={() => {
                          setReconcileMedId(item.personal_med_id);
                          setCountedVal(item.confirmed_stock);
                        }}
                      />
                    </View>
                  </View>
                )}

                {reconcileMedId === item.personal_med_id && (
                  <View className="mt-3.5 p-3.5 bg-slate-50 rounded-2xl border border-slate-200 gap-2.5">
                    <Text className="text-[13.5px] font-semibold text-ink">
                      Enter actual physical count ({item.stock_unit}):
                    </Text>
                    <TextInput
                      className="min-h-[46px] border border-slate-300 rounded-xl px-3.5 text-[16px] bg-white text-ink"
                      keyboardType="decimal-pad"
                      value={countedVal}
                      onChangeText={setCountedVal}
                    />
                    <PrimaryButton
                      title="Save Physical Reconciliation"
                      loading={busyId === item.personal_med_id}
                      onPress={() => handleReconcile(item.personal_med_id)}
                    />
                  </View>
                )}
              </Card>
            </FadeSlideIn>
          ))}
        </View>
      )}

      <View className="flex-row items-center mt-4 mb-3">
        <BellIcon size={20} color={Colors.primary} />
        <Text className="text-[20px] font-extrabold text-ink ml-2">
          {t(lang, 'refillAlerts')}
        </Text>
      </View>

      <View className={twoCol ? 'flex-row flex-wrap -mx-2' : ''}>
        {refills.map((pred) => (
          <View
            key={pred.personal_med_id}
            className={twoCol ? 'w-1/2 px-2' : 'w-full'}
          >
            <Card
              accentColor={pred.should_alert_now ? '#D97706' : Colors.emerald}
              className={pred.should_alert_now ? 'bg-amber-50/70 border-amber-300' : ''}
            >
              <View className="flex-row items-center justify-between mb-1.5">
                <Text className="text-[17px] font-extrabold text-ink">{pred.display_name}</Text>
                {pred.should_alert_now && (
                  <View className="bg-amber-200/80 px-2.5 py-1 rounded-full">
                    <Text className="text-[12px] font-bold text-amber-900">Refill Soon</Text>
                  </View>
                )}
              </View>
              <Text className="text-[14.5px] text-ink-muted leading-6">{pred.reason}</Text>
              {pred.estimated_remaining_days !== null && (
                <Text className="text-[13px] font-semibold text-ink-soft mt-2">
                  Est. remaining: {pred.estimated_remaining_days} days
                  {pred.projected_depletion_date ? ` • Depletes: ${pred.projected_depletion_date}` : ''}
                </Text>
              )}
            </Card>
          </View>
        ))}
      </View>
    </ScrollView>
  );
}
