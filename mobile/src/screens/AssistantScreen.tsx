/** Elevated Multilingual Hybrid Assistant Screen with NityaMed Avatar & Explicit Confirmation Gates. */

import * as Speech from 'expo-speech';
import React, { useState } from 'react';
import { ScrollView, Text, TouchableOpacity, useWindowDimensions, View } from 'react-native';
import { Card, FadeSlideIn, LabeledInput, PrimaryButton } from '../components/AccessibleUI';
import { BrandMark } from '../components/BrandMark';
import { MicIcon } from '../components/Icons';
import { t } from '../i18n/translations';
import { api } from '../services/api';
import { Colors } from '../theme';
import type { AssistantResponse, SupportedLang } from '../types/api';

interface AssistantScreenProps {
  lang: SupportedLang;
  isOnline: boolean;
  onDataChanged: () => Promise<void>;
}

const QUICK_PROMPTS: Record<SupportedLang, string[]> = {
  en: [
    'Which medicines should I take today?',
    'How many tablets do I have left?',
    'When is my next dose?',
    'When should I refill my medicine?',
  ],
  kn: [
    'ಇಂದು ನಾನು ಯಾವ ಮಾತ್ರೆಗಳನ್ನು ತೆಗೆದುಕೊಳ್ಳಬೇಕು',
    'ನನ್ ಹತ್ರ ಎಷ್ಟ್ ಗುಳಿಗೆ ಉಂಟು',
    'ನನ್ನ ಮುಂದಿನ ಡೋಸ್ ಯಾವಾಗ ಇದೆ',
    'ನಾನು ಯಾವಾಗ ಹೊಸ ಮಾತ್ರೆ ಖರೀದಿಸಬೇಕು',
  ],
  hi: [
    'आज मुझे कौन सी दवाइयां लेनी हैं',
    'मेरे पास कितनी गोलियां बची हैं',
    'मेरी अगली खुराक कब है',
    'मुझे अपनी दवाई कब रीफिल करनी चाहिए',
  ],
};

const TTS_LOCALE: Record<SupportedLang, string> = {
  en: 'en-IN',
  kn: 'kn-IN',
  hi: 'hi-IN',
};

