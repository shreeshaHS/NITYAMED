/** Elevated Settings Screen: Language, Privacy Controls, Email Reminders, PIN, Export & Account Deletion. */

import React, { useState } from 'react';
import { Platform, ScrollView, Switch, Text, TouchableOpacity, useWindowDimensions, View } from 'react-native';
import { Card, FadeSlideIn, LabeledInput, PrimaryButton } from '../components/AccessibleUI';
import { BellIcon, ShieldIcon } from '../components/Icons';
import { t } from '../i18n/translations';
import { api, ApiError } from '../services/api';
import { tokenStore } from '../services/tokenStore';
import { Colors } from '../theme';
import type { ProfileResponse, SupportedLang } from '../types/api';

interface SettingsScreenProps {
  lang: SupportedLang;
  profile: ProfileResponse | null;
  onChangeLang: (lang: SupportedLang) => Promise<void>;
  onUpdatePrivacy: (mask: boolean) => Promise<void>;
  onToggleEmailReminders: (enabled: boolean) => Promise<void>;
  onReplayIntro: () => void;
  onLogout: () => Promise<void>;
  onAccountDeleted: () => Promise<void>;
}

const LANGS: Array<{ code: SupportedLang; label: string }> = [
  { code: 'en', label: 'English' },
  { code: 'kn', label: 'ಕನ್ನಡ' },
  { code: 'hi', label: 'हिन्दी' },
];

