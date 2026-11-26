/** Elevated Inventory Screen (Confirmed vs Projected Estimate, Purchases, Loss Adjustments, Ledger & Refill Alerts). */

import React, { useState } from 'react';
import { Modal, ScrollView, Text, TextInput, useWindowDimensions, View } from 'react-native';
import { AnimatedProgressBar, Card, EmptyState, FadeSlideIn, LabeledInput, PrimaryButton } from '../components/AccessibleUI';
import { BellIcon, HistoryIcon, PackageIcon } from '../components/Icons';
import { t } from '../i18n/translations';
import { api } from '../services/api';
import { Colors } from '../theme';
import type {
  InventorySummaryItem,
  RefillPredictionItem,
  StockTransactionItem,
  SupportedLang,
} from '../types/api';
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

  const [purchaseMedId, setPurchaseMedId] = useState<string | null>(null);
  const [buyPacks, setBuyPacks] = useState('1');
  const [buyLoose, setBuyLoose] = useState('0');

  const [adjustMedId, setAdjustMedId] = useState<string | null>(null);
  const [adjustQty, setAdjustQty] = useState('');
  const [adjustReason, setAdjustReason] = useState('Expired or damaged tablets');

  const [ledgerMedName, setLedgerMedName] = useState<string | null>(null);
  const [ledgerItems, setLedgerItems] = useState<StockTransactionItem[]>([]);

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

  const handlePurchaseCustom = async (medId: string) => {
    const packs = Number(buyPacks || '0');
    const loose = Number(buyLoose || '0');
    if ((Number.isNaN(packs) || packs <= 0) && (Number.isNaN(loose) || loose <= 0)) {
      setMessage('Please enter packs or loose units greater than 0.');
      return;
    }
    setBusyId(medId);
    setMessage(null);
    try {
      await api.purchaseStock(medId, Math.max(0, Math.floor(packs)), String(Math.max(0, loose)), generateUuid());
      setPurchaseMedId(null);
      setBuyPacks('1');
      setBuyLoose('0');
      await onRefresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Unable to record stock purchase.');
    } finally {
      setBusyId(null);
    }
  };

  const handleDeductLoss = async (medId: string) => {
    const num = Number(adjustQty || '0');
    if (Number.isNaN(num) || num <= 0) {
      setMessage('Please enter a positive quantity to deduct.');
      return;
    }
    setBusyId(medId);
    setMessage(null);
    try {
      await api.adjustStock(
        medId,
        'EXPIRED_DAMAGED_LOST',
        `-${Math.abs(num)}`,
        adjustReason.trim() || 'Expired or damaged stock deducted',
        generateUuid()
      );
      setAdjustMedId(null);
      setAdjustQty('');
      await onRefresh();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Unable to adjust stock.');
    } finally {
      setBusyId(null);
    }
  };

  const handleOpenLedger = async (medId: string, name: string) => {
    setBusyId(medId);
    setMessage(null);
    try {
      const txList = await api.listStockTransactions(medId);
      setLedgerItems(txList);
      setLedgerMedName(name);
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Unable to load stock ledger.');
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
          {inventory.map((item, idx) => {
            const refillInfo = refills.find((r) => r.personal_med_id === item.personal_med_id);
            const remDays = refillInfo?.estimated_remaining_days ?? null;
            const gaugeRatio = remDays !== null ? Math.min(1, Math.max(0.05, remDays / 30)) : 0.5;
            const gaugeColor =
              remDays !== null && remDays <= 5
                ? Colors.danger
                : remDays !== null && remDays <= 10
                  ? '#D97706'
                  : Colors.emerald;

            return (
            <FadeSlideIn
              key={item.personal_med_id}
              delay={Math.min(idx * 45, 200)}
              className={twoCol ? 'w-1/2 px-2' : 'w-full'}
            >
              <Card accentColor={refillInfo?.should_alert_now ? '#D97706' : Colors.primary}>
                <View className="flex-row items-center mb-3">
                  <View className="w-10 h-10 rounded-xl bg-brand-soft items-center justify-center mr-3">
                    <PackageIcon size={20} color={Colors.primary} />
                  </View>
                  <View className="flex-1 pr-2">
                    <Text className="text-[18.5px] font-extrabold text-ink">
                      {item.display_name}
                    </Text>
                    {remDays !== null && (
                      <Text className="text-[12.5px] font-semibold text-ink-muted mt-0.5">
                        ~{remDays} days runway remaining
                      </Text>
                    )}
                  </View>
                  {refillInfo?.should_alert_now && (
                    <View className="bg-amber-100 border border-amber-300 px-2.5 py-1 rounded-full">
                      <Text className="text-[11px] font-extrabold text-amber-900">Refill Soon</Text>
                    </View>
                  )}
                </View>

                {remDays !== null && (
                  <View className="mb-3.5">
                    <AnimatedProgressBar
                      progress={gaugeRatio}
                      height={7}
                      trackColor="#F1F5F9"
                      fillColor={gaugeColor}
                    />
                  </View>
                )}

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
                  <View className="gap-2">
                    <View className="flex-row gap-2">
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
                          title={t(lang, 'buyStockBtn')}
                          variant="primary"
                          onPress={() => {
                            setPurchaseMedId(
                              purchaseMedId === item.personal_med_id ? null : item.personal_med_id
                            );
                            setAdjustMedId(null);
                            setReconcileMedId(null);
                          }}
                        />
                      </View>
                    </View>

                    <View className="flex-row gap-2">
                      <View className="flex-1">
                        <PrimaryButton
                          title={t(lang, 'reconcile')}
                          variant="outline"
                          onPress={() => {
                            setReconcileMedId(
                              reconcileMedId === item.personal_med_id ? null : item.personal_med_id
                            );
                            setCountedVal(item.confirmed_stock);
                            setPurchaseMedId(null);
                            setAdjustMedId(null);
                          }}
                        />
                      </View>
                      <View className="flex-1">
                        <PrimaryButton
                          title={t(lang, 'adjustLossBtn')}
                          variant="outline"
                          onPress={() => {
                            setAdjustMedId(
                              adjustMedId === item.personal_med_id ? null : item.personal_med_id
                            );
                            setAdjustQty('');
                            setPurchaseMedId(null);
                            setReconcileMedId(null);
                          }}
                        />
                      </View>
                    </View>

                    <PrimaryButton
                      title={t(lang, 'ledgerHistoryBtn')}
                      variant="secondary"
                      icon={<HistoryIcon size={15} color={Colors.primaryDark} />}
                      loading={busyId === item.personal_med_id}
                      onPress={() => handleOpenLedger(item.personal_med_id, item.display_name)}
                    />
                  </View>
                )}

                {purchaseMedId === item.personal_med_id && (
                  <View className="mt-3.5 p-3.5 bg-emerald-50/70 rounded-2xl border border-emerald-200 gap-2.5">
                    <LabeledInput
                      label="Full Packs / Strips Purchased"
                      value={buyPacks}
                      onChangeText={setBuyPacks}
                      keyboardType="number-pad"
                    />
                    <LabeledInput
                      label={`Extra Loose Units (${item.stock_unit})`}
                      value={buyLoose}
                      onChangeText={setBuyLoose}
                      keyboardType="decimal-pad"
                    />
                    <PrimaryButton
                      title="Save Stock Purchase"
                      variant="emerald"
                      loading={busyId === item.personal_med_id}
                      onPress={() => handlePurchaseCustom(item.personal_med_id)}
                    />
                  </View>
                )}

                {adjustMedId === item.personal_med_id && (
                  <View className="mt-3.5 p-3.5 bg-red-50/70 rounded-2xl border border-red-200 gap-2.5">
                    <LabeledInput
                      label={`Quantity Lost / Expired (${item.stock_unit})`}
                      value={adjustQty}
                      onChangeText={setAdjustQty}
                      keyboardType="decimal-pad"
                      placeholder="e.g. 2"
                    />
                    <LabeledInput
                      label="Reason / Notes"
                      value={adjustReason}
                      onChangeText={setAdjustReason}
                      placeholder="Expired or damaged tablets"
                    />
                    <PrimaryButton
                      title="Confirm Deduction"
                      variant="danger"
                      loading={busyId === item.personal_med_id}
                      onPress={() => handleDeductLoss(item.personal_med_id)}
                    />
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
            );
          })}
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

      <Modal visible={ledgerMedName !== null} animationType="slide">
        <ScrollView
          className="flex-1 bg-surface-canvas"
          contentContainerStyle={{
            padding: 24,
            paddingBottom: 56,
            maxWidth: 660,
            width: '100%',
            alignSelf: 'center',
          }}
        >
          <Card className="p-6">
            <Text className="text-[22px] font-extrabold text-ink mb-4">
              {ledgerMedName} — Stock Ledger
            </Text>
            {ledgerItems.length === 0 ? (
              <Text className="text-[14.5px] text-ink-muted mb-4">No stock transactions recorded yet.</Text>
            ) : (
              <View className="gap-2.5 mb-4">
                {ledgerItems.map((tx) => (
                  <View
                    key={tx.id}
                    className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200"
                  >
                    <View className="flex-row items-center justify-between">
                      <Text className="text-[13.5px] font-bold text-ink">
                        {tx.tx_type}
                      </Text>
                      <Text className="text-[14px] font-extrabold text-brand-dark">
                        Delta: {tx.qty_delta} • Bal: {tx.balance_after}
                      </Text>
                    </View>
                    {tx.notes && (
                      <Text className="text-[13px] text-ink-muted mt-1">{tx.notes}</Text>
                    )}
                    <Text className="text-[11.5px] text-ink-soft mt-1">
                      {new Date(tx.created_at).toLocaleString()}
                    </Text>
                  </View>
                ))}
              </View>
            )}
            <PrimaryButton title="Close" onPress={() => setLedgerMedName(null)} />
          </Card>
        </ScrollView>
      </Modal>
    </ScrollView>
  );
}