export function AssistantScreen({ lang, isOnline, onDataChanged }: AssistantScreenProps) {
  const { width } = useWindowDimensions();
  const twoCol = width >= 880;

  const [query, setQuery] = useState('');
  const [speakReplies, setSpeakReplies] = useState(true);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<Array<{ user: string; bot: AssistantResponse }>>([]);
  const [pendingConfirm, setPendingConfirm] = useState<AssistantResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const speakText = (text: string, replyLang: SupportedLang) => {
    if (!speakReplies) return;
    try {
      Speech.stop();
      Speech.speak(text, { language: TTS_LOCALE[replyLang] || 'en-IN' });
    } catch {
      // Ignore if device TTS voice is unavailable.
    }
  };

  const handleSend = async (customText?: string) => {
    const text = (customText ?? query).trim();
    if (!text) return;
    setErrorMsg(null);
    setLoading(true);
    try {
      const res = await api.askAssistantText(text, lang);
      setHistory((prev) => [{ user: text, bot: res }, ...prev]);
      setPendingConfirm(res.requires_confirmation ? res : null);
      if (!customText) setQuery('');
      speakText(res.reply_text, res.language);
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Assistant requires internet connectivity.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async (approved: boolean) => {
    if (!pendingConfirm?.confirmation_token) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.confirmAssistantAction(pendingConfirm.confirmation_token, approved);
      setHistory((prev) => [{ user: approved ? 'Confirmed' : 'Cancelled', bot: res }, ...prev]);
      setPendingConfirm(null);
      speakText(res.reply_text, res.language);
      if (approved) await onDataChanged();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Unable to complete confirmation.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScrollView className="flex-1" contentContainerStyle={{ padding: 20, paddingBottom: 48 }}>
      <View className="flex-row items-center mb-4">
        <View className="w-11 h-11 rounded-2xl bg-brand-soft items-center justify-center mr-3">
          <MicIcon size={22} color={Colors.primary} />
        </View>
        <View>
          <Text className="text-[25px] font-extrabold text-ink tracking-tight">
            {t(lang, 'tabAssistant')}
          </Text>
          <Text className="text-[13.5px] text-ink-muted">
            English • ಕನ್ನಡ • हिन्दी (Regional dialect friendly)
          </Text>
        </View>
      </View>

      {!isOnline && (
        <View className="bg-amber-50 border border-amber-200 rounded-2xl p-4 mb-4">
          <Text className="text-[14.5px] font-semibold text-amber-800 leading-6">
            You are offline. Voice/text assistant requires internet — please use the Today tab for
            offline dose confirmations.
          </Text>
        </View>
      )}

      <Card>
        <LabeledInput
          label={t(lang, 'assistantHint')}
          value={query}
          onChangeText={setQuery}
          placeholder={t(lang, 'assistantHint')}
        />
        <View className="flex-row gap-2.5 mt-1">
          <View className="flex-1">
            <PrimaryButton
              title={t(lang, 'send')}
              variant="emerald"
              onPress={() => handleSend()}
              loading={loading}
              disabled={!isOnline}
            />
          </View>
          <View className="flex-1">
            <PrimaryButton
              title={speakReplies ? 'Voice Reply: ON' : 'Voice Reply: OFF'}
              variant="outline"
              onPress={() => setSpeakReplies((prev) => !prev)}
            />
          </View>
        </View>

        <Text className="text-[13.5px] font-bold text-ink-muted mt-5 mb-2.5">
          Quick Tap Examples:
        </Text>
        <View className={twoCol ? 'flex-row flex-wrap -mx-1.5' : 'gap-2'}>
          {QUICK_PROMPTS[lang].map((prompt) => (
            <View key={prompt} className={twoCol ? 'w-1/2 px-1.5 mb-2.5' : 'w-full'}>
              <TouchableOpacity
                disabled={!isOnline || loading}
                onPress={() => handleSend(prompt)}
                className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200"
              >
                <Text className="text-[15px] font-semibold text-brand-dark">{prompt}</Text>
              </TouchableOpacity>
            </View>
          ))}
        </View>
      </Card>

      {errorMsg && (
        <View className="bg-red-50 border border-red-200 rounded-2xl p-3.5 mb-4">
          <Text className="text-[14.5px] font-semibold text-red-700">{errorMsg}</Text>
        </View>
      )}

      {pendingConfirm && (
        <FadeSlideIn>
          <Card className="bg-brand-soft/80 border-2 border-brand">
            <Text className="text-[19px] font-extrabold text-brand-dark">
              Confirmation Required
            </Text>
            <Text className="text-[15.5px] text-ink leading-6 my-3">
              {pendingConfirm.reply_text}
            </Text>
            <View className="flex-row gap-2.5">
              <View className="flex-1">
                <PrimaryButton
                  title={t(lang, 'confirmAction')}
                  variant="emerald"
                  loading={loading}
                  onPress={() => handleConfirm(true)}
                />
              </View>
              <View className="flex-1">
                <PrimaryButton
                  title={t(lang, 'cancelAction')}
                  variant="danger"
                  loading={loading}
                  onPress={() => handleConfirm(false)}
                />
              </View>
            </View>
          </Card>
        </FadeSlideIn>
      )}

      {history.map((item, idx) => (
        <FadeSlideIn key={idx}>
          <Card>
            <View className="bg-slate-100 self-end px-4 py-2.5 rounded-2xl rounded-tr-sm mb-3 max-w-[90%]">
              <Text className="text-[15px] font-semibold text-ink">{item.user}</Text>
            </View>

            <View className="flex-row items-start">
              <View className="mr-2.5 mt-0.5">
                <BrandMark size={28} />
              </View>
              <View className="flex-1 bg-brand-soft/60 border border-brand/15 px-4 py-3 rounded-2xl rounded-tl-sm">
                <Text className="text-[16px] text-brand-deep leading-6 font-medium">
                  {item.bot.reply_text}
                </Text>
                <Text className="text-[12px] font-semibold text-ink-soft mt-2">
                  Intent: {item.bot.intent} ({item.bot.classification_source})
                </Text>
              </View>
            </View>
          </Card>
        </FadeSlideIn>
      ))}
    </ScrollView>
  );
}
