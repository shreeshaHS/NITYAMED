/** Elevated Medicines Screen: Catalogue Search, Custom Entry, Schedule Setup & Verified Education. */

import React, { useState } from 'react';
import {
  Modal,
  ScrollView,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import {
  Card,
  EmptyState,
  FadeSlideIn,
  FormIconBadge,
  LabeledInput,
  PrimaryButton,
} from '../components/AccessibleUI';
import { SearchIcon } from '../components/Icons';
import { t } from '../i18n/translations';
import { api, ApiError } from '../services/api';
import { Colors } from '../theme';
import type {
  CatalogueItem,
  DosageForm,
  FrequencyType,
  PersonalMedicine,
  PersonalMedicineDetail,
  SupportedLang,
} from '../types/api';
import { getLocalDateString } from '../utils/date';
import { generateUuid } from '../utils/uuid';

interface MedicinesScreenProps {
  lang: SupportedLang;
  medicines: PersonalMedicine[];
  isOnline: boolean;
  onRefresh: () => Promise<void>;
}

const FREQ_OPTIONS: Array<{ value: FrequencyType; label: string }> = [
  { value: 'once_daily', label: 'Once Daily' },
  { value: 'multiple_daily', label: 'Twice Daily' },
  { value: 'alternate_day', label: 'Alternate Day' },
  { value: 'weekly', label: 'Weekly' },
  { value: 'fixed_course', label: 'Fixed Course' },
  { value: 'as_needed', label: 'As Needed (PRN)' },
];

const FORMS: DosageForm[] = ['tablet', 'capsule', 'syrup', 'inhaler', 'drops', 'injection', 'other'];

export function MedicinesScreen({ lang, medicines, isOnline, onRefresh }: MedicinesScreenProps) {
  const { width } = useWindowDimensions();
  const twoCol = width >= 900;

  const [searchQ, setSearchQ] = useState('');
  const [results, setResults] = useState<CatalogueItem[]>([]);
  const [searching, setSearching] = useState(false);

  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedCatalogue, setSelectedCatalogue] = useState<CatalogueItem | null>(null);
  const [isCustom, setIsCustom] = useState(false);

  const [customName, setCustomName] = useState('');
  const [customStrength, setCustomStrength] = useState('');
  const [customForm, setCustomForm] = useState<DosageForm>('tablet');
  const [dosePerIntake, setDosePerIntake] = useState('1');
  const [initialPacks, setInitialPacks] = useState('1');
  const [initialLoose, setInitialLoose] = useState('0');
  const [packSize, setPackSize] = useState('10');
  const [instructions, setInstructions] = useState('');

  const [freq, setFreq] = useState<FrequencyType>('once_daily');
  const [time1, setTime1] = useState('08:00');
  const [time2, setTime2] = useState('20:00');
  const [endDate, setEndDate] = useState('');
  const [createdMedId, setCreatedMedId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [detailModal, setDetailModal] = useState<PersonalMedicineDetail | null>(null);

  const resetAddForm = () => {
    setShowAddForm(false);
    setSelectedCatalogue(null);
    setIsCustom(false);
    setCustomName('');
    setCustomStrength('');
    setCustomForm('tablet');
    setDosePerIntake('1');
    setInitialPacks('1');
    setInitialLoose('0');
    setPackSize('10');
    setInstructions('');
    setFreq('once_daily');
    setTime1('08:00');
    setTime2('20:00');
    setEndDate('');
    setCreatedMedId(null);
    setErrorMsg(null);
  };

  const handleSearch = async () => {
    if (!searchQ.trim()) return;
    setSearching(true);
    setErrorMsg(null);
    try {
      const hits = await api.searchCatalogue(searchQ.trim());
      setResults(hits);
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Search requires internet connection.');
    } finally {
      setSearching(false);
    }
  };

  const openCatalogueAdd = (item: CatalogueItem) => {
    resetAddForm();
    setSelectedCatalogue(item);
    setIsCustom(false);
    setPackSize(item.standard_pack_size || '10');
    setShowAddForm(true);
  };

  const openCustomAdd = () => {
    resetAddForm();
    setSelectedCatalogue(null);
    setIsCustom(true);
    setShowAddForm(true);
  };

  const handleSaveMedicineAndSchedule = async () => {
    setErrorMsg(null);
    if (isCustom && !customName.trim()) {
      setErrorMsg('Please enter the medicine name.');
      return;
    }
    const timeRegex = /^([01]\d|2[0-3]):[0-5]\d$/;
    if (freq !== 'as_needed' && !timeRegex.test(time1.trim())) {
      setErrorMsg('Please enter a valid 24-hour Dose Time (HH:MM, e.g. 08:00).');
      return;
    }
    if (freq === 'multiple_daily' && !timeRegex.test(time2.trim())) {
      setErrorMsg('Please enter a valid 24-hour Evening Dose Time (HH:MM, e.g. 20:00).');
      return;
    }
    if (freq === 'fixed_course' && endDate.trim() && !/^\d{4}-\d{2}-\d{2}$/.test(endDate.trim())) {
      setErrorMsg('Please enter End Date as YYYY-MM-DD (e.g. 2026-12-01).');
      return;
    }

    setSaving(true);
    try {
      let targetMedId = createdMedId;
      if (!targetMedId) {
        const form = isCustom ? customForm : selectedCatalogue!.dosage_form;
        const unit = form === 'syrup' || form === 'drops' ? 'ml' : form === 'inhaler' ? 'puff' : form;
        const med = await api.createMedicine({
          catalogue_id: selectedCatalogue ? selectedCatalogue.id : null,
          is_custom: isCustom,
          display_name: isCustom ? customName.trim() : selectedCatalogue!.brand_name,
          strength: isCustom ? customStrength.trim() : selectedCatalogue!.strength,
          dosage_form: form,
          dose_per_intake: dosePerIntake || '1',
          dose_unit: unit,
          stock_unit: unit,
          units_per_pack: packSize ? packSize : null,
          initial_packs: Number(initialPacks || '0'),
          initial_loose_units: initialLoose || '0',
          instructions: instructions.trim() || null,
          client_event_id: generateUuid(),
        });
        targetMedId = med.id;
        setCreatedMedId(med.id);
      }

      const todayStr = getLocalDateString();
      const times =
        freq === 'as_needed'
          ? []
          : freq === 'multiple_daily'
            ? [
                { time: time1.trim(), dose: dosePerIntake || '1' },
                { time: time2.trim(), dose: dosePerIntake || '1' },
              ]
            : [{ time: time1.trim(), dose: dosePerIntake || '1' }];

      await api.createSchedule(targetMedId, {
        frequency_type: freq,
        times,
        start_date: todayStr,
        end_date: freq === 'fixed_course' && endDate.trim() ? endDate.trim() : null,
        horizon_days: 14,
      });

      resetAddForm();
      setResults([]);
      setSearchQ('');
      await onRefresh();
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Unable to save medicine.');
    } finally {
      setSaving(false);
    }
  };

  const handleOpenDetail = async (medId: string) => {
    try {
      const detail = await api.getMedicineDetail(medId);
      setDetailModal(detail);
    } catch {
      const fallback = medicines.find((m) => m.id === medId);
      if (fallback) {
        setDetailModal({
          medicine: fallback,
          education: null,
          education_notice: 'Connect to internet to view full verified medicine information.',
        });
      }
    }
  };

  return (
    <ScrollView className="flex-1" contentContainerStyle={{ padding: 20, paddingBottom: 48 }}>
      <Text className="text-[26px] font-extrabold text-ink mb-4 tracking-tight">
        {t(lang, 'myMedicines')}
      </Text>

      {isOnline && (
        <FadeSlideIn>
          <Card>
            <View className="flex-row items-center mb-2">
              <SearchIcon size={18} color={Colors.primary} />
              <Text className="text-[16px] font-bold text-ink ml-2">
                Verified Medicine Search
              </Text>
            </View>
            <LabeledInput
              label={t(lang, 'addMedicine')}
              value={searchQ}
              onChangeText={setSearchQ}
              placeholder={t(lang, 'searchPlaceholder')}
            />
            <View className="flex-row gap-2.5 mt-1">
              <View className="flex-1">
                <PrimaryButton title="Search" onPress={handleSearch} loading={searching} />
              </View>
              <View className="flex-1">
                <PrimaryButton
                  title={t(lang, 'addCustom')}
                  variant="outline"
                  onPress={openCustomAdd}
                />
              </View>
            </View>

            {results.length > 0 && (
              <View className="mt-4 border-t border-slate-100 pt-2">
                {results.map((item) => (
                  <TouchableOpacity
                    key={item.id}
                    onPress={() => openCatalogueAdd(item)}
                    className="py-3.5 px-3 rounded-2xl border-b border-slate-100 bg-slate-50/70 mb-2 flex-row items-center justify-between"
                  >
                    <View className="flex-1 pr-3">
                      <Text className="text-[16px] font-bold text-ink">{item.brand_name}</Text>
                      <Text className="text-[13.5px] text-ink-muted mt-0.5">
                        {item.generic_name} • {item.strength} • {item.dosage_form}
                        {item.standard_pack_size ? ` (${item.standard_pack_size}/pack)` : ''}
                      </Text>
                    </View>
                    <View className="bg-brand-soft px-3 py-1.5 rounded-full">
                      <Text className="text-[12.5px] font-bold text-brand-dark">+ Add</Text>
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            )}
          </Card>
        </FadeSlideIn>
      )}

      {errorMsg && (
        <View className="bg-red-50 border border-red-200 rounded-2xl p-3.5 mb-4">
          <Text className="text-[14.5px] font-semibold text-red-700">{errorMsg}</Text>
        </View>
      )}

      {medicines.length === 0 ? (
        <EmptyState
          title="No Medicines Added Yet"
          subtitle="Search our verified Indian medicine catalogue above or add a custom prescription to build your daily routine."
        />
      ) : (
        <View className={twoCol ? 'flex-row flex-wrap -mx-2' : ''}>
          {medicines.map((med, idx) => (
            <FadeSlideIn
              key={med.id}
              delay={Math.min(idx * 45, 200)}
              className={twoCol ? 'w-1/2 px-2' : 'w-full'}
            >
              <TouchableOpacity onPress={() => handleOpenDetail(med.id)}>
                <Card accentColor={Colors.primary}>
                  <View className="flex-row items-start">
                    <FormIconBadge form={med.dosage_form} />
                    <View className="flex-1">
                      <Text className="text-[18.5px] font-extrabold text-ink tracking-tight">
                        {med.display_name}
                      </Text>
                      <Text className="text-[13.5px] text-ink-muted mt-0.5">
                        {med.generic_name ? `${med.generic_name} • ` : ''}
                        {med.strength} • {med.dosage_form}
                      </Text>
                    </View>
                  </View>

                  <View className="flex-row gap-2.5 mt-3.5">
                    <View className="flex-1 bg-slate-50 rounded-2xl p-3 border border-slate-100">
                      <Text className="text-[12px] font-semibold text-ink-soft">Dose</Text>
                      <Text className="text-[15.5px] font-bold text-ink mt-0.5">
                        {med.dose_per_intake} {med.dose_unit}
                      </Text>
                    </View>
                    <View className="flex-1 bg-brand-soft/60 rounded-2xl p-3 border border-brand/10">
                      <Text className="text-[12px] font-semibold text-brand-dark">Confirmed Stock</Text>
                      <Text className="text-[15.5px] font-bold text-brand-dark mt-0.5">
                        {med.confirmed_stock} {med.stock_unit}
                      </Text>
                    </View>
                  </View>

                  <Text className="text-[13px] font-bold text-brand mt-3">
                    Tap for verified uses, side effects & precautions →
                  </Text>
                </Card>
              </TouchableOpacity>
            </FadeSlideIn>
          ))}
        </View>
      )}

      <Modal visible={showAddForm} animationType="slide">
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
              {isCustom ? 'Add Custom Medicine' : `Add ${selectedCatalogue?.brand_name}`}
            </Text>

            {isCustom && (
              <>
                <LabeledInput
                  label="Medicine Name"
                  value={customName}
                  onChangeText={setCustomName}
                  placeholder="e.g., Triphala Churna"
                />
                <LabeledInput
                  label="Strength"
                  value={customStrength}
                  onChangeText={setCustomStrength}
                  placeholder="e.g., 500 mg"
                />
                <Text className="text-[14px] font-bold text-ink mt-2 mb-2">Dosage Form</Text>
                <View className="flex-row flex-wrap gap-2 mb-4">
                  {FORMS.map((f) => (
                    <TouchableOpacity
                      key={f}
                      onPress={() => setCustomForm(f)}
                      className={`px-3.5 py-2 rounded-full border ${
                        customForm === f
                          ? 'bg-brand-soft border-brand'
                          : 'bg-slate-50 border-slate-200'
                      }`}
                    >
                      <Text
                        className={`text-[14px] font-semibold ${
                          customForm === f ? 'text-brand-dark' : 'text-ink-muted'
                        }`}
                      >
                        {f}
                      </Text>
                    </TouchableOpacity>
                  ))}
                </View>
              </>
            )}

            <LabeledInput
              label="Prescribed Dose Per Intake"
              value={dosePerIntake}
              onChangeText={setDosePerIntake}
              keyboardType="decimal-pad"
            />
            <LabeledInput
              label="Units Per Strip / Pack"
              value={packSize}
              onChangeText={setPackSize}
              keyboardType="decimal-pad"
            />
            <LabeledInput
              label="Initial Full Strips / Packs"
              value={initialPacks}
              onChangeText={setInitialPacks}
              keyboardType="number-pad"
            />
            <LabeledInput
              label="Initial Loose Units"
              value={initialLoose}
              onChangeText={setInitialLoose}
              keyboardType="decimal-pad"
            />
            <LabeledInput
              label="Instructions (Optional)"
              value={instructions}
              onChangeText={setInstructions}
              placeholder="e.g., After food"
            />

            <Text className="text-[14px] font-bold text-ink mt-2 mb-2">Schedule Pattern</Text>
            <View className="flex-row flex-wrap gap-2 mb-4">
              {FREQ_OPTIONS.map((opt) => (
                <TouchableOpacity
                  key={opt.value}
                  onPress={() => setFreq(opt.value)}
                  className={`px-3.5 py-2 rounded-full border ${
                    freq === opt.value
                      ? 'bg-brand-soft border-brand'
                      : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <Text
                    className={`text-[14px] font-semibold ${
                      freq === opt.value ? 'text-brand-dark' : 'text-ink-muted'
                    }`}
                  >
                    {opt.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {freq !== 'as_needed' && (
              <LabeledInput
                label="Time 1 (HH:MM 24h)"
                value={time1}
                onChangeText={setTime1}
                placeholder="08:00"
              />
            )}
            {freq === 'multiple_daily' && (
              <LabeledInput
                label="Time 2 (HH:MM 24h)"
                value={time2}
                onChangeText={setTime2}
                placeholder="20:00"
              />
            )}
            {freq === 'fixed_course' && (
              <LabeledInput
                label="End Date (YYYY-MM-DD)"
                value={endDate}
                onChangeText={setEndDate}
                placeholder="2026-12-01"
              />
            )}

            {errorMsg && (
              <View className="bg-red-50 border border-red-200 rounded-2xl p-3 mb-3">
                <Text className="text-[14px] font-semibold text-red-700">{errorMsg}</Text>
              </View>
            )}

            <View className="flex-row gap-3 mt-2">
              <View className="flex-1">
                <PrimaryButton
                  title="Save Medicine"
                  variant="emerald"
                  onPress={handleSaveMedicineAndSchedule}
                  loading={saving}
                />
              </View>
              <View className="flex-1">
                <PrimaryButton
                  title="Cancel"
                  variant="outline"
                  onPress={resetAddForm}
                />
              </View>
            </View>
          </Card>
        </ScrollView>
      </Modal>

      <Modal visible={detailModal !== null} animationType="slide">
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
          {detailModal && (
            <>
              <Text className="text-[26px] font-extrabold text-ink mb-1">
                {detailModal.medicine.display_name}
              </Text>
              <Text className="text-[14.5px] font-medium text-ink-muted mb-4">
                {detailModal.medicine.generic_name || 'Custom entry'} •{' '}
                {detailModal.medicine.strength}
              </Text>

              {detailModal.education ? (
                <Card>
                  <Text className="text-[14px] font-extrabold text-brand-dark uppercase tracking-wide">
                    Category
                  </Text>
                  <Text className="text-[15.5px] text-ink leading-6 mt-1 mb-3">
                    {detailModal.education.category}
                  </Text>

                  <Text className="text-[14px] font-extrabold text-brand-dark uppercase tracking-wide">
                    Common Uses
                  </Text>
                  <Text className="text-[15.5px] text-ink leading-6 mt-1 mb-3">
                    {detailModal.education.common_uses}
                  </Text>

                  <Text className="text-[14px] font-extrabold text-brand-dark uppercase tracking-wide">
                    How It Works
                  </Text>
                  <Text className="text-[15.5px] text-ink leading-6 mt-1 mb-3">
                    {detailModal.education.mechanism}
                  </Text>

                  <Text className="text-[14px] font-extrabold text-brand-dark uppercase tracking-wide">
                    Common Side Effects
                  </Text>
                  <Text className="text-[15.5px] text-ink leading-6 mt-1 mb-3">
                    {detailModal.education.side_effects}
                  </Text>

                  <Text className="text-[14px] font-extrabold text-brand-dark uppercase tracking-wide">
                    Important Precautions
                  </Text>
                  <Text className="text-[15.5px] text-ink leading-6 mt-1 mb-3">
                    {detailModal.education.precautions}
                  </Text>

                  <View className="bg-slate-50 rounded-2xl p-3.5 border border-slate-200 mt-2">
                    <Text className="text-[13px] font-semibold text-ink-muted">
                      Source: {detailModal.education.source_name} (Verified{' '}
                      {detailModal.education.verified_at})
                    </Text>
                    <Text className="text-[12.5px] text-ink-soft mt-1 leading-5">
                      {detailModal.education.disclaimer}
                    </Text>
                  </View>
                </Card>
              ) : (
                <Card>
                  <Text className="text-[15.5px] text-ink leading-6">
                    {detailModal.education_notice}
                  </Text>
                </Card>
              )}

              <PrimaryButton title="Close" onPress={() => setDetailModal(null)} />
            </>
          )}
        </ScrollView>
      </Modal>
    </ScrollView>
  );
}
