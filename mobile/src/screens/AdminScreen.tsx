/** Full System Administrator Console: Platform Telemetry, Catalogue Curation, Sweep & SMTP Diagnostics. */

import React, { useEffect, useState } from 'react';
import {
  Modal,
  ScrollView,
  Switch,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import { Card, FadeSlideIn, LabeledInput, PrimaryButton } from '../components/AccessibleUI';
import { ChartIcon, PillIcon, RefreshIcon, SettingsIcon, ShieldIcon } from '../components/Icons';
import { api, ApiError } from '../services/api';
import { CardShadow, Colors } from '../theme';
import type { AdminCatalogueListItem, AdminHealthMetrics, DosageForm } from '../types/api';

interface AdminScreenProps {
  onLogout: () => Promise<void>;
}

type AdminTab = 'overview' | 'catalogue' | 'maintenance';
type StatusFilter = 'all' | 'active' | 'deprecated' | 'unverified';

const FORMS: DosageForm[] = ['tablet', 'capsule', 'syrup', 'inhaler', 'drops', 'injection', 'other'];

export function AdminScreen({ onLogout }: AdminScreenProps) {
  const { width } = useWindowDimensions();
  const isWide = width >= 860;

  const [tab, setTab] = useState<AdminTab>('overview');
  const [metrics, setMetrics] = useState<AdminHealthMetrics | null>(null);
  const [items, setItems] = useState<AdminCatalogueListItem[]>([]);
  const [searchQ, setSearchQ] = useState('');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

  const [sweepMsg, setSweepMsg] = useState<string | null>(null);
  const [seedMsg, setSeedMsg] = useState<string | null>(null);
  const [testEmailAddr, setTestEmailAddr] = useState('');
  const [testEmailMsg, setTestEmailMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // Create Catalogue Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [cBrand, setCBrand] = useState('');
  const [cGeneric, setCGeneric] = useState('');
  const [cStrength, setCStrength] = useState('');
  const [cForm, setCForm] = useState<DosageForm>('tablet');
  const [cPackSize, setCPackSize] = useState('10');
  const [cManufacturer, setCManufacturer] = useState('');
  const [cCategory, setCCategory] = useState('');
  const [cUses, setCUses] = useState('');
  const [cMechanism, setCMechanism] = useState('');
  const [cSideEffects, setCSideEffects] = useState('');
  const [cPrecautions, setCPrecautions] = useState('');
  const [cSourceName, setCSourceName] = useState('National Formulary Reference');

  // Edit Catalogue Modal State
  const [editItem, setEditItem] = useState<AdminCatalogueListItem | null>(null);
  const [eBrand, setEBrand] = useState('');
  const [eGeneric, setEGeneric] = useState('');
  const [ePackSize, setEPackSize] = useState('');
  const [eManufacturer, setEManufacturer] = useState('');
  const [eVerified, setEVerified] = useState(true);

  const loadAdminData = async (q = searchQ, filter = statusFilter) => {
    setErrorMsg(null);
    try {
      const [m, list] = await Promise.all([
        api.adminGetMetrics(),
        api.adminListCatalogue(q, filter),
      ]);
      setMetrics(m);
      setItems(list);
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Unable to load admin telemetry.');
    }
  };

  useEffect(() => {
    loadAdminData('', 'all');
  }, []);

  const handleSweep = async () => {
    setBusy(true);
    setSweepMsg(null);
    try {
      const res = await api.adminRunMaintenanceSweep();
      setSweepMsg(
        `Sweep completed: ${res.expired_doses_marked} overdue dose(s) marked unconfirmed, ${res.refill_alerts_created} refill/backup alert(s) processed.`
      );
      await loadAdminData();
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Maintenance sweep failed.');
    } finally {
      setBusy(false);
    }
  };

  const handleSeed = async () => {
    setBusy(true);
    setSeedMsg(null);
    try {
      const res = await api.adminSeedCatalogue();
      setSeedMsg(`Curated seed complete: ${res.inserted} new medicine(s) inserted.`);
      await loadAdminData();
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Reseed failed.');
    } finally {
      setBusy(false);
    }
  };

  const handleTestEmail = async () => {
    if (!testEmailAddr.trim()) {
      setTestEmailMsg({ ok: false, text: 'Enter a recipient email address first.' });
      return;
    }
    setBusy(true);
    setTestEmailMsg(null);
    try {
      const res = await api.adminTestEmail(testEmailAddr.trim());
      setTestEmailMsg({ ok: res.sent, text: res.detail });
    } catch (err) {
      setTestEmailMsg({
        ok: false,
        text: err instanceof ApiError ? err.message : 'Failed to run SMTP test.',
      });
    } finally {
      setBusy(false);
    }
  };

  const handleToggleDeprecate = async (item: AdminCatalogueListItem) => {
    setBusy(true);
    try {
      await api.adminUpdateCatalogue(item.id, { is_deprecated: !item.is_deprecated });
      await loadAdminData();
    } finally {
      setBusy(false);
    }
  };

  const openEditModal = (item: AdminCatalogueListItem) => {
    setEditItem(item);
    setEBrand(item.brand_name);
    setEGeneric(item.generic_name);
    setEPackSize(item.standard_pack_size || '');
    setEManufacturer(item.manufacturer || '');
    setEVerified(item.is_verified);
  };

  const handleSaveEdit = async () => {
    if (!editItem) return;
    setBusy(true);
    setErrorMsg(null);
    try {
      await api.adminUpdateCatalogue(editItem.id, {
        brand_name: eBrand.trim(),
        generic_name: eGeneric.trim(),
        standard_pack_size: ePackSize.trim() ? Number(ePackSize) : null,
        manufacturer: eManufacturer.trim() || null,
        is_verified: eVerified,
      });
      setEditItem(null);
      await loadAdminData();
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Update failed.');
    } finally {
      setBusy(false);
    }
  };

  const handleCreateCatalogue = async () => {
    setBusy(true);
    setErrorMsg(null);
    try {
      await api.adminCreateCatalogue({
        brand_name: cBrand.trim(),
        generic_name: cGeneric.trim(),
        strength: cStrength.trim(),
        dosage_form: cForm,
        standard_pack_size: cPackSize.trim() ? Number(cPackSize) : null,
        pack_unit: cForm === 'syrup' || cForm === 'drops' ? 'ml' : cForm === 'inhaler' ? 'puff' : cForm,
        manufacturer: cManufacturer.trim() || null,
        education: {
          category: cCategory.trim(),
          common_uses: cUses.trim(),
          mechanism: cMechanism.trim(),
          side_effects: cSideEffects.trim(),
          precautions: cPrecautions.trim(),
          source_name: cSourceName.trim(),
          verified_at: new Date().toISOString().slice(0, 10),
        },
      });
      setShowCreateModal(false);
      setCBrand('');
      setCGeneric('');
      setCStrength('');
      setCManufacturer('');
      setCCategory('');
      setCUses('');
      setCMechanism('');
      setCSideEffects('');
      setCPrecautions('');
      await loadAdminData();
    } catch (err) {
      setErrorMsg(
        err instanceof ApiError
          ? err.message
          : 'Please complete all required medicine & education fields (min 5 chars).'
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <ScrollView className="flex-1" contentContainerStyle={{ padding: 20, paddingBottom: 48 }}>
      {/* Hero Banner */}
      <FadeSlideIn>
        <View className="bg-brand-dark rounded-[28px] p-6 mb-5" style={CardShadow}>
          <View className="flex-row items-start justify-between flex-wrap gap-3">
            <View className="flex-1">
              <Text className="text-[12px] font-bold uppercase tracking-wider text-emerald-300 mb-1">
                System Administration
              </Text>
              <Text className="text-[25px] font-extrabold text-white tracking-tight">
                NityaMed Admin Console
              </Text>
              <Text className="text-[14px] text-teal-100 mt-1 leading-5">
                Platform health telemetry, verified catalogue curation & job maintenance (Zero
                patient PII access)
              </Text>
            </View>
            <View className="flex-row gap-2">
              <TouchableOpacity
                onPress={() => loadAdminData()}
                className="bg-white/15 px-3.5 py-2.5 rounded-xl flex-row items-center"
              >
                <RefreshIcon size={16} color="#FFFFFF" />
                <Text className="text-[13px] font-bold text-white ml-1.5">Refresh</Text>
              </TouchableOpacity>
              <TouchableOpacity
                onPress={onLogout}
                className="bg-red-500/90 px-3.5 py-2.5 rounded-xl"
              >
                <Text className="text-[13px] font-bold text-white">Sign Out</Text>
              </TouchableOpacity>
            </View>
          </View>
        </View>
      </FadeSlideIn>

      {/* Segmented Admin Tabs */}
      <View className="flex-row bg-white border border-slate-200 p-1.5 rounded-2xl mb-5">
        <TouchableOpacity
          onPress={() => setTab('overview')}
          className={`flex-1 py-2.5 rounded-xl flex-row items-center justify-center ${
            tab === 'overview' ? 'bg-brand-soft' : ''
          }`}
        >
          <ChartIcon size={17} color={tab === 'overview' ? Colors.primary : Colors.textMuted} />
          <Text
            className={`ml-1.5 text-[14px] font-bold ${
              tab === 'overview' ? 'text-brand-dark' : 'text-ink-muted'
            }`}
          >
            Overview & Health
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          onPress={() => setTab('catalogue')}
          className={`flex-1 py-2.5 rounded-xl flex-row items-center justify-center ${
            tab === 'catalogue' ? 'bg-brand-soft' : ''
          }`}
        >
          <PillIcon size={17} color={tab === 'catalogue' ? Colors.primary : Colors.textMuted} />
          <Text
            className={`ml-1.5 text-[14px] font-bold ${
              tab === 'catalogue' ? 'text-brand-dark' : 'text-ink-muted'
            }`}
          >
            Catalogue
          </Text>
        </TouchableOpacity>
        <TouchableOpacity
          onPress={() => setTab('maintenance')}
          className={`flex-1 py-2.5 rounded-xl flex-row items-center justify-center ${
            tab === 'maintenance' ? 'bg-brand-soft' : ''
          }`}
        >
          <SettingsIcon size={17} color={tab === 'maintenance' ? Colors.primary : Colors.textMuted} />
          <Text
            className={`ml-1.5 text-[14px] font-bold ${
              tab === 'maintenance' ? 'text-brand-dark' : 'text-ink-muted'
            }`}
          >
            Maintenance & SMTP
          </Text>
        </TouchableOpacity>
      </View>

      {errorMsg && (
        <View className="bg-red-50 border border-red-200 rounded-2xl p-3.5 mb-4">
          <Text className="text-[14px] font-semibold text-red-700">{errorMsg}</Text>
        </View>
      )}

      {/* TAB 1: OVERVIEW & SYSTEM HEALTH */}
      {tab === 'overview' && metrics && (
        <FadeSlideIn>
          <View className="flex-row flex-wrap -mx-1.5 mb-2">
            {[
              {
                label: 'Registered Accounts',
                val: `${metrics.total_users}`,
                sub: `${metrics.verified_users} verified • ${metrics.email_backup_opt_in_users} email opt-in`,
                tone: 'bg-white',
              },
              {
                label: 'Active Patient Meds',
                val: `${metrics.active_personal_medicines}`,
                sub: `${metrics.total_notifications} notifications queued/sent`,
                tone: 'bg-white',
              },
              {
                label: 'Dose Adherence Ledger',
                val: `${metrics.confirmed_dose_events}/${metrics.total_dose_events}`,
                sub: `${metrics.expired_unconfirmed_events} expired unconfirmed`,
                tone: 'bg-white',
              },
              {
                label: 'Verified Catalogue',
                val: `${metrics.verified_catalogue_items.toLocaleString()}`,
                sub: `${metrics.deprecated_catalogue_items} deprecated • ${metrics.total_catalogue_items.toLocaleString()} total`,
                tone: 'bg-brand-soft/60',
              },
            ].map((stat) => (
              <View
                key={stat.label}
                className={isWide ? 'w-1/2 px-1.5 mb-3' : 'w-full px-1.5 mb-3'}
              >
                <Card className={`${stat.tone} mb-0`}>
                  <Text className="text-[13px] font-bold text-ink-soft uppercase tracking-wide">
                    {stat.label}
                  </Text>
                  <Text className="text-[30px] font-extrabold text-brand-dark mt-1">
                    {stat.val}
                  </Text>
                  <Text className="text-[13.5px] font-medium text-ink-muted mt-1">{stat.sub}</Text>
                </Card>
              </View>
            ))}
          </View>

          <Card>
            <Text className="text-[18px] font-extrabold text-ink mb-3">
              Subsystem Diagnostics
            </Text>
            <View className="flex-row flex-wrap gap-2.5">
              <View
                className={`px-3.5 py-2 rounded-full ${
                  metrics.smtp_configured ? 'bg-emerald-100' : 'bg-amber-100'
                }`}
              >
                <Text
                  className={`text-[13px] font-bold ${
                    metrics.smtp_configured ? 'text-emerald-800' : 'text-amber-800'
                  }`}
                >
                  SMTP Mail: {metrics.smtp_configured ? 'Configured' : 'Dev Fallback'}
                </Text>
              </View>
              <View
                className={`px-3.5 py-2 rounded-full ${
                  metrics.require_email_verification ? 'bg-emerald-100' : 'bg-slate-100'
                }`}
              >
                <Text
                  className={`text-[13px] font-bold ${
                    metrics.require_email_verification ? 'text-emerald-800' : 'text-ink-muted'
                  }`}
                >
                  OTP Verify: {metrics.require_email_verification ? 'Enforced' : 'Optional'}
                </Text>
              </View>
              <View
                className={`px-3.5 py-2 rounded-full ${
                  metrics.ml_model_ready ? 'bg-brand-soft' : 'bg-red-100'
                }`}
              >
                <Text
                  className={`text-[13px] font-bold ${
                    metrics.ml_model_ready ? 'text-brand-dark' : 'text-red-700'
                  }`}
                >
                  ML Intent Model: {metrics.ml_model_ready ? metrics.ml_model_name : 'Not Loaded'}
                </Text>
              </View>
            </View>

            <View className="bg-slate-50 border border-slate-200 rounded-2xl p-3.5 mt-4 flex-row items-start">
              <ShieldIcon size={20} color={Colors.primary} />
              <Text className="text-[13.5px] text-ink-muted ml-2.5 flex-1 leading-5">
                Privacy Architecture Active: Administrators only view anonymized system counts and
                catalogue metadata. Patient emails, names, and personal medication histories remain
                strictly inaccessible from this console.
              </Text>
            </View>
          </Card>

          <View className="flex-row gap-3">
            <View className="flex-1">
              <PrimaryButton
                title="Open Catalogue Manager"
                onPress={() => setTab('catalogue')}
              />
            </View>
            <View className="flex-1">
              <PrimaryButton
                title="Run Maintenance Sweep"
                variant="emerald"
                loading={busy}
                onPress={handleSweep}
              />
            </View>
          </View>
          {sweepMsg && (
            <View className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3.5 mt-3">
              <Text className="text-[14px] font-semibold text-emerald-800">{sweepMsg}</Text>
            </View>
          )}
        </FadeSlideIn>
      )}

      {/* TAB 2: CATALOGUE MANAGER */}
      {tab === 'catalogue' && (
        <FadeSlideIn>
          <Card>
            <View className="flex-row items-center justify-between flex-wrap gap-2 mb-3">
              <Text className="text-[19px] font-extrabold text-ink">
                Shared Medicine Catalogue
              </Text>
              <PrimaryButton
                title="+ Add Verified Medicine"
                variant="emerald"
                onPress={() => setShowCreateModal(true)}
              />
            </View>

            <LabeledInput
              label="Search Brand or Generic Salt"
              value={searchQ}
              onChangeText={setSearchQ}
              placeholder="e.g., Fempro, Valprol, Dolo, Metformin"
            />

            <View className="flex-row flex-wrap gap-2 mb-3">
              {(['all', 'active', 'deprecated', 'unverified'] as StatusFilter[]).map((f) => (
                <TouchableOpacity
                  key={f}
                  onPress={() => {
                    setStatusFilter(f);
                    loadAdminData(searchQ, f);
                  }}
                  className={`px-3.5 py-2 rounded-full border ${
                    statusFilter === f
                      ? 'bg-brand border-brand'
                      : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <Text
                    className={`text-[13px] font-bold capitalize ${
                      statusFilter === f ? 'text-white' : 'text-ink-muted'
                    }`}
                  >
                    {f}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <PrimaryButton
              title="Search Catalogue"
              onPress={() => loadAdminData(searchQ, statusFilter)}
              loading={busy}
            />
          </Card>

          <View className={isWide ? 'flex-row flex-wrap -mx-2' : ''}>
            {items.map((item) => (
              <View key={item.id} className={isWide ? 'w-1/2 px-2' : 'w-full'}>
                <Card accentColor={item.is_deprecated ? Colors.danger : Colors.emerald}>
                  <View className="flex-row items-start justify-between gap-2">
                    <View className="flex-1">
                      <Text className="text-[17.5px] font-extrabold text-ink">
                        {item.brand_name}
                      </Text>
                      <Text className="text-[13.5px] text-ink-muted mt-0.5">
                        {item.generic_name} • {item.strength} • {item.dosage_form}
                      </Text>
                      {item.manufacturer && (
                        <Text className="text-[12.5px] text-ink-soft mt-0.5">
                          Mfr: {item.manufacturer}
                          {item.standard_pack_size ? ` • Pack: ${item.standard_pack_size}` : ''}
                        </Text>
                      )}
                    </View>
                    <View
                      className={`px-2.5 py-1 rounded-full ${
                        item.is_deprecated
                          ? 'bg-red-100'
                          : item.is_verified
                            ? 'bg-emerald-100'
                            : 'bg-amber-100'
                      }`}
                    >
                      <Text
                        className={`text-[11.5px] font-bold ${
                          item.is_deprecated
                            ? 'text-red-700'
                            : item.is_verified
                              ? 'text-emerald-800'
                              : 'text-amber-800'
                        }`}
                      >
                        {item.is_deprecated
                          ? 'Deprecated'
                          : item.is_verified
                            ? 'Verified'
                            : 'Unverified'}
                      </Text>
                    </View>
                  </View>

                  <View className="flex-row gap-2.5 mt-3.5">
                    <View className="flex-1">
                      <PrimaryButton
                        title="Edit Details"
                        variant="secondary"
                        onPress={() => openEditModal(item)}
                      />
                    </View>
                    <View className="flex-1">
                      <PrimaryButton
                        title={item.is_deprecated ? 'Restore' : 'Deprecate'}
                        variant={item.is_deprecated ? 'emerald' : 'outline'}
                        onPress={() => handleToggleDeprecate(item)}
                      />
                    </View>
                  </View>
                </Card>
              </View>
            ))}
          </View>
        </FadeSlideIn>
      )}

      {/* TAB 3: MAINTENANCE & SMTP DIAGNOSTICS */}
      {tab === 'maintenance' && (
        <FadeSlideIn>
          <Card accentColor={Colors.accent}>
            <Text className="text-[19px] font-extrabold text-ink">Scheduled Maintenance Sweep</Text>
            <Text className="text-[14.5px] text-ink-muted leading-6 my-2">
              Marks overdue unanswered doses as expired unconfirmed and dispatches deduplicated
              refill & opt-in privacy-safe backup reminder emails.
            </Text>
            <PrimaryButton title="Run Maintenance Sweep Now" onPress={handleSweep} loading={busy} />
            {sweepMsg && (
              <Text className="text-[14px] font-semibold text-emerald-700 mt-2.5">{sweepMsg}</Text>
            )}
          </Card>

          <Card accentColor={Colors.primary}>
            <Text className="text-[19px] font-extrabold text-ink">SMTP Live Email Check</Text>
            <Text className="text-[14px] text-ink-muted leading-5 my-2">
              Verify that Gmail / SMTP credentials in backend/.env send real mail cleanly.
            </Text>
            <LabeledInput
              label="Test Recipient Email"
              value={testEmailAddr}
              onChangeText={setTestEmailAddr}
              autoCapitalize="none"
              keyboardType="email-address"
              placeholder="e.g., nityamed578@gmail.com"
            />
            <PrimaryButton
              title="Send Diagnostic Email"
              variant="emerald"
              loading={busy}
              onPress={handleTestEmail}
            />
            {testEmailMsg && (
              <View
                className={`mt-3 p-3 rounded-2xl border ${
                  testEmailMsg.ok
                    ? 'bg-emerald-50 border-emerald-200'
                    : 'bg-amber-50 border-amber-200'
                }`}
              >
                <Text
                  className={`text-[13.5px] font-semibold ${
                    testEmailMsg.ok ? 'text-emerald-800' : 'text-amber-800'
                  }`}
                >
                  {testEmailMsg.text}
                </Text>
              </View>
            )}
          </Card>

          <Card>
            <Text className="text-[19px] font-extrabold text-ink">Curated Baseline Seed</Text>
            <Text className="text-[14px] text-ink-muted leading-5 my-2">
              Idempotently ensures built-in baseline Indian medicines and verified education cards
              exist in the catalogue.
            </Text>
            <PrimaryButton
              title="Reseed Curated Medicines"
              variant="outline"
              loading={busy}
              onPress={handleSeed}
            />
            {seedMsg && (
              <Text className="text-[14px] font-semibold text-emerald-700 mt-2.5">{seedMsg}</Text>
            )}
          </Card>
        </FadeSlideIn>
      )}

      {/* CREATE VERIFIED MEDICINE MODAL */}
      <Modal visible={showCreateModal} animationType="slide">
        <ScrollView
          className="flex-1 bg-surface-canvas"
          contentContainerStyle={{
            padding: 24,
            paddingBottom: 56,
            maxWidth: 680,
            width: '100%',
            alignSelf: 'center',
          }}
        >
          <Card className="p-6">
            <Text className="text-[22px] font-extrabold text-ink mb-4">
              Add Verified Catalogue Medicine
            </Text>
            <LabeledInput label="Brand Name" value={cBrand} onChangeText={setCBrand} placeholder="e.g., Shelcal 500" />
            <LabeledInput label="Generic / Active Ingredients" value={cGeneric} onChangeText={setCGeneric} placeholder="e.g., Calcium + Vitamin D3" />
            <LabeledInput label="Strength" value={cStrength} onChangeText={setCStrength} placeholder="e.g., 500 mg" />

            <Text className="text-[14px] font-bold text-ink mt-1 mb-2">Dosage Form</Text>
            <View className="flex-row flex-wrap gap-2 mb-4">
              {FORMS.map((f) => (
                <TouchableOpacity
                  key={f}
                  onPress={() => setCForm(f)}
                  className={`px-3.5 py-2 rounded-full border ${
                    cForm === f ? 'bg-brand-soft border-brand' : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <Text className={`text-[13.5px] font-semibold ${cForm === f ? 'text-brand-dark' : 'text-ink-muted'}`}>
                    {f}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>

            <LabeledInput label="Standard Pack Size" value={cPackSize} onChangeText={setCPackSize} keyboardType="decimal-pad" />
            <LabeledInput label="Manufacturer (Optional)" value={cManufacturer} onChangeText={setCManufacturer} />

            <Text className="text-[16px] font-extrabold text-brand-dark mt-3 mb-2">
              Verified Patient Education
            </Text>
            <LabeledInput label="Category" value={cCategory} onChangeText={setCCategory} placeholder="e.g., Mineral Supplement" />
            <LabeledInput label="Common Uses" value={cUses} onChangeText={setCUses} placeholder="Supports calcium intake..." />
            <LabeledInput label="How It Works" value={cMechanism} onChangeText={setCMechanism} placeholder="Provides elemental calcium..." />
            <LabeledInput label="Side Effects" value={cSideEffects} onChangeText={setCSideEffects} placeholder="Mild constipation or bloating" />
            <LabeledInput label="Precautions" value={cPrecautions} onChangeText={setCPrecautions} placeholder="Consult doctor if kidney stones..." />
            <LabeledInput label="Reference Source" value={cSourceName} onChangeText={setCSourceName} />

            {errorMsg && <Text className="text-[14px] font-semibold text-red-700 mb-3">{errorMsg}</Text>}
            <View className="flex-row gap-3 mt-2">
              <View className="flex-1">
                <PrimaryButton title="Save Entry" variant="emerald" loading={busy} onPress={handleCreateCatalogue} />
              </View>
              <View className="flex-1">
                <PrimaryButton title="Cancel" variant="outline" onPress={() => setShowCreateModal(false)} />
              </View>
            </View>
          </Card>
        </ScrollView>
      </Modal>

      {/* EDIT CATALOGUE MODAL */}
      <Modal visible={editItem !== null} animationType="slide">
        <ScrollView
          className="flex-1 bg-surface-canvas"
          contentContainerStyle={{
            padding: 24,
            paddingBottom: 56,
            maxWidth: 620,
            width: '100%',
            alignSelf: 'center',
          }}
        >
          {editItem && (
            <Card className="p-6">
              <Text className="text-[22px] font-extrabold text-ink mb-4">
                Edit Catalogue Item
              </Text>
              <LabeledInput label="Brand Name" value={eBrand} onChangeText={setEBrand} />
              <LabeledInput label="Generic Name" value={eGeneric} onChangeText={setEGeneric} />
              <LabeledInput label="Standard Pack Size" value={ePackSize} onChangeText={setEPackSize} keyboardType="decimal-pad" />
              <LabeledInput label="Manufacturer" value={eManufacturer} onChangeText={setEManufacturer} />
              <View className="flex-row items-center justify-between py-3 mb-4">
                <Text className="text-[15.5px] font-semibold text-ink">Verified Status</Text>
                <Switch value={eVerified} onValueChange={setEVerified} trackColor={{ true: Colors.emerald }} />
              </View>
              <View className="flex-row gap-3">
                <View className="flex-1">
                  <PrimaryButton title="Update Entry" variant="emerald" loading={busy} onPress={handleSaveEdit} />
                </View>
                <View className="flex-1">
                  <PrimaryButton title="Cancel" variant="outline" onPress={() => setEditItem(null)} />
                </View>
              </View>
            </Card>
          )}
        </ScrollView>
      </Modal>
    </ScrollView>
  );
}
