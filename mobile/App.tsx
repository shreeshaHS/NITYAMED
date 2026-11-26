/** Main NityaMed Cross-Platform Entrypoint (Responsive Web Sidebar, Mobile Tabs, Intro & Admin). */

import './global.css';
import NetInfo from '@react-native-community/netinfo';
import { StatusBar } from 'expo-status-bar';
import React, { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Platform,
  SafeAreaView,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import { BrandMark } from './src/components/BrandMark';
import { ToastBanner } from './src/components/AccessibleUI';
import {
  BellIcon,
  CalendarIcon,
  ChartIcon,
  MicIcon,
  PackageIcon,
  PillIcon,
  RefreshIcon,
  SettingsIcon,
  ShieldIcon,
} from './src/components/Icons';
import { DosePopupModal, NotificationDrawerModal } from './src/components/NotificationCenter';
import { t } from './src/i18n/translations';
import { AdminScreen } from './src/screens/AdminScreen';
import { AssistantScreen } from './src/screens/AssistantScreen';
import { AuthScreen } from './src/screens/AuthScreen';
import { InventoryScreen } from './src/screens/InventoryScreen';
import { MedicinesScreen } from './src/screens/MedicinesScreen';
import { OnboardingIntroScreen } from './src/screens/OnboardingIntroScreen';
import { PinLockScreen } from './src/screens/PinLockScreen';
import { ReportsScreen } from './src/screens/ReportsScreen';
import { SettingsScreen } from './src/screens/SettingsScreen';
import { TodayScreen } from './src/screens/TodayScreen';
import { api } from './src/services/api';
import {
  formatDoseNotificationText,
  getWebNotificationPermission,
  requestWebNotificationPermission,
  rescheduleLocalDoseAlarms,
  showWebBrowserPopup,
} from './src/services/notifications';
import { offlineDb } from './src/services/offlineDb';
import { tokenStore } from './src/services/tokenStore';
import { Colors } from './src/theme';
import type {
  AdherenceReport,
  DailyDoseItem,
  InventorySummaryItem,
  NotificationItem,
  PersonalMedicine,
  ProfileResponse,
  RefillPredictionItem,
  SupportedLang,
} from './src/types/api';
import { generateUuid } from './src/utils/uuid';
import { getLocalDateString } from './src/utils/date';

type TabKey = 'today' | 'medicines' | 'inventory' | 'assistant' | 'reports' | 'settings';

export default function App() {
  const { width } = useWindowDimensions();
  const isWide = width >= 860;

  const [booting, setBooting] = useState(true);
  const [showIntro, setShowIntro] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userRole, setUserRole] = useState<'patient' | 'admin'>('patient');
  const [savedPin, setSavedPin] = useState<string | null>(null);
  const [pinLocked, setPinLocked] = useState(false);

  const [lang, setLang] = useState<SupportedLang>('en');
  const [activeTab, setActiveTab] = useState<TabKey>('today');
  const [isOnline, setIsOnline] = useState(true);
  const [pendingSyncCount, setPendingSyncCount] = useState(0);

  const [profile, setProfile] = useState<ProfileResponse | null>(null);
  const [medicines, setMedicines] = useState<PersonalMedicine[]>([]);
  const [selectedDate, setSelectedDate] = useState<string>(() => getLocalDateString());
  const [todayDoses, setTodayDoses] = useState<DailyDoseItem[]>([]);
  const [inventory, setInventory] = useState<InventorySummaryItem[]>([]);
  const [refills, setRefills] = useState<RefillPredictionItem[]>([]);
  const [report, setReport] = useState<AdherenceReport | null>(null);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [notifOpen, setNotifOpen] = useState(false);
  const [popupDose, setPopupDose] = useState<DailyDoseItem | null>(null);
  const [dismissedPopupIds, setDismissedPopupIds] = useState<Record<string, boolean>>({});
  const [popupBusy, setPopupBusy] = useState(false);
  const [toast, setToast] = useState<{ msg: string; tone: 'success' | 'info' | 'error' } | null>(
    null
  );
  const showToast = useCallback((msg: string, tone: 'success' | 'info' | 'error' = 'success') => {
    setToast({ msg, tone });
    setTimeout(() => {
      setToast((prev) => (prev?.msg === msg ? null : prev));
    }, 2600);
  }, []);
  const [webNotifPerm, setWebNotifPerm] = useState<'granted' | 'denied' | 'default' | 'unsupported'>(
    () => getWebNotificationPermission()
  );

  const loadData = useCallback(async (onlineOverride?: boolean, dateOverride?: string) => {
    const online = onlineOverride ?? isOnline;
    const targetDate = dateOverride ?? selectedDate;

    if (Platform.OS !== 'web') {
      const cnt = await offlineDb.getPendingOutboxCount();
      setPendingSyncCount(cnt);
    }

    if (online) {
      try {
        const me = await api.getMe();
        setUserRole(me.role);
        if (me.role === 'admin') {
          return;
        }

        if (Platform.OS !== 'web') {
          await offlineDb.flushOutbox();
          setPendingSyncCount(await offlineDb.getPendingOutboxCount());
        }

        // Priority 1: Load only what Today & Medicines need so the UI appears immediately.
        const [prof, daily, activeMeds] = await Promise.all([
          api.getProfile(),
          api.getDailyDoses(targetDate),
          api.listMedicines('active'),
        ]);

        setProfile(prof);
        setLang(prof.preferred_lang);
        setTodayDoses(daily);
        setMedicines(activeMeds);

        // Priority 2: Load secondary tabs & offline cache in the background without blocking UI.
        void Promise.all([
          api.getInventorySummary(14).then(setInventory).catch(() => undefined),
          api.getRefillPredictions().then(setRefills).catch(() => undefined),
          api.getAdherenceReport(30).then(setReport).catch(() => undefined),
          api.getNotificationHistory(30).then(setNotifications).catch(() => undefined),
          Platform.OS !== 'web'
            ? api.syncBootstrap().then(async (boot) => {
                await offlineDb.hydrateFromBootstrap(boot);
                await rescheduleLocalDoseAlarms(boot.dose_events, prof.lockscreen_privacy);
              }).catch(() => undefined)
            : Promise.resolve(),
        ]);
        return;
      } catch {
        // Fall through to offline SQLite cache on transient error.
      }
    }

    if (Platform.OS !== 'web') {
      const [localMeds, localDoses, cnt] = await Promise.all([
        offlineDb.getLocalMedicines(),
        offlineDb.getLocalDailyDoses(targetDate),
        offlineDb.getPendingOutboxCount(),
      ]);
      setMedicines(localMeds);
      setTodayDoses(localDoses);
      setPendingSyncCount(cnt);
    }
  }, [isOnline, selectedDate]);

  const refreshTodayQuick = useCallback(async () => {
    if (!isOnline) {
      await loadData();
      return;
    }
    try {
      const daily = await api.getDailyDoses(selectedDate);
      setTodayDoses(daily);
      void Promise.all([
        api.getInventorySummary(14).then(setInventory).catch(() => undefined),
        api.getRefillPredictions().then(setRefills).catch(() => undefined),
        api.getAdherenceReport(30).then(setReport).catch(() => undefined),
      ]);
    } catch {
      await loadData();
    }
  }, [isOnline, selectedDate, loadData]);

  const handleSelectDate = useCallback(
    async (nextDate: string) => {
      setSelectedDate(nextDate);
      if (isOnline) {
        try {
          const daily = await api.getDailyDoses(nextDate);
          setTodayDoses(daily);
          return;
        } catch {
          // Fall back to local cache if transient network issue.
        }
      }
      if (Platform.OS !== 'web') {
        const localDoses = await offlineDb.getLocalDailyDoses(nextDate);
        setTodayDoses(localDoses);
      }
    },
    [isOnline]
  );

  useEffect(() => {
    const unsub = NetInfo.addEventListener((state) => {
      const onlineNow = Boolean(state.isConnected && state.isInternetReachable !== false);
      setIsOnline(onlineNow);
    });
    return () => unsub();
  }, []);

  useEffect(() => {
    (async () => {
      try {
        const [access, pin, introSeen] = await Promise.all([
          tokenStore.getAccessToken(),
          tokenStore.getPin(),
          tokenStore.hasSeenIntro(),
        ]);
        if (!introSeen && !access) {
          setShowIntro(true);
        }
        if (access) {
          setIsAuthenticated(true);
          if (pin && Platform.OS !== 'web') {
            setSavedPin(pin);
            setPinLocked(true);
          }
          await loadData();
        }
      } finally {
        setBooting(false);
      }
    })();
  }, [loadData]);

  useEffect(() => {
    if (isAuthenticated && userRole === 'patient' && isOnline && pendingSyncCount > 0) {
      loadData(true);
    }
  }, [isAuthenticated, userRole, isOnline, pendingSyncCount, loadData]);

  const handleFinishIntro = async () => {
    await tokenStore.setIntroSeen(true);
    setShowIntro(false);
  };

  const handleAuthenticated = async () => {
    await tokenStore.setIntroSeen(true);
    setShowIntro(false);
    setIsAuthenticated(true);
    setPinLocked(false);
    await loadData(true);
  };

  const resetClientSessionState = async () => {
    await tokenStore.clearSession();
    await tokenStore.clearPin();
    if (Platform.OS !== 'web') await offlineDb.clearAll();
    setIsAuthenticated(false);
    setUserRole('patient');
    setActiveTab('today');
    setPinLocked(false);
    setSavedPin(null);
    setProfile(null);
    setMedicines([]);
    setTodayDoses([]);
    setInventory([]);
    setRefills([]);
    setReport(null);
    setNotifications([]);
    setPopupDose(null);
    setDismissedPopupIds({});
  };

  const handleLogout = async () => {
    try {
      const refresh = await tokenStore.getRefreshToken();
      if (refresh && isOnline) await api.logout(refresh);
    } catch {
      // Clear local session regardless.
    }
    await resetClientSessionState();
  };

  const handleAccountDeleted = async () => {
    await resetClientSessionState();
  };

  const handleChangeLang = async (nextLang: SupportedLang) => {
    setLang(nextLang);
    if (isAuthenticated && userRole === 'patient' && isOnline) {
      const updated = await api.updateProfile({ preferred_lang: nextLang });
      setProfile(updated);
    }
  };

  const handleUpdatePrivacy = async (mask: boolean) => {
    if (!isOnline) return;
    const updated = await api.updateProfile({ lockscreen_privacy: mask });
    setProfile(updated);
    if (Platform.OS !== 'web') {
      await rescheduleLocalDoseAlarms(todayDoses, mask);
    }
  };

  const handleToggleEmailReminders = async (enabled: boolean) => {
    if (!isOnline) return;
    const updated = await api.updateProfile({ email_reminders_enabled: enabled });
    setProfile(updated);
  };

  // In-app & Browser Pop-up Reminder Watcher (for Web & foreground Mobile)
  useEffect(() => {
    if (!isAuthenticated || userRole !== 'patient') {
      setPopupDose(null);
      return;
    }

    const evaluateDuePopup = () => {
      const nowMs = Date.now();
      const due = todayDoses.find((d) => {
        if (dismissedPopupIds[d.id]) return false;
        if (d.status === 'pending') {
          const schedMs = new Date(d.scheduled_at).getTime();
          return !Number.isNaN(schedMs) && schedMs <= nowMs;
        }
        if (d.status === 'snoozed' && d.snoozed_until) {
          const snoozeMs = new Date(d.snoozed_until).getTime();
          return !Number.isNaN(snoozeMs) && snoozeMs <= nowMs;
        }
        return false;
      });

      if (due) {
        setPopupDose((current) => {
          if (current?.id !== due.id && Platform.OS === 'web') {
            const { title, body } = formatDoseNotificationText(
              due,
              profile?.lockscreen_privacy ?? true
            );
            showWebBrowserPopup(title, body);
          }
          return due;
        });
      }
    };

    evaluateDuePopup();
    const timer = setInterval(evaluateDuePopup, 25000);
    return () => clearInterval(timer);
  }, [isAuthenticated, userRole, todayDoses, dismissedPopupIds, profile?.lockscreen_privacy]);

  const handlePopupConfirmTaken = async (dose: DailyDoseItem) => {
    setPopupBusy(true);
    try {
      if (isOnline) {
        await api.confirmDose(dose.id, dose.expected_qty, generateUuid());
      } else if (Platform.OS !== 'web') {
        await offlineDb.queueOfflineDoseAction(dose, 'DOSE_CONFIRM', dose.expected_qty);
      }
      setDismissedPopupIds((prev) => ({ ...prev, [dose.id]: true }));
      setPopupDose(null);
      await loadData();
    } catch {
      if (Platform.OS !== 'web') {
        await offlineDb.queueOfflineDoseAction(dose, 'DOSE_CONFIRM', dose.expected_qty);
      }
      setDismissedPopupIds((prev) => ({ ...prev, [dose.id]: true }));
      setPopupDose(null);
    } finally {
      setPopupBusy(false);
    }
  };

  const handlePopupSnooze = async (dose: DailyDoseItem) => {
    setPopupBusy(true);
    try {
      if (isOnline) {
        await api.snoozeDose(dose.id, 15);
      }
      setDismissedPopupIds((prev) => ({ ...prev, [dose.id]: true }));
      setPopupDose(null);
      await loadData();
    } catch {
      setDismissedPopupIds((prev) => ({ ...prev, [dose.id]: true }));
      setPopupDose(null);
    } finally {
      setPopupBusy(false);
    }
  };

  const handleEnableWebPopups = async () => {
    const res = await requestWebNotificationPermission();
    setWebNotifPerm(res);
    if (res === 'granted') {
      showWebBrowserPopup('NityaMed Alerts Enabled', 'You will now receive browser pop-up dose reminders.');
    }
  };

  const handleCheckRefills = async () => {
    if (!isOnline) return;
    try {
      const hist = await api.checkRefillAlerts();
      setNotifications(hist);
    } catch {
      // Ignore transient network errors during manual refill poll.
    }
  };

  const handleDismissNotification = async (id: string) => {
    try {
      await api.updateNotificationStatus(id, 'dismissed');
      setNotifications((prev) =>
        prev.map((n) => (n.id === id ? { ...n, delivery_status: 'dismissed' } : n))
      );
    } catch {
      // Ignore transient network errors when dismissing alert.
    }
  };

  if (booting) {
    return (
      <SafeAreaView className="flex-1 items-center justify-center bg-surface-canvas">
        <BrandMark size={64} />
        <ActivityIndicator size="large" color={Colors.primary} style={{ marginTop: 16 }} />
      </SafeAreaView>
    );
  }

  if (showIntro) {
    return (
      <SafeAreaView style={{ flex: 1, width: '100%' }} className="bg-surface-canvas">
        <StatusBar style="dark" />
        <OnboardingIntroScreen
          lang={lang}
          onChangeLang={setLang}
          onFinish={handleFinishIntro}
        />
      </SafeAreaView>
    );
  }

  if (!isAuthenticated) {
    return (
      <SafeAreaView style={{ flex: 1, width: '100%' }} className="bg-surface-canvas">
        <StatusBar style="dark" />
        <AuthScreen
          lang={lang}
          onChangeLang={setLang}
          onAuthenticated={handleAuthenticated}
          onReplayIntro={() => setShowIntro(true)}
        />
      </SafeAreaView>
    );
  }

  if (pinLocked && savedPin) {
    return (
      <SafeAreaView className="flex-1 bg-surface-canvas">
        <StatusBar style="dark" />
        <PinLockScreen
          lang={lang}
          expectedPin={savedPin}
          onUnlock={() => setPinLocked(false)}
          onUsePasswordInstead={handleLogout}
        />
      </SafeAreaView>
    );
  }

  if (userRole === 'admin') {
    return (
      <SafeAreaView className="flex-1 bg-surface-canvas">
        <StatusBar style="dark" />
        <View className="bg-white border-b border-slate-200 px-5 py-3.5 flex-row items-center justify-between">
          <View className="flex-row items-center">
            <BrandMark size={34} />
            <View className="ml-3">
              <Text className="text-[18px] font-extrabold text-ink">NityaMed Admin</Text>
              <Text className="text-[12px] font-semibold text-brand">System Governance</Text>
            </View>
          </View>
          <View className="flex-row items-center bg-brand-soft px-3 py-1.5 rounded-full">
            <ShieldIcon size={15} color={Colors.primary} />
            <Text className="text-[12px] font-bold text-brand-dark ml-1.5">Administrator</Text>
          </View>
        </View>
        <View className="flex-1 w-full max-w-5xl self-center">
          <AdminScreen onLogout={handleLogout} />
        </View>
      </SafeAreaView>
    );
  }

  const tabs: Array<{
    key: TabKey;
    label: string;
    renderIcon: (active: boolean) => React.ReactNode;
  }> = [
    {
      key: 'today',
      label: t(lang, 'tabToday'),
      renderIcon: (a) => <CalendarIcon size={20} color={a ? Colors.primary : Colors.textMuted} />,
    },
    {
      key: 'medicines',
      label: t(lang, 'tabMedicines'),
      renderIcon: (a) => <PillIcon size={20} color={a ? Colors.primary : Colors.textMuted} />,
    },
    {
      key: 'inventory',
      label: t(lang, 'tabInventory'),
      renderIcon: (a) => <PackageIcon size={20} color={a ? Colors.primary : Colors.textMuted} />,
    },
    {
      key: 'assistant',
      label: t(lang, 'tabAssistant'),
      renderIcon: (a) => <MicIcon size={20} color={a ? Colors.primary : Colors.textMuted} />,
    },
    {
      key: 'reports',
      label: t(lang, 'tabReports'),
      renderIcon: (a) => <ChartIcon size={20} color={a ? Colors.primary : Colors.textMuted} />,
    },
    {
      key: 'settings',
      label: t(lang, 'tabSettings'),
      renderIcon: (a) => <SettingsIcon size={20} color={a ? Colors.primary : Colors.textMuted} />,
    },
  ];

  const activeTabMeta = tabs.find((item) => item.key === activeTab) || tabs[0];

  const renderMainScreen = () => {
    switch (activeTab) {
      case 'today':
        return (
          <TodayScreen
            lang={lang}
            displayName={profile?.display_name}
            doses={todayDoses}
            selectedDate={selectedDate}
            onSelectDate={handleSelectDate}
            isOnline={isOnline}
            pendingSyncCount={pendingSyncCount}
            onRefresh={refreshTodayQuick}
            onSyncNow={() => loadData(true)}
            onToast={showToast}
          />
        );
      case 'medicines':
        return (
          <MedicinesScreen
            lang={lang}
            medicines={medicines}
            isOnline={isOnline}
            onRefresh={() => loadData(true)}
          />
        );
      case 'inventory':
        return (
          <InventoryScreen
            lang={lang}
            inventory={inventory}
            refills={refills}
            isOnline={isOnline}
            onRefresh={() => loadData(true)}
          />
        );
      case 'assistant':
        return (
          <AssistantScreen
            lang={lang}
            isOnline={isOnline}
            onDataChanged={() => loadData(true)}
          />
        );
      case 'reports':
        return <ReportsScreen lang={lang} report={report} />;
      case 'settings':
        return (
          <SettingsScreen
            lang={lang}
            profile={profile}
            onChangeLang={handleChangeLang}
            onUpdatePrivacy={handleUpdatePrivacy}
            onToggleEmailReminders={handleToggleEmailReminders}
            onReplayIntro={() => setShowIntro(true)}
            onLogout={handleLogout}
            onAccountDeleted={handleAccountDeleted}
          />
        );
    }
  };

  return (
    <SafeAreaView className="flex-1 bg-surface-canvas">
      <StatusBar style="dark" />
      <ToastBanner message={toast?.msg ?? null} tone={toast?.tone ?? 'success'} />

      <View className="flex-1 flex-row">
        {isWide && (
          <View className="w-[268px] bg-white border-r border-slate-200/90 px-4 py-5 justify-between">
            <View>
              {/* Brand Header */}
              <View className="flex-row items-center px-2 pb-6 mb-4 border-b border-slate-100">
                <BrandMark size={40} />
                <View className="ml-3">
                  <Text className="text-[20px] font-extrabold text-ink tracking-tight">
                    {t(lang, 'appTitle')}
                  </Text>
                  <Text className="text-[12px] font-semibold text-brand">Continuity Care</Text>
                </View>
              </View>

              {/* Vertical Navigation */}
              {tabs.map((tab) => {
                const active = activeTab === tab.key;
                return (
                  <TouchableOpacity
                    key={tab.key}
                    onPress={() => setActiveTab(tab.key)}
                    className={`flex-row items-center px-3.5 py-3.5 rounded-2xl mb-1.5 ${
                      active ? 'bg-brand-soft' : 'bg-transparent'
                    }`}
                  >
                    {tab.renderIcon(active)}
                    <Text
                      className={`ml-3 text-[15px] ${
                        active ? 'font-bold text-brand-dark' : 'font-semibold text-ink-muted'
                      }`}
                    >
                      {tab.label}
                    </Text>
                    {active && <View className="ml-auto w-2 h-2 rounded-full bg-brand-mint" />}
                  </TouchableOpacity>
                );
              })}
            </View>

            {/* Sidebar Status & Patient Chip */}
            <View className="bg-slate-50 rounded-2xl p-3.5 border border-slate-200/80">
              <View className="flex-row items-center justify-between mb-2">
                <View className="flex-row items-center">
                  <View
                    className={`w-2.5 h-2.5 rounded-full mr-2 ${
                      isOnline ? 'bg-brand-mint' : 'bg-amber-600'
                    }`}
                  />
                  <Text className="text-[13px] font-bold text-ink">
                    {isOnline ? 'Synced & Online' : 'Offline Mode'}
                  </Text>
                </View>
                <TouchableOpacity onPress={() => loadData(true)}>
                  <RefreshIcon size={16} color={Colors.primary} />
                </TouchableOpacity>
              </View>
              {profile && (
                <Text className="text-[12.5px] font-medium text-ink-muted" numberOfLines={1}>
                  {profile.display_name} • {profile.preferred_lang.toUpperCase()}
                </Text>
              )}
              {pendingSyncCount > 0 && (
                <Text className="text-[12px] font-bold text-amber-700 mt-1">
                  {pendingSyncCount} offline update(s) queued
                </Text>
              )}
            </View>
          </View>
        )}

        {/* Right / Main Workspace */}
        <View className="flex-1 bg-surface-canvas">
          {/* Top Bar */}
          <View className="bg-white border-b border-slate-200/90 px-5 py-3.5 flex-row items-center justify-between">
            <View className="flex-row items-center">
              {!isWide && <BrandMark size={34} />}
              <View className={!isWide ? 'ml-3' : ''}>
                <Text className="text-[19px] font-extrabold text-ink tracking-tight">
                  {isWide ? activeTabMeta.label : t(lang, 'appTitle')}
                </Text>
                {isWide && profile && (
                  <Text className="text-[12.5px] text-ink-soft font-medium">
                    Medication Continuity Management
                  </Text>
                )}
              </View>
            </View>

            <View className="flex-row items-center gap-2">
              {isWide && (
                <TouchableOpacity
                  onPress={() => loadData(true)}
                  className="flex-row items-center bg-slate-100 px-3 py-1.5 rounded-full"
                >
                  <RefreshIcon size={14} color={Colors.primary} />
                  <Text className="text-[12.5px] font-semibold text-ink ml-1.5">Refresh</Text>
                </TouchableOpacity>
              )}
              <TouchableOpacity
                onPress={() => setNotifOpen(true)}
                className="flex-row items-center bg-brand-soft px-3 py-1.5 rounded-full"
              >
                <BellIcon size={15} color={Colors.primary} />
                {(refills.filter((r) => r.should_alert_now).length +
                  notifications.filter((n) => n.delivery_status !== 'dismissed').length) > 0 && (
                  <View className="ml-1.5 bg-brand-mint px-1.5 py-0.5 rounded-full">
                    <Text className="text-[11px] font-extrabold text-white">
                      {refills.filter((r) => r.should_alert_now).length +
                        notifications.filter((n) => n.delivery_status !== 'dismissed').length}
                    </Text>
                  </View>
                )}
              </TouchableOpacity>
              <View
                className={`flex-row items-center px-3 py-1.5 rounded-full ${
                  isOnline ? 'bg-brand-mintSoft' : 'bg-amber-100'
                }`}
              >
                <View
                  className={`w-2 h-2 rounded-full mr-1.5 ${
                    isOnline ? 'bg-brand-mint' : 'bg-amber-600'
                  }`}
                />
                <Text
                  className={`text-[12.5px] font-bold ${
                    isOnline ? 'text-green-800' : 'text-amber-800'
                  }`}
                >
                  {isOnline ? 'Online' : 'Offline'}
                </Text>
              </View>
            </View>
          </View>

          {/* Main Content Container */}
          <View className="flex-1 w-full max-w-5xl self-center">{renderMainScreen()}</View>
        </View>
      </View>

      {/* Mobile Bottom Tab Bar */}
      {!isWide && (
        <View className="flex-row bg-white border-t border-slate-200 px-1.5 py-2">
          {tabs.map((tab) => {
            const active = activeTab === tab.key;
            return (
              <TouchableOpacity
                key={tab.key}
                onPress={() => setActiveTab(tab.key)}
                className={`flex-1 min-h-[54px] items-center justify-center rounded-2xl mx-0.5 ${
                  active ? 'bg-brand-soft' : ''
                }`}
              >
                {tab.renderIcon(active)}
                <Text
                  numberOfLines={1}
                  className={`text-[11px] mt-1 ${
                    active ? 'font-extrabold text-brand-dark' : 'font-semibold text-ink-soft'
                  }`}
                >
                  {tab.label}
                </Text>
                {active && <View className="w-4 h-1 rounded-full bg-brand mt-0.5" />}
              </TouchableOpacity>
            );
          })}
        </View>
      )}

      <DosePopupModal
        dose={popupDose}
        privacyMasked={profile?.lockscreen_privacy ?? true}
        busy={popupBusy}
        onConfirmTaken={handlePopupConfirmTaken}
        onSnooze={handlePopupSnooze}
        onDismiss={(id) => {
          setDismissedPopupIds((prev) => ({ ...prev, [id]: true }));
          setPopupDose(null);
        }}
      />

      <NotificationDrawerModal
        visible={notifOpen}
        notifications={notifications}
        refills={refills}
        webPermission={webNotifPerm}
        onEnableWebPopups={handleEnableWebPopups}
        onCheckRefills={handleCheckRefills}
        onDismissNotif={handleDismissNotification}
        onClose={() => setNotifOpen(false)}
      />
    </SafeAreaView>
  );
}
