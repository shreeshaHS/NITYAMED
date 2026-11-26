/** Conversational Gemini-style Hybrid Voice & Text Assistant Screen with Sticky Composer & Live Auto-Scroll. */

import * as Speech from 'expo-speech';
import {
  ExpoSpeechRecognitionModule,
  useSpeechRecognitionEvent,
} from 'expo-speech-recognition';
import React, { useEffect, useRef, useState } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Text,
  TextInput,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import {
  Card,
  FadeSlideIn,
  PrimaryButton,
  PulseRingHalo,
  VoiceWaveform,
} from '../components/AccessibleUI';
import { BrandMark } from '../components/BrandMark';
import { MicIcon, SendIcon, SparkleIcon, VolumeIcon } from '../components/Icons';
import { t } from '../i18n/translations';
import { api } from '../services/api';
import { CardShadow, Colors, FloatingShadow } from '../theme';
import type { AssistantResponse, SupportedLang } from '../types/api';

interface AssistantScreenProps {
  lang: SupportedLang;
  isOnline: boolean;
  onDataChanged: () => Promise<void>;
}

interface ChatTurn {
  id: string;
  user: string;
  viaVoice?: boolean;
  bot: AssistantResponse;
}

const QUICK_PROMPTS: Record<SupportedLang, string[]> = {
  en: [
    'Which medicines should I take today?',
    'Show verified medicines from Micro Labs',
    'How many tablets do I have left?',
    'When is my next dose?',
  ],
  kn: [
    'ಇಂದು ನಾನು ಯಾವ ಮಾತ್ರೆಗಳನ್ನು ತೆಗೆದುಕೊಳ್ಳಬೇಕು',
    'ಸಿಪ್ಲಾ ಕಂಪನಿಯ ಔಷಧಿಗಳನ್ನು ತೋರಿಸಿ',
    'ನನ್ ಹತ್ರ ಎಷ್ಟ್ ಗುಳಿಗೆ ಉಂಟು',
    'ನನ್ನ ಮುಂದಿನ ಡೋಸ್ ಯಾವಾಗ ಇದೆ',
  ],
  hi: [
    'आज मुझे कौन सी दवाइयां लेनी हैं',
    'सिप्ला कंपनी की दवाइयां दिखाओ',
    'मेरे पास कितनी गोलियां बची हैं',
    'मेरी अगली खुराक कब है',
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
  const [liveTranscript, setLiveTranscript] = useState('');
  const [speakReplies, setSpeakReplies] = useState(true);
  const [speaking, setSpeaking] = useState(false);
  const [listening, setListening] = useState(false);
  const [loading, setLoading] = useState(false);
  const [history, setHistory] = useState<ChatTurn[]>([]);
  const [pendingConfirm, setPendingConfirm] = useState<AssistantResponse | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const scrollRef = useRef<React.ComponentRef<typeof ScrollView> | null>(null);
  const sendLatestRef = useRef<(customText?: string, viaVoice?: boolean) => Promise<void>>(
    async () => {}
  );

  const scrollToBottom = () => {
    setTimeout(() => {
      scrollRef.current?.scrollToEnd({ animated: true });
    }, 80);
  };

  useEffect(() => {
    scrollToBottom();
  }, [history.length, listening, loading, pendingConfirm]);

  const speakText = (text: string, replyLang: SupportedLang) => {
    try {
      Speech.stop();
      setSpeaking(true);
      Speech.speak(text, {
        language: TTS_LOCALE[replyLang] || 'en-IN',
        onDone: () => setSpeaking(false),
        onStopped: () => setSpeaking(false),
        onError: () => setSpeaking(false),
      });
    } catch {
      setSpeaking(false);
    }
  };

  const handleSend = async (customText?: string, viaVoice = false) => {
    const text = (customText ?? query).trim();
    if (!text) return;
    setErrorMsg(null);
    setLiveTranscript('');
    if (!customText) setQuery('');
    setLoading(true);
    try {
      const res = await api.askAssistantText(text, lang);
      setHistory((prev) => [
        ...prev,
        { id: `${Date.now()}-${prev.length}`, user: text, viaVoice, bot: res },
      ]);
      setPendingConfirm(res.requires_confirmation ? res : null);
      if (speakReplies) speakText(res.reply_text, res.language);
      if (
        !res.requires_confirmation &&
        (res.intent === 'confirm_dose' ||
          res.intent === 'update_stock_purchase' ||
          res.intent === 'skip_dose' ||
          res.intent === 'snooze_dose')
      ) {
        await onDataChanged();
      }
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Assistant requires internet connectivity.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    sendLatestRef.current = handleSend;
  });

  useSpeechRecognitionEvent('start', () => {
    setListening(true);
    setLiveTranscript('');
  });

  useSpeechRecognitionEvent('end', () => {
    setListening(false);
  });

  useSpeechRecognitionEvent('error', (event) => {
    setListening(false);
    setLiveTranscript('');
    if (event.error !== 'aborted' && event.error !== 'no-speech') {
      setErrorMsg(event.message || 'Voice recognition could not complete. Please try again.');
    }
  });

  useSpeechRecognitionEvent('result', (event) => {
    const transcript = event.results?.[0]?.transcript?.trim();
    if (!transcript) return;
    setLiveTranscript(transcript);
    setQuery(transcript);
    if (event.isFinal) {
      setListening(false);
      setLiveTranscript('');
      setQuery('');
      void sendLatestRef.current(transcript, true);
    }
  });

  const handleToggleVoiceInput = async () => {
    setErrorMsg(null);
    if (listening) {
      try {
        ExpoSpeechRecognitionModule.stop();
      } catch {
        setListening(false);
      }
      return;
    }

    try {
      if (!ExpoSpeechRecognitionModule.isRecognitionAvailable()) {
        setErrorMsg(
          'Speech recognition is unavailable on this browser/device. Try Chrome/Edge on web or use your keyboard microphone.'
        );
        return;
      }

      try {
        Speech.stop();
        setSpeaking(false);
      } catch {
        // Ignore TTS stop error.
      }

      const perm = await ExpoSpeechRecognitionModule.requestPermissionsAsync();
      if (!perm.granted) {
        setErrorMsg('Microphone permission is required for voice input.');
        return;
      }

      ExpoSpeechRecognitionModule.start({
        lang: TTS_LOCALE[lang] || 'en-IN',
        interimResults: true,
        maxAlternatives: 1,
        continuous: false,
      });
    } catch (err) {
      setListening(false);
      setErrorMsg(
        err instanceof Error ? err.message : 'Unable to start voice recognition right now.'
      );
    }
  };

  const handleConfirm = async (approved: boolean) => {
    if (!pendingConfirm?.confirmation_token) return;
    setLoading(true);
    setErrorMsg(null);
    try {
      const res = await api.confirmAssistantAction(pendingConfirm.confirmation_token, approved);
      setHistory((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${prev.length}`,
          user: approved ? t(lang, 'confirmAction') : t(lang, 'cancelAction'),
          bot: res,
        },
      ]);
      setPendingConfirm(null);
      if (speakReplies) speakText(res.reply_text, res.language);
      if (approved) await onDataChanged();
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : 'Unable to complete confirmation.');
    } finally {
      setLoading(false);
    }
  };

  const latestTurn = history.length > 0 ? history[history.length - 1] : null;
  const followUpChips =
    latestTurn && !pendingConfirm
      ? latestTurn.bot.suggested_replies?.length
        ? latestTurn.bot.suggested_replies
        : QUICK_PROMPTS[lang].slice(0, 3)
      : QUICK_PROMPTS[lang];

  return (
    <KeyboardAvoidingView
      className="flex-1 bg-surface-canvas"
      behavior={Platform.OS === 'ios' ? 'padding' : undefined}
    >
      {/* Compact Sticky Top Assistant Header */}
      <View className="bg-white/95 border-b border-slate-200/80 px-4 py-3 flex-row items-center justify-between">
        <View className="flex-row items-center flex-1 pr-2">
          <View className="w-10 h-10 rounded-2xl bg-brand-soft items-center justify-center mr-3">
            {listening || speaking ? (
              <VoiceWaveform active={listening || speaking} color={listening ? '#DC2626' : Colors.primary} />
            ) : (
              <SparkleIcon size={20} color={Colors.primary} />
            )}
          </View>
          <View className="flex-1">
            <Text className="text-[17.5px] font-extrabold text-ink tracking-tight" numberOfLines={1}>
              {t(lang, 'tabAssistant')}
            </Text>
            <Text className="text-[12px] font-medium text-ink-muted" numberOfLines={1}>
              {listening
                ? `Listening (${TTS_LOCALE[lang]})...`
                : speaking
                  ? 'Speaking response...'
                  : 'English • ಕನ್ನಡ • हिन्दी • Company & Dose AI'}
            </Text>
          </View>
        </View>

        <View className="flex-row items-center gap-2">
          <TouchableOpacity
            onPress={() => {
              if (speakReplies) {
                try {
                  Speech.stop();
                  setSpeaking(false);
                } catch {
                  // Ignore.
                }
              }
              setSpeakReplies((prev) => !prev);
            }}
            className={`flex-row items-center px-3 py-1.5 rounded-full border ${
              speakReplies ? 'bg-brand-soft border-brand/25' : 'bg-slate-100 border-slate-200'
            }`}
          >
            <VolumeIcon size={14} color={speakReplies ? Colors.primaryDark : Colors.textMuted} />
            <Text
              className={`text-[12px] font-bold ml-1.5 ${
                speakReplies ? 'text-brand-dark' : 'text-ink-muted'
              }`}
            >
              {speakReplies ? 'Voice ON' : 'Muted'}
            </Text>
          </TouchableOpacity>

          {history.length > 0 && (
            <TouchableOpacity
              onPress={() => {
                setHistory([]);
                setPendingConfirm(null);
              }}
              className="px-2.5 py-1.5 rounded-full bg-slate-100 border border-slate-200"
            >
              <Text className="text-[12px] font-bold text-ink-muted">Clear</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>

      {!isOnline && (
        <View className="mx-4 mt-3 bg-amber-50 border border-amber-200 rounded-2xl p-3.5">
          <Text className="text-[13.5px] font-semibold text-amber-800 leading-5">
            {t(lang, 'assistantOfflineMsg')}
          </Text>
        </View>
      )}

      {/* Main Visible Scrollable Conversation Feed */}
      <ScrollView
        ref={scrollRef}
        className="flex-1"
        contentContainerStyle={{ padding: 16, paddingBottom: 24, flexGrow: 1 }}
        onContentSizeChange={scrollToBottom}
      >
        {history.length === 0 ? (
          <FadeSlideIn>
            <View className="items-center pt-4 pb-3 px-2">
              <View
                className="w-20 h-20 rounded-[28px] bg-brand-dark items-center justify-center mb-4"
                style={FloatingShadow}
              >
                <BrandMark size={48} variant="inverse" />
              </View>
              <Text className="text-[22px] font-extrabold text-ink text-center tracking-tight">
                NityaMed Voice Assistant
              </Text>
              <Text className="text-[14px] text-ink-muted text-center leading-6 max-w-md mt-1.5">
                Speak naturally or type in English, Kannada, or Hindi to check your schedule, search medicines by company, track stock, or confirm doses.
              </Text>

              <View className={`w-full mt-5 ${twoCol ? 'flex-row flex-wrap -mx-1.5' : 'gap-2.5'}`}>
                {QUICK_PROMPTS[lang].map((prompt, idx) => (
                  <View key={prompt} className={twoCol ? 'w-1/2 px-1.5 mb-2.5' : 'w-full'}>
                    <TouchableOpacity
                      disabled={!isOnline || loading}
                      onPress={() => handleSend(prompt)}
                      className="bg-white border border-slate-200/90 rounded-2xl p-4 flex-row items-center justify-between"
                      style={CardShadow}
                    >
                      <View className="flex-1 pr-3">
                        <Text className="text-[11px] font-extrabold uppercase tracking-wider text-brand mb-0.5">
                          Example {idx + 1}
                        </Text>
                        <Text className="text-[15px] font-bold text-ink leading-5">{prompt}</Text>
                      </View>
                      <View className="w-8 h-8 rounded-full bg-brand-soft items-center justify-center">
                        <SendIcon size={14} color={Colors.primary} />
                      </View>
                    </TouchableOpacity>
                  </View>
                ))}
              </View>
            </View>
          </FadeSlideIn>
        ) : (
          <View className="gap-4">
            {history.map((item) => (
              <FadeSlideIn key={item.id}>
                <View className="gap-2.5">
                  {/* Sent User Chat Bubble (Always Visible Above Bot Reply) */}
                  <View className="items-end">
                    <View
                      className="bg-brand-dark px-4 py-3 rounded-[20px] rounded-tr-sm max-w-[85%]"
                      style={CardShadow}
                    >
                      {item.viaVoice && (
                        <Text className="text-[10.5px] font-bold uppercase tracking-wider text-emerald-300 mb-0.5">
                          Voice Input
                        </Text>
                      )}
                      <Text className="text-[15px] font-semibold text-white leading-6">
                        {item.user}
                      </Text>
                    </View>
                  </View>

                  {/* Assistant Grounded Reply Bubble */}
                  <View className="flex-row items-start max-w-[94%]">
                    <View className="mr-2.5 mt-1">
                      <BrandMark size={30} />
                    </View>
                    <View
                      className="flex-1 bg-white border border-slate-200/90 px-4 py-3.5 rounded-[22px] rounded-tl-sm"
                      style={CardShadow}
                    >
                      <Text className="text-[15.5px] text-ink leading-6 font-medium">
                        {item.bot.reply_text}
                      </Text>

                      <View className="flex-row items-center justify-between mt-2.5 pt-2 border-t border-slate-100">
                        <Text className="text-[11.5px] font-bold text-ink-soft">
                          {item.bot.intent.replace(/_/g, ' ')} • {Math.round(item.bot.confidence * 100)}%
                        </Text>
                        <TouchableOpacity
                          onPress={() => speakText(item.bot.reply_text, item.bot.language)}
                          className="flex-row items-center bg-brand-soft px-2.5 py-1 rounded-full"
                        >
                          <VolumeIcon size={12} color={Colors.primaryDark} />
                          <Text className="text-[11.5px] font-bold text-brand-dark ml-1">
                            Listen
                          </Text>
                        </TouchableOpacity>
                      </View>
                    </View>
                  </View>
                </View>
              </FadeSlideIn>
            ))}
          </View>
        )}

        {/* Live Listening / Processing Bubble Right Inside Visible Chat Area */}
        {listening && (
          <FadeSlideIn>
            <View className="mt-3 items-end">
              <View className="bg-red-50 border border-red-200 px-4 py-3 rounded-2xl max-w-[85%] flex-row items-center gap-3">
                <VoiceWaveform active color="#DC2626" />
                <Text className="text-[14px] font-bold text-red-700">
                  {liveTranscript || `Listening in ${TTS_LOCALE[lang]}... Speak now`}
                </Text>
              </View>
            </View>
          </FadeSlideIn>
        )}

        {loading && (
          <FadeSlideIn>
            <View className="mt-3 flex-row items-center">
              <View className="mr-2.5">
                <BrandMark size={28} />
              </View>
              <View className="bg-white border border-slate-200 px-4 py-3 rounded-2xl flex-row items-center gap-2.5">
                <VoiceWaveform active color={Colors.primary} />
                <Text className="text-[13.5px] font-semibold text-ink-muted">
                  Checking verified records...
                </Text>
              </View>
            </View>
          </FadeSlideIn>
        )}
      </ScrollView>

      {/* Pinned Inline Confirmation Card (Visible Above Composer Without Scrolling) */}
      {pendingConfirm && (
        <View className="mx-3 mb-2">
          <FadeSlideIn>
            <Card className="bg-brand-soft border-2 border-brand mb-0 p-4">
              <Text className="text-[16px] font-extrabold text-brand-dark">
                {t(lang, 'confirmationRequired')}
              </Text>
              <Text className="text-[14.5px] text-ink leading-5 my-2">
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
        </View>
      )}

      {errorMsg && (
        <View className="mx-3 mb-2 bg-red-50 border border-red-200 rounded-2xl px-3.5 py-2.5">
          <Text className="text-[13px] font-semibold text-red-700">{errorMsg}</Text>
        </View>
      )}

      {/* Sticky Bottom Composer Bar with Contextual Suggestions & Animated Mic Orb */}
      <View className="bg-white border-t border-slate-200/90 pt-2.5 pb-3 px-3">
        {history.length > 0 && !pendingConfirm && (
          <ScrollView
            horizontal
            showsHorizontalScrollIndicator={false}
            contentContainerStyle={{ gap: 8, paddingBottom: 8 }}
          >
            {followUpChips.map((chip) => (
              <TouchableOpacity
                key={chip}
                disabled={!isOnline || loading}
                onPress={() => handleSend(chip)}
                className="bg-slate-100 border border-slate-200 px-3.5 py-1.5 rounded-full"
              >
                <Text className="text-[12.5px] font-bold text-brand-dark">{chip}</Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        )}

        <View className="flex-row items-center gap-2">
          <PulseRingHalo active={listening} size={50} color="#DC2626">
            <TouchableOpacity
              onPress={handleToggleVoiceInput}
              disabled={!isOnline || loading}
              className={`w-[50px] h-[50px] rounded-full items-center justify-center ${
                listening ? 'bg-red-600' : 'bg-brand'
              } ${!isOnline ? 'opacity-50' : ''}`}
              style={CardShadow}
            >
              <MicIcon size={22} color="#FFFFFF" />
            </TouchableOpacity>
          </PulseRingHalo>

          <TextInput
            value={query}
            onChangeText={setQuery}
            placeholder={t(lang, 'assistantHint')}
            placeholderTextColor={Colors.textMuted}
            editable={isOnline && !loading}
            onSubmitEditing={() => handleSend()}
            returnKeyType="send"
            className="flex-1 min-h-[48px] max-h-[96px] bg-slate-100 border border-slate-200 rounded-full px-4 py-2.5 text-[15px] text-ink"
          />

          <TouchableOpacity
            onPress={() => handleSend()}
            disabled={!isOnline || loading || !query.trim()}
            className={`w-[48px] h-[48px] rounded-full items-center justify-center ${
              query.trim() && isOnline ? 'bg-brand-mint' : 'bg-slate-200'
            }`}
          >
            <SendIcon size={19} color={query.trim() && isOnline ? '#FFFFFF' : '#94A3B8'} />
          </TouchableOpacity>
        </View>
      </View>
    </KeyboardAvoidingView>
  );
}
