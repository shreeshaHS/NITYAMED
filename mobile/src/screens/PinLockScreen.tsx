/** Elevated 4-digit Quick PIN Lock Screen featuring NityaMed Emblem. */

import React, { useState } from 'react';
import { Text, View } from 'react-native';
import { Card, LabeledInput, PrimaryButton } from '../components/AccessibleUI';
import { BrandMark } from '../components/BrandMark';
import { t } from '../i18n/translations';
import type { SupportedLang } from '../types/api';

interface PinLockScreenProps {
  lang: SupportedLang;
  expectedPin: string;
  onUnlock: () => void;
  onUsePasswordInstead: () => void;
}

export function PinLockScreen({
  lang,
  expectedPin,
  onUnlock,
  onUsePasswordInstead,
}: PinLockScreenProps) {
  const [pin, setPin] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handleVerify = () => {
    if (pin.trim() === expectedPin) {
      setError(null);
      onUnlock();
    } else {
      setError('Incorrect 4-digit PIN.');
      setPin('');
    }
  };

  return (
    <View className="flex-1 p-6 justify-center bg-surface-canvas max-w-md w-full self-center">
      <Card className="p-6">
        <View className="items-center mb-4">
          <BrandMark size={56} />
          <Text className="text-[22px] font-extrabold text-ink mt-3">{t(lang, 'appTitle')}</Text>
          <Text className="text-[15px] text-ink-muted text-center mt-1">{t(lang, 'pinPrompt')}</Text>
        </View>

        <LabeledInput
          label="4-Digit Quick PIN"
          value={pin}
          onChangeText={setPin}
          keyboardType="number-pad"
          maxLength={4}
          secureTextEntry
          placeholder="••••"
        />
        {error && (
          <View className="bg-red-50 border border-red-200 rounded-xl p-3 mb-3">
            <Text className="text-[14px] font-semibold text-red-700">{error}</Text>
          </View>
        )}
        <PrimaryButton title={t(lang, 'unlock')} onPress={handleVerify} />
        <PrimaryButton
          title={t(lang, 'logout')}
          variant="outline"
          onPress={onUsePasswordInstead}
          className="mt-3"
        />
      </Card>
    </View>
  );
}
