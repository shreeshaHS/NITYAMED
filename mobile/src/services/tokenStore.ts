/** Platform-aware secure storage for JWT tokens and optional local 4-digit PIN. */

import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const ACCESS_KEY = 'nityamed_access_token';
const REFRESH_KEY = 'nityamed_refresh_token';
const PIN_KEY = 'nityamed_local_pin';
const INTRO_SEEN_KEY = 'nityamed_intro_seen';

async function getItem(key: string): Promise<string | null> {
  if (Platform.OS === 'web') {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  }
  return SecureStore.getItemAsync(key);
}

async function setItem(key: string, value: string): Promise<void> {
  if (Platform.OS === 'web') {
    window.localStorage.setItem(key, value);
    return;
  }
  await SecureStore.setItemAsync(key, value);
}

async function removeItem(key: string): Promise<void> {
  if (Platform.OS === 'web') {
    window.localStorage.removeItem(key);
    return;
  }
  await SecureStore.deleteItemAsync(key);
}

export const tokenStore = {
  async saveTokens(access: string, refresh: string): Promise<void> {
    await setItem(ACCESS_KEY, access);
    await setItem(REFRESH_KEY, refresh);
  },
  async getAccessToken(): Promise<string | null> {
    return getItem(ACCESS_KEY);
  },
  async getRefreshToken(): Promise<string | null> {
    return getItem(REFRESH_KEY);
  },
  async clearSession(): Promise<void> {
    await removeItem(ACCESS_KEY);
    await removeItem(REFRESH_KEY);
  },
  async savePin(pin: string): Promise<void> {
    await setItem(PIN_KEY, pin);
  },
  async getPin(): Promise<string | null> {
    return getItem(PIN_KEY);
  },
  async clearPin(): Promise<void> {
    await removeItem(PIN_KEY);
  },
  async hasSeenIntro(): Promise<boolean> {
    return (await getItem(INTRO_SEEN_KEY)) === 'true';
  },
  async setIntroSeen(seen: boolean): Promise<void> {
    if (seen) {
      await setItem(INTRO_SEEN_KEY, 'true');
    } else {
      await removeItem(INTRO_SEEN_KEY);
    }
  },
};
