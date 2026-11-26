/** Elevated Medicines Screen: Company & Verified Catalogue Search, Missing Request, Schedule Editor & Education. */

import React, { useEffect, useState } from 'react';
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
const WEEKDAYS = [
  { idx: 0, label: 'Mon' },
  { idx: 1, label: 'Tue' },
  { idx: 2, label: 'Wed' },
  { idx: 3, label: 'Thu' },
  { idx: 4, label: 'Fri' },
  { idx: 5, label: 'Sat' },
  { idx: 6, label: 'Sun' },
];

export function MedicinesScreen({ lang, medicines, isOnline, onRefresh }: MedicinesScreenProps) {
  const { width } = useWindowDimensions();
  const twoCol = width >= 900;

  const [searchQ, setSearchQ] = useState('');
  const [companyFilter, setCompanyFilter] = useState('');
  const [results, setResults] = useState<CatalogueItem[]>([]);
  const [hasSearched, setHasSearched] = useState(false);
  const [searching, setSearching] = useState(false);

  const [statusFilter, setStatusFilter] = useState<'active' | 'paused' | 'completed'>('active');
  const [filteredMeds, setFilteredMeds] = useState<PersonalMedicine[]>(medicines);

  const [showAddForm, setShowAddForm] = useState(false);
  const [selectedCatalogue, setSelectedCatalogue] = useState<CatalogueItem | null>(null);

  const [showRequestModal, setShowRequestModal] = useState(false);
  const [reqBrand, setReqBrand] = useState('');
  const [reqGeneric, setReqGeneric] = useState('');
  const [reqStrength, setReqStrength] = useState('');
  const [reqManufacturer, setReqManufacturer] = useState('');
  const [reqPackSize, setReqPackSize] = useState('10');
  const [reqForm, setReqForm] = useState<DosageForm>('tablet');
  const [infoMsg, setInfoMsg] = useState<string | null>(null);

  const [dosePerIntake, setDosePerIntake] = useState('1');
  const [initialPacks, setInitialPacks] = useState('1');
  const [initialLoose, setInitialLoose] = useState('0');
  const [packSize, setPackSize] = useState('10');
  const [instructions, setInstructions] = useState('');

  const [freq, setFreq] = useState<FrequencyType>('once_daily');
  const [time1, setTime1] = useState('08:00');
  const [time2, setTime2] = useState('20:00');
  const [selectedWeekdays, setSelectedWeekdays] = useState<number[]>([0]);
  const [endDate, setEndDate] = useState('');
  const [createdMedId, setCreatedMedId] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const [detailModal, setDetailModal] = useState<PersonalMedicineDetail | null>(null);
  const [editScheduleMed, setEditScheduleMed] = useState<PersonalMedicine | null>(null);

  useEffect(() => {
    if (statusFilter === 'active') {
      setFilteredMeds(medicines);
    }
  }, [medicines, statusFilter]);

  const handleSelectStatusFilter = async (next: 'active' | 'paused' | 'completed') => {
    setStatusFilter(next);
    setErrorMsg(null);
    if (!isOnline) {
      setFilteredMeds(medicines.filter((m) => m.status === next));
      return;
    }
    try {
      const list = await api.listMedicines(next);
      setFilteredMeds(list);
    } catch {
      setFilteredMeds(next === 'active' ? medicines : []);
    }
  };

  const resetAddForm = () => {
    setShowAddForm(false);
    setSelectedCatalogue(null);
    setDosePerIntake('1');
    setInitialPacks('1');
    setInitialLoose('0');
    setPackSize('10');
    setInstructions('');
    setFreq('once_daily');
    setTime1('08:00');
    setTime2('20:00');
    setSelectedWeekdays([0]);
    setEndDate('');
    setCreatedMedId(null);
    setErrorMsg(null);
  };

  const toggleWeekday = (idx: number) => {
    setSelectedWeekdays((prev) => {
      if (prev.includes(idx)) {
        return prev.length > 1 ? prev.filter((d) => d !== idx) : prev;
      }
      return [...prev, idx].sort((a, b) => a - b);
    });
  };

  const handleSearch = async () => {
    if (!searchQ.trim() && !companyFilter.trim()) return;
    setSearching(true);
    setErrorMsg(null);
    setInfoMsg(null);
    try {
      const hits = await api.searchCatalogue(
        searchQ.trim(),
        undefined,
        companyFilter.trim() || undefined
      );
      setResults(hits);
      setHasSearched(true);
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Search requires internet connection.');
    } finally {
      setSearching(false);
    }
  };

  const openCatalogueAdd = (item: CatalogueItem) => {
    resetAddForm();
    setSelectedCatalogue(item);
    setPackSize(item.standard_pack_size || '10');
    setShowAddForm(true);
  };

  const openRequestModal = () => {
    setErrorMsg(null);
    setInfoMsg(null);
    setReqBrand(searchQ.trim());
    setReqManufacturer(companyFilter.trim());
    setReqGeneric('');
    setReqStrength('');
    setReqPackSize('10');
    setReqForm('tablet');
    setShowRequestModal(true);
  };

  const handleSubmitVerificationRequest = async () => {
    setErrorMsg(null);
    if (!reqBrand.trim() || !reqStrength.trim()) {
      setErrorMsg('Please enter both the medicine name and strength (e.g. 500 mg).');
      return;
    }
    setSaving(true);
    try {
      const submitted = await api.requestCatalogueVerification({
        brand_name: reqBrand.trim(),
        generic_name: reqGeneric.trim() || null,
        strength: reqStrength.trim(),
        dosage_form: reqForm,
        manufacturer: reqManufacturer.trim() || null,
        standard_pack_size: reqPackSize.trim() || null,
      });
      setShowRequestModal(false);
      setInfoMsg(
        `"${submitted.brand_name}" has been submitted for pharmacist/admin verification before scheduling.`
      );
    } catch (err) {
      setErrorMsg(
        err instanceof ApiError
          ? err.message
          : 'Unable to submit medicine verification request.'
      );
    } finally {
      setSaving(false);
    }
  };

  const handleSaveMedicineAndSchedule = async () => {
    setErrorMsg(null);
    if (!selectedCatalogue) {
      setErrorMsg('Only verified catalogue medicines can be scheduled.');
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
        const form = selectedCatalogue.dosage_form;
        const unit = form === 'syrup' || form === 'drops' ? 'ml' : form === 'inhaler' ? 'puff' : form;
        const med = await api.createMedicine({
          catalogue_id: selectedCatalogue.id,
          is_custom: false,
          display_name: selectedCatalogue.brand_name,
          strength: selectedCatalogue.strength,
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
        weekdays: freq === 'weekly' ? selectedWeekdays : undefined,
        start_date: todayStr,
        end_date: freq === 'fixed_course' && endDate.trim() ? endDate.trim() : null,
        horizon_days: 14,
      });

      resetAddForm();
      setResults([]);
      setHasSearched(false);
      setSearchQ('');
      setCompanyFilter('');
      setStatusFilter('active');
      await onRefresh();
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Unable to save medicine.');
    } finally {
      setSaving(false);
    }
  };

  const handleSaveEditedSchedule = async () => {
    if (!editScheduleMed) return;
    setErrorMsg(null);
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
      const todayStr = getLocalDateString();
      const times =
        freq === 'as_needed'
          ? []
          : freq === 'multiple_daily'
            ? [
                { time: time1.trim(), dose: editScheduleMed.dose_per_intake || '1' },
                { time: time2.trim(), dose: editScheduleMed.dose_per_intake || '1' },
              ]
            : [{ time: time1.trim(), dose: editScheduleMed.dose_per_intake || '1' }];

      await api.createSchedule(editScheduleMed.id, {
        frequency_type: freq,
        times,
        weekdays: freq === 'weekly' ? selectedWeekdays : undefined,
        start_date: todayStr,
        end_date: freq === 'fixed_course' && endDate.trim() ? endDate.trim() : null,
        horizon_days: 14,
      });
      setEditScheduleMed(null);
      setDetailModal(null);
      setInfoMsg(`Schedule updated for ${editScheduleMed.display_name}.`);
      await onRefresh();
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Unable to update schedule.');
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
                {t(lang, 'verifiedSearchTitle')}
              </Text>
            </View>
            <LabeledInput
              label={t(lang, 'addMedicine')}
              value={searchQ}
              onChangeText={setSearchQ}
              placeholder={t(lang, 'searchPlaceholder')}
            />
            <LabeledInput
              label={t(lang, 'companyFilterLabel')}
              value={companyFilter}
              onChangeText={setCompanyFilter}
              placeholder={t(lang, 'companyFilterPlaceholder')}
            />
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={{ gap: 8, paddingBottom: 10 }}
            >
              {['Cipla', 'Micro Labs', 'Sun Pharma', 'Abbott', "Dr. Reddy's"].map((cmp) => (
                <TouchableOpacity
                  key={cmp}
                  onPress={async () => {
                    setCompanyFilter(cmp);
                    setSearching(true);
                    setErrorMsg(null);
                    setInfoMsg(null);
                    try {
                      const hits = await api.searchCatalogue(searchQ.trim(), undefined, cmp);
                      setResults(hits);
                      setHasSearched(true);
                    } catch (err) {
                      setErrorMsg(
                        err instanceof ApiError ? err.message : 'Search requires internet connection.'
                      );
                    } finally {
                      setSearching(false);
                    }
                  }}
                  className={`px-3 py-1.5 rounded-full border ${
                    companyFilter === cmp
                      ? 'bg-brand-soft border-brand'
                      : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <Text
                    className={`text-[12.5px] font-bold ${
                      companyFilter === cmp ? 'text-brand-dark' : 'text-ink-muted'
                    }`}
                  >
                    {cmp}
                  </Text>
                </TouchableOpacity>
              ))}
            </ScrollView>
            <View className="flex-row gap-2.5 mt-1">
              <View className="flex-1">
                <PrimaryButton title="Search" onPress={handleSearch} loading={searching} />
              </View>
              <View className="flex-1">
                <PrimaryButton
                  title={t(lang, 'addCustom')}
                  variant="outline"
                  onPress={openRequestModal}
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
                      {item.manufacturer && (
                        <Text className="text-[12.5px] font-semibold text-brand-dark mt-0.5">
                          {t(lang, 'manufacturerLabel')}: {item.manufacturer}
                        </Text>
                      )}
                    </View>
                    <View className="bg-brand-soft px-3 py-1.5 rounded-full">
                      <Text className="text-[12.5px] font-bold text-brand-dark">+ Add</Text>
                    </View>
                  </TouchableOpacity>
                ))}
              </View>
            )}

            {hasSearched && results.length === 0 && (
              <View className="mt-4 bg-slate-50 border border-slate-200 rounded-2xl p-3.5">
                <Text className="text-[13.5px] text-ink-muted leading-5 mb-2">
                  No verified medicine matched your search. {t(lang, 'verifiedSafetyNotice')}
                </Text>
                <PrimaryButton
                  title={t(lang, 'addCustom')}
                  variant="outline"
                  onPress={openRequestModal}
                />
              </View>
            )}
          </Card>
        </FadeSlideIn>
      )}

      {infoMsg && (
        <View className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3.5 mb-4">
          <Text className="text-[14.5px] font-semibold text-emerald-800">{infoMsg}</Text>
        </View>
      )}

      {errorMsg && (
        <View className="bg-red-50 border border-red-200 rounded-2xl p-3.5 mb-4">
          <Text className="text-[14.5px] font-semibold text-red-700">{errorMsg}</Text>
        </View>
      )}

      {/* Status Filter Tabs (Active / Paused / Completed) */}
      <View className="flex-row gap-2 mb-4">
        {(
          [
            { key: 'active', label: t(lang, 'filterActive') },
            { key: 'paused', label: t(lang, 'filterPaused') },
            { key: 'completed', label: t(lang, 'filterCompleted') },
          ] as const
        ).map((tab) => (
          <TouchableOpacity
            key={tab.key}
            onPress={() => handleSelectStatusFilter(tab.key)}
            className={`px-4 py-2 rounded-full border ${
              statusFilter === tab.key
                ? 'bg-brand border-brand'
                : 'bg-white border-slate-200'
            }`}
          >
            <Text
              className={`text-[13.5px] font-bold ${
                statusFilter === tab.key ? 'text-white' : 'text-ink-muted'
              }`}
            >
              {tab.label}
            </Text>
          </TouchableOpacity>
        ))}
      </View>

      {filteredMeds.length === 0 ? (
        <EmptyState
          title="No Medicines In This List"
          subtitle="Search our verified Indian medicine catalogue above by tablet name, salt, or company."
        />
      ) : (
        <View className={twoCol ? 'flex-row flex-wrap -mx-2' : ''}>
          {filteredMeds.map((med, idx) => (
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
              {`Add ${selectedCatalogue?.brand_name || 'Verified Medicine'}`}
            </Text>

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
            {freq === 'weekly' && (
              <View className="mb-4">
                <Text className="text-[14px] font-bold text-ink mb-2">Select Days of Week</Text>
                <View className="flex-row flex-wrap gap-2">
                  {WEEKDAYS.map((day) => {
                    const activeDay = selectedWeekdays.includes(day.idx);
                    return (
                      <TouchableOpacity
                        key={day.idx}
                        onPress={() => toggleWeekday(day.idx)}
                        className={`px-3 py-1.5 rounded-full border ${
                          activeDay ? 'bg-brand border-brand' : 'bg-slate-50 border-slate-200'
                        }`}
                      >
                        <Text
                          className={`text-[13px] font-bold ${
                            activeDay ? 'text-white' : 'text-ink-muted'
                          }`}
                        >
                          {day.label}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>
              </View>
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

              {isOnline && (
                <View className="gap-2.5 mb-3">
                  <View className="flex-row gap-2.5">
                    <View className="flex-1">
                      <PrimaryButton
                        title={
                          detailModal.medicine.status === 'active'
                            ? 'Pause Medicine'
                            : 'Resume Medicine'
                        }
                        variant="outline"
                        loading={saving}
                        onPress={async () => {
                          setSaving(true);
                          try {
                            await api.updateMedicine(detailModal.medicine.id, {
                              status:
                                detailModal.medicine.status === 'active' ? 'paused' : 'active',
                            });
                            setDetailModal(null);
                            await onRefresh();
                          } catch (err) {
                            setErrorMsg(
                              err instanceof ApiError
                                ? err.message
                                : 'Unable to update medicine status.'
                            );
                          } finally {
                            setSaving(false);
                          }
                        }}
                      />
                    </View>
                    <View className="flex-1">
                      <PrimaryButton
                        title="Mark Completed"
                        variant="secondary"
                        loading={saving}
                        onPress={async () => {
                          setSaving(true);
                          try {
                            await api.updateMedicine(detailModal.medicine.id, {
                              status: 'completed',
                            });
                            setDetailModal(null);
                            await onRefresh();
                          } catch (err) {
                            setErrorMsg(
                              err instanceof ApiError
                                ? err.message
                                : 'Unable to complete medicine.'
                            );
                          } finally {
                            setSaving(false);
                          }
                        }}
                      />
                    </View>
                  </View>

                  <View className="flex-row gap-2.5">
                    <View className="flex-1">
                      <PrimaryButton
                        title={t(lang, 'editSchedule')}
                        variant="primary"
                        onPress={() => {
                          setErrorMsg(null);
                          setEditScheduleMed(detailModal.medicine);
                        }}
                      />
                    </View>
                    <View className="flex-1">
                      <PrimaryButton
                        title={t(lang, 'archiveMedicine')}
                        variant="danger"
                        loading={saving}
                        onPress={async () => {
                          setSaving(true);
                          try {
                            await api.updateMedicine(detailModal.medicine.id, {
                              status: 'archived',
                            });
                            setDetailModal(null);
                            await onRefresh();
                          } catch (err) {
                            setErrorMsg(
                              err instanceof ApiError
                                ? err.message
                                : 'Unable to archive medicine.'
                            );
                          } finally {
                            setSaving(false);
                          }
                        }}
                      />
                    </View>
                  </View>
                </View>
              )}

              <PrimaryButton title="Close" onPress={() => setDetailModal(null)} />
            </>
          )}
        </ScrollView>
      </Modal>

      {/* Request Missing Medicine (Verified-Only Governance Modal) */}
      <Modal visible={showRequestModal} animationType="slide">
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
            <Text className="text-[22px] font-extrabold text-ink mb-2">
              {t(lang, 'requestMissingTitle')}
            </Text>
            <View className="bg-amber-50 border border-amber-200 rounded-2xl p-3.5 mb-4">
              <Text className="text-[13.5px] font-semibold text-amber-900 leading-5">
                {t(lang, 'verifiedSafetyNotice')}
              </Text>
            </View>

            <LabeledInput
              label="Brand / Medicine Name *"
              value={reqBrand}
              onChangeText={setReqBrand}
              placeholder="e.g., Dolo 650"
            />
            <LabeledInput
              label="Generic Salt / Composition (Optional)"
              value={reqGeneric}
              onChangeText={setReqGeneric}
              placeholder="e.g., Paracetamol"
            />
            <LabeledInput
              label="Strength *"
              value={reqStrength}
              onChangeText={setReqStrength}
              placeholder="e.g., 650 mg"
            />
            <LabeledInput
              label="Manufacturer / Company (Optional)"
              value={reqManufacturer}
              onChangeText={setReqManufacturer}
              placeholder="e.g., Micro Labs Ltd"
            />
            <LabeledInput
              label="Standard Pack Size (Optional)"
              value={reqPackSize}
              onChangeText={setReqPackSize}
              placeholder="e.g., 15"
              keyboardType="decimal-pad"
            />

            <Text className="text-[14px] font-bold text-ink mt-2 mb-2">Dosage Form</Text>
            <View className="flex-row flex-wrap gap-2 mb-4">
              {FORMS.map((f) => (
                <TouchableOpacity
                  key={f}
                  onPress={() => setReqForm(f)}
                  className={`px-3.5 py-2 rounded-full border ${
                    reqForm === f ? 'bg-brand-soft border-brand' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <Text
                    className={`text-[14px] font-semibold ${
                      reqForm === f ? 'text-brand-dark' : 'text-ink-muted'
                    }`}
                  >
                    {f}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            {errorMsg && (
              <View className="bg-red-50 border border-red-200 rounded-2xl p-3 mb-3">
                <Text className="text-[14px] font-semibold text-red-700">{errorMsg}</Text>
              </View>
            )}

            <View className="flex-row gap-3 mt-2">
              <View className="flex-1">
                <PrimaryButton
                  title={t(lang, 'submitRequest')}
                  variant="emerald"
                  onPress={handleSubmitVerificationRequest}
                  loading={saving}
                />
              </View>
              <View className="flex-1">
                <PrimaryButton
                  title="Cancel"
                  variant="outline"
                  onPress={() => {
                    setShowRequestModal(false);
                    setErrorMsg(null);
                  }}
                />
              </View>
            </View>
          </Card>
        </ScrollView>
      </Modal>

      {/* Edit Schedule Modal */}
      <Modal visible={editScheduleMed !== null} animationType="slide">
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
              {t(lang, 'editSchedule')}: {editScheduleMed?.display_name}
            </Text>

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
            {freq === 'weekly' && (
              <View className="mb-4">
                <Text className="text-[14px] font-bold text-ink mb-2">Select Days of Week</Text>
                <View className="flex-row flex-wrap gap-2">
                  {WEEKDAYS.map((day) => {
                    const activeDay = selectedWeekdays.includes(day.idx);
                    return (
                      <TouchableOpacity
                        key={day.idx}
                        onPress={() => toggleWeekday(day.idx)}
                        className={`px-3 py-1.5 rounded-full border ${
                          activeDay ? 'bg-brand border-brand' : 'bg-slate-50 border-slate-200'
                        }`}
                      >
                        <Text
                          className={`text-[13px] font-bold ${
                            activeDay ? 'text-white' : 'text-ink-muted'
                          }`}
                        >
                          {day.label}
                        </Text>
                      </TouchableOpacity>
                    );
                  })}
                </View>
              </View>
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
                  title="Save Schedule"
                  variant="emerald"
                  onPress={handleSaveEditedSchedule}
                  loading={saving}
                />
              </View>
              <View className="flex-1">
                <PrimaryButton
                  title="Cancel"
                  variant="outline"
                  onPress={() => {
                    setEditScheduleMed(null);
                    setErrorMsg(null);
                  }}
                />
              </View>
            </View>
          </Card>
        </ScrollView>
      </Modal>
    </ScrollView>
  );
}