export function SettingsScreen({
  lang,
  profile,
  onChangeLang,
  onUpdatePrivacy,
  onToggleEmailReminders,
  onReplayIntro,
  onLogout,
  onAccountDeleted,
}: SettingsScreenProps) {
  const { width } = useWindowDimensions();
  const twoCol = width >= 880;

  const [pinInput, setPinInput] = useState('');
  const [pinMsg, setPinMsg] = useState<string | null>(null);
  const [exportedPreview, setExportedPreview] = useState<string | null>(null);
  const [exportMsg, setExportMsg] = useState<string | null>(null);

  const [showDeleteBox, setShowDeleteBox] = useState(false);
  const [deletePassword, setDeletePassword] = useState('');
  const [deleteBusy, setDeleteBusy] = useState(false);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const handleSavePin = async () => {
    if (!/^\d{4}$/.test(pinInput.trim())) {
      setPinMsg('Enter exactly 4 digits.');
      return;
    }
    await tokenStore.savePin(pinInput.trim());
    setPinInput('');
    setPinMsg('4-digit Quick PIN saved on this device.');
  };

  const handleExport = async () => {
    setExportMsg(null);
    try {
      const data = await api.exportData();
      const jsonText = JSON.stringify(data, null, 2);
      setExportedPreview(jsonText.slice(0, 1200) + (jsonText.length > 1200 ? '\n...' : ''));

      if (Platform.OS === 'web' && typeof document !== 'undefined') {
        const blob = new Blob([jsonText], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const anchor = document.createElement('a');
        anchor.href = url;
        anchor.download = `nityamed-export-${new Date().toISOString().slice(0, 10)}.json`;
        document.body.appendChild(anchor);
        anchor.click();
        document.body.removeChild(anchor);
        URL.revokeObjectURL(url);
        setExportMsg('Downloaded nityamed-export JSON file.');
      }
    } catch {
      setExportedPreview('Export requires an active internet connection.');
    }
  };

  const handleConfirmDeleteAccount = async () => {
    setDeleteError(null);
    if (!deletePassword) {
      setDeleteError('Please enter your current password to confirm deletion.');
      return;
    }
    setDeleteBusy(true);
    try {
      await api.deleteAccount(deletePassword);
      await onAccountDeleted();
    } catch (err) {
      setDeleteError(
        err instanceof ApiError ? err.message : 'Unable to delete account right now.'
      );
    } finally {
      setDeleteBusy(false);
    }
  };

  return (
    <ScrollView className="flex-1" contentContainerStyle={{ padding: 20, paddingBottom: 48 }}>
      <Text className="text-[26px] font-extrabold text-ink mb-4 tracking-tight">
        {t(lang, 'settingsTitle')}
      </Text>

      {profile && (
        <FadeSlideIn>
          <Card className="bg-brand-dark border-0">
            <View className="flex-row items-center justify-between flex-wrap gap-3">
              <View>
                <Text className="text-[12px] font-bold uppercase tracking-wider text-emerald-300 mb-1">
                  Patient Account
                </Text>
                <Text className="text-[22px] font-extrabold text-white">{profile.display_name}</Text>
                <Text className="text-[14.5px] text-teal-100 mt-0.5">
                  {profile.email} • {profile.timezone}
                </Text>
              </View>
              <View className="bg-white/15 px-3.5 py-2 rounded-full">
                <Text className="text-[13px] font-bold text-white">
                  {profile.preferred_lang.toUpperCase()}
                </Text>
              </View>
            </View>
          </Card>
        </FadeSlideIn>
      )}

      <View className={twoCol ? 'flex-row flex-wrap -mx-2' : ''}>
        <View className={twoCol ? 'w-1/2 px-2' : 'w-full'}>
          <Card>
            <Text className="text-[18px] font-bold text-ink mb-3">{t(lang, 'languageLabel')}</Text>
            <View className="flex-row gap-2.5">
              {LANGS.map((opt) => (
                <TouchableOpacity
                  key={opt.code}
                  onPress={() => onChangeLang(opt.code)}
                  className={`flex-1 py-3 rounded-2xl border items-center ${
                    lang === opt.code
                      ? 'bg-brand-soft border-brand'
                      : 'bg-slate-50 border-slate-200'
                  }`}
                >
                  <Text
                    className={`text-[15px] font-bold ${
                      lang === opt.code ? 'text-brand-dark' : 'text-ink-muted'
                    }`}
                  >
                    {opt.label}
                  </Text>
                </TouchableOpacity>
              ))}
            </View>
          </Card>

          <Card>
            <View className="flex-row items-center mb-3">
              <ShieldIcon size={20} color={Colors.primary} />
              <Text className="text-[18px] font-bold text-ink ml-2">Privacy & Alerts</Text>
            </View>

            <View className="flex-row items-center justify-between py-2 border-b border-slate-100">
              <Text className="text-[15.5px] font-medium text-ink flex-1 pr-3">
                {t(lang, 'lockscreenPrivacy')}
              </Text>
              <Switch
                value={profile?.lockscreen_privacy ?? true}
                onValueChange={onUpdatePrivacy}
                trackColor={{ true: Colors.primary }}
              />
            </View>

            <View className="flex-row items-center justify-between pt-3">
              <View className="flex-1 pr-3">
                <View className="flex-row items-center">
                  <BellIcon size={16} color={Colors.emeraldDark} />
                  <Text className="text-[15.5px] font-semibold text-ink ml-1.5">
                    Email Refill & Reminder Backup
                  </Text>
                </View>
                <Text className="text-[13px] text-ink-muted mt-1 leading-5">
                  Sends privacy-masked alerts (medicine names hidden) to {profile?.email}
                </Text>
              </View>
              <Switch
                value={profile?.email_reminders_enabled ?? false}
                onValueChange={onToggleEmailReminders}
                trackColor={{ true: Colors.emerald }}
              />
            </View>

            {Platform.OS === 'android' && (
              <View className="bg-sky-50 border border-sky-200 rounded-2xl p-3 mt-3">
                <Text className="text-[13px] text-sky-800 leading-5">
                  Android Tip: Disable Battery Optimization for NityaMed so offline reminders always
                  ring on time after restarts.
                </Text>
              </View>
            )}
          </Card>
        </View>

        <View className={twoCol ? 'w-1/2 px-2' : 'w-full'}>
          <Card>
            <LabeledInput
              label={t(lang, 'setPinLabel')}
              value={pinInput}
              onChangeText={setPinInput}
              keyboardType="number-pad"
              maxLength={4}
              secureTextEntry
              placeholder="4 digits (e.g. 1234)"
            />
            <PrimaryButton title={t(lang, 'savePin')} onPress={handleSavePin} />
            {pinMsg && (
              <Text className="text-[13.5px] font-semibold text-emerald-700 mt-2">{pinMsg}</Text>
            )}
          </Card>

          <Card>
            <PrimaryButton
              title="Replay App Welcome Guide"
              variant="secondary"
              onPress={onReplayIntro}
              className="mb-3"
            />
            <PrimaryButton title={t(lang, 'exportData')} variant="outline" onPress={handleExport} />
            {exportMsg && (
              <Text className="text-[13px] font-semibold text-emerald-700 mt-2">{exportMsg}</Text>
            )}
            {exportedPreview && (
              <Text
                className="mt-3 p-3 bg-slate-50 border border-slate-200 rounded-xl text-[12.5px] text-ink"
                style={{ fontFamily: Platform.OS === 'ios' ? 'Courier' : 'monospace' }}
              >
                {exportedPreview}
              </Text>
            )}
          </Card>

          <Card className="border-red-200 bg-red-50/40">
            <PrimaryButton title={t(lang, 'logout')} variant="outline" onPress={onLogout} className="mb-3" />

            {!showDeleteBox ? (
              <PrimaryButton
                title="Delete My Account"
                variant="danger"
                onPress={() => {
                  setShowDeleteBox(true);
                  setDeleteError(null);
                }}
              />
            ) : (
              <View className="mt-1 p-3.5 bg-white rounded-2xl border border-red-200">
                <Text className="text-[15px] font-extrabold text-red-700 mb-1">
                  Permanent Account Deletion
                </Text>
                <Text className="text-[13px] text-ink-muted leading-5 mb-3">
                  This permanently erases your medicines, schedules, dose history, and stock
                  transactions. Enter your password to confirm.
                </Text>
                <LabeledInput
                  label="Current Password"
                  value={deletePassword}
                  onChangeText={setDeletePassword}
                  secureTextEntry
                  placeholder="Enter your password"
                />
                {deleteError && (
                  <Text className="text-[13.5px] font-semibold text-red-700 mb-2.5">
                    {deleteError}
                  </Text>
                )}
                <View className="flex-row gap-2.5">
                  <View className="flex-1">
                    <PrimaryButton
                      title="Confirm Delete"
                      variant="danger"
                      loading={deleteBusy}
                      onPress={handleConfirmDeleteAccount}
                    />
                  </View>
                  <View className="flex-1">
                    <PrimaryButton
                      title="Cancel"
                      variant="outline"
                      onPress={() => {
                        setShowDeleteBox(false);
                        setDeletePassword('');
                        setDeleteError(null);
                      }}
                    />
                  </View>
                </View>
              </View>
            )}
          </Card>
        </View>
      </View>
    </ScrollView>
  );
}
