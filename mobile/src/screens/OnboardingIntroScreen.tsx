/** Modern animated multi-slide onboarding intro with official NityaMed vector emblem. */

import React, { useEffect, useRef, useState } from 'react';
import {
  Animated,
  ScrollView,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import { PrimaryButton } from '../components/AccessibleUI';
import { BrandMark } from '../components/BrandMark';
import { ClockIcon, MicIcon, PackageIcon } from '../components/Icons';
import { CardShadow } from '../theme';
import type { SupportedLang } from '../types/api';

interface OnboardingIntroScreenProps {
  lang: SupportedLang;
  onChangeLang: (lang: SupportedLang) => void;
  onFinish: () => void;
}

interface SlideContent {
  key: string;
  accentBg: string;
  tag: Record<SupportedLang, string>;
  title: Record<SupportedLang, string>;
  body: Record<SupportedLang, string>;
}

const SLIDES: SlideContent[] = [
  {
    key: 'welcome',
    accentBg: '#E6F4F1',
    tag: { en: 'CONTINUITY CARE', kn: 'ನಿರಂತರ ಆರೈಕೆ', hi: 'निरंतर देखभाल' },
    title: {
      en: 'Welcome to NityaMed',
      kn: 'ನಿತ್ಯಮೆಡ್‌ಗೆ ಸ್ವಾಗತ',
      hi: 'नित्यमेड में आपका स्वागत है',
    },
    body: {
      en: 'Your calm, intelligent companion for daily medication schedules, stock tracking, and verified medicine guidance.',
      kn: 'ದೈನಂದಿನ ಔಷಧಿ ವೇಳಾಪಟ್ಟಿ, ಸ್ಟಾಕ್ ಟ್ರ್ಯಾಕಿಂಗ್ ಮತ್ತು ದೃಢೀಕೃತ ಮಾಹಿತಿಗಾಗಿ ನಿಮ್ಮ ಸರಳ ಸಂಗಾತಿ.',
      hi: 'दैनिक दवाई नियम, स्टॉक ट्रैकिंग और सत्यापित जानकारी के लिए आपका सरल साथी।',
    },
  },
  {
    key: 'offline',
    accentBg: '#E0F2FE',
    tag: { en: 'OFFLINE ALARMS', kn: 'ಆಫ್‌ಲೈನ್ ಅಲಾರಂ', hi: 'ऑफलाइन अलार्म' },
    title: {
      en: 'Never Miss a Dose',
      kn: 'ಇಂಟರ್ನೆಟ್ ಇಲ್ಲದಿದ್ದರೂ ಕೆಲಸ ಮಾಡುತ್ತದೆ',
      hi: 'ऑफलाइन भी समय पर याद',
    },
    body: {
      en: 'Receive privacy-safe alarms on your phone and confirm doses in two taps. Everything syncs safely when internet returns.',
      kn: 'ಆಫ್‌ಲೈನ್‌ನಲ್ಲಿಯೂ ಅಲಾರಂ ಬರುತ್ತದೆ. ಎರಡು ಟ್ಯಾಪ್‌ಗಳಲ್ಲಿ ಡೋಸ್ ದೃಢೀಕರಿಸಿ—ಇಂಟರ್ನೆಟ್ ಬಂದಾಗ ತಾನಾಗಿಯೇ ಸಿಂಕ್ ಆಗುತ್ತದೆ.',
      hi: 'बिना इंटरनेट के भी अलार्म पाएं और दो टैप में डोज़ कन्फर्म करें। इंटरनेट आने पर डेटा अपने आप सिंक होगा।',
    },
  },
  {
    key: 'stock',
    accentBg: '#DCFCE7',
    tag: { en: 'REFILL PROTECTION', kn: 'ರಿಫಿಲ್ ಎಚ್ಚರಿಕೆ', hi: 'रीफिल सुरक्षा' },
    title: {
      en: 'Never Run Out of Strips',
      kn: 'ಮಾತ್ರೆ ಖಾಲಿಯಾಗುವ ಮೊದಲೇ ಎಚ್ಚರಿಕೆ',
      hi: 'दवाई खत्म होने से पहले अलर्ट',
    },
    body: {
      en: 'Track confirmed strips and loose tablets separately from projections so you always refill on time.',
      kn: 'ನಿಮ್ಮ ಸ್ಟ್ರಿಪ್ ಮತ್ತು ಬಿಡಿ ಮಾತ್ರೆಗಳ ದೃಢೀಕೃತ ಸ್ಟಾಕ್ ಅನ್ನು ಲೆಕ್ಕಹಾಕಿ, ರಿಫಿಲ್ ದಿನಾಂಕವನ್ನು ಮುಂಚಿತವಾಗಿ ತಿಳಿಸುತ್ತದೆ.',
      hi: 'स्ट्रिप और खुली गोलियों का सटीक स्टॉक ट्रैक करें और समय पर रीफिल की जानकारी पाएं।',
    },
  },
  {
    key: 'assistant',
    accentBg: '#EDE9FE',
    tag: { en: 'SAFE ASSISTANT', kn: 'ಸುರಕ್ಷಿತ ಸಹಾಯಕ', hi: 'सुरक्षित सहायक' },
    title: {
      en: 'Speak in Your Own Language',
      kn: 'ಕನ್ನಡ, ಹಿಂದಿ ಮತ್ತು ಇಂಗ್ಲಿಷ್ ಸಹಾಯಕ',
      hi: 'अपनी भाषा में पूछें',
    },
    body: {
      en: 'Ask in English, Kannada, or Hindi. Every action asks your clear confirmation first and never invents medical advice.',
      kn: 'ಕನ್ನಡ, ಹಿಂದಿ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಕೇಳಿ. ನಿಮ್ಮ ಅನುಮತಿ ಇಲ್ಲದೆ ಯಾವುದೇ ಬದಲಾವಣೆ ಮಾಡುವುದಿಲ್ಲ.',
      hi: 'हिंदी, कन्नड़ या अंग्रेज़ी में पूछें। आपकी पुष्टि के बिना कोई बदलाव नहीं किया जाता।',
    },
  },
];

const LANGS: Array<{ code: SupportedLang; label: string }> = [
  { code: 'en', label: 'English' },
  { code: 'kn', label: 'ಕನ್ನಡ' },
  { code: 'hi', label: 'हिन्दी' },
];

export function OnboardingIntroScreen({
  lang,
  onChangeLang,
  onFinish,
}: OnboardingIntroScreenProps) {
  const { width } = useWindowDimensions();
  const isWide = width >= 820;

  const [step, setStep] = useState(0);
  const pulse = useRef(new Animated.Value(1)).current;
  const slideX = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse, { toValue: 1.04, duration: 1200, useNativeDriver: false }),
        Animated.timing(pulse, { toValue: 1.0, duration: 1200, useNativeDriver: false }),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [pulse]);

  useEffect(() => {
    if (step === 0) return;
    slideX.setValue(16);
    Animated.timing(slideX, {
      toValue: 0,
      duration: 240,
      useNativeDriver: false,
    }).start();
  }, [step, slideX]);

  const current = SLIDES[step];
  const isLast = step === SLIDES.length - 1;

  const renderVisual = () => {
    if (current.key === 'welcome') {
      return (
        <View className="w-32 h-32 rounded-[36px] bg-white items-center justify-center border border-brand/15 shadow-sm">
          <BrandMark size={84} />
        </View>
      );
    }
    if (current.key === 'offline') {
      return (
        <View className="w-28 h-28 rounded-[32px] bg-sky-100 items-center justify-center border border-sky-200">
          <ClockIcon size={54} color="#0284C7" />
        </View>
      );
    }
    if (current.key === 'stock') {
      return (
        <View className="w-28 h-28 rounded-[32px] bg-emerald-100 items-center justify-center border border-emerald-200">
          <PackageIcon size={54} color="#059669" />
        </View>
      );
    }
    return (
      <View className="w-28 h-28 rounded-[32px] bg-violet-100 items-center justify-center border border-violet-200">
        <MicIcon size={54} color="#6D28D9" />
      </View>
    );
  };

  return (
    <ScrollView
      style={{ flex: 1, width: '100%' }}
      className="bg-surface-canvas"
      contentContainerStyle={{
        flexGrow: 1,
        width: '100%',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 24,
      }}
    >
      <View className="w-full max-w-3xl self-center">
        {/* Top Bar */}
        <View className="flex-row items-center justify-between mb-6">
          <View className="flex-row items-center">
            <BrandMark size={38} />
            <Text className="text-[22px] font-extrabold text-ink ml-2.5 tracking-tight">
              NityaMed
            </Text>
          </View>
          <TouchableOpacity
            onPress={onFinish}
            className="bg-white border border-slate-200 px-4 py-2 rounded-full"
          >
            <Text className="text-[14px] font-bold text-ink-muted">Skip</Text>
          </TouchableOpacity>
        </View>

        {/* Language Selector Pills */}
        <View className="flex-row justify-center gap-2 mb-6">
          {LANGS.map((opt) => (
            <TouchableOpacity
              key={opt.code}
              onPress={() => onChangeLang(opt.code)}
              className={`px-4 py-2 rounded-full border ${
                lang === opt.code
                  ? 'bg-brand border-brand'
                  : 'bg-white border-slate-200'
              }`}
            >
              <Text
                className={`text-[14px] font-bold ${
                  lang === opt.code ? 'text-white' : 'text-ink-muted'
                }`}
              >
                {opt.label}
              </Text>
            </TouchableOpacity>
          ))}
        </View>

        {/* Main Animated Showcase Card */}
        <Animated.View style={{ transform: [{ translateX: slideX }] }}>
          <View
            className={`bg-white rounded-[32px] border border-slate-200/90 p-7 ${
              isWide ? 'flex-row items-center gap-8' : 'items-center'
            }`}
            style={CardShadow}
          >
            <Animated.View
              style={{ transform: [{ scale: pulse }] }}
              className={`items-center justify-center rounded-[28px] p-6 ${
                isWide ? 'w-56 h-56' : 'mb-6'
              }`}
            >
              {renderVisual()}
            </Animated.View>

            <View className={isWide ? 'flex-1' : 'items-center'}>
              <View
                className="px-3 py-1 rounded-full mb-3 self-start"
                style={{
                  backgroundColor: current.accentBg,
                  alignSelf: isWide ? 'flex-start' : 'center',
                }}
              >
                <Text className="text-[12px] font-extrabold text-brand-dark tracking-wider">
                  {current.tag[lang]}
                </Text>
              </View>

              <Text
                className={`text-[28px] font-extrabold text-ink tracking-tight mb-3 ${
                  isWide ? 'text-left' : 'text-center'
                }`}
              >
                {current.title[lang]}
              </Text>
              <Text
                className={`text-[16px] text-ink-muted leading-7 ${
                  isWide ? 'text-left' : 'text-center'
                }`}
              >
                {current.body[lang]}
              </Text>
            </View>
          </View>
        </Animated.View>

        {/* Progress Dots */}
        <View className="flex-row justify-center items-center gap-2 my-6">
          {SLIDES.map((_, i) => (
            <TouchableOpacity
              key={i}
              onPress={() => setStep(i)}
              className={`h-2.5 rounded-full ${
                i === step ? 'w-8 bg-brand' : 'w-2.5 bg-slate-300'
              }`}
            />
          ))}
        </View>

        {/* Bottom Actions */}
        <View className="flex-row gap-3">
          {step > 0 && (
            <View className="flex-1">
              <PrimaryButton
                title="Back"
                variant="outline"
                onPress={() => setStep((s) => Math.max(0, s - 1))}
              />
            </View>
          )}
          <View className="flex-[2]">
            <PrimaryButton
              title={isLast ? 'Get Started' : 'Next'}
              variant={isLast ? 'emerald' : 'primary'}
              onPress={() => (isLast ? onFinish() : setStep((s) => s + 1))}
            />
          </View>
        </View>
      </View>
    </ScrollView>
  );
}
