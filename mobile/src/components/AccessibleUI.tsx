/** Elevated Tailwind-powered UI primitives with accessible touch targets & crisp SVG badges. */

import React, { useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Animated,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
  type ViewStyle,
} from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { CardShadow, Colors, FloatingShadow } from '../theme';
import type { DoseStatus } from '../types/api';
import { BellIcon, PillIcon, ShieldIcon } from './Icons';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'emerald' | 'secondary' | 'danger' | 'outline';
  loading?: boolean;
  disabled?: boolean;
  icon?: React.ReactNode;
  style?: ViewStyle;
  className?: string;
}

export function PrimaryButton({
  title,
  onPress,
  variant = 'primary',
  loading = false,
  disabled = false,
  icon,
  style,
  className = '',
}: ButtonProps) {
  const scale = useRef(new Animated.Value(1)).current;

  const variantClasses: Record<NonNullable<ButtonProps['variant']>, string> = {
    primary: 'bg-brand border border-brand',
    emerald: 'bg-brand-mint border border-brand-mint',
    secondary: 'bg-brand-soft border border-brand/20',
    danger: 'bg-red-700 border border-red-700',
    outline: 'bg-white border-2 border-slate-200',
  };

  const textClasses: Record<NonNullable<ButtonProps['variant']>, string> = {
    primary: 'text-white',
    emerald: 'text-white',
    secondary: 'text-brand-dark',
    danger: 'text-white',
    outline: 'text-brand-dark',
  };

  const spinnerColor = variant === 'outline' || variant === 'secondary' ? Colors.primary : '#FFFFFF';

  const animateTo = (toValue: number) => {
    Animated.spring(scale, {
      toValue,
      useNativeDriver: true,
      speed: 42,
      bounciness: 6,
    }).start();
  };

  return (
    <Animated.View style={[{ transform: [{ scale }] }, style]}>
      <Pressable
        disabled={disabled || loading}
        onPress={onPress}
        onPressIn={() => animateTo(0.96)}
        onPressOut={() => animateTo(1)}
        className={`min-h-[48px] px-4 py-3 rounded-2xl items-center justify-center flex-row ${variantClasses[variant]} ${disabled ? 'opacity-50' : ''} ${className}`}
      >
        {loading ? (
          <ActivityIndicator color={spinnerColor} />
        ) : (
          <View className="flex-row items-center justify-center gap-2">
            {icon}
            <Text className={`text-[15.5px] font-bold text-center tracking-tight ${textClasses[variant]}`}>
              {title}
            </Text>
          </View>
        )}
      </Pressable>
    </Animated.View>
  );
}

export function FadeSlideIn({
  children,
  delay = 0,
  style,
  className = '',
}: {
  children: React.ReactNode;
  delay?: number;
  style?: ViewStyle;
  className?: string;
}) {
  const translateY = useRef(new Animated.Value(12)).current;
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(translateY, {
        toValue: 0,
        duration: 280,
        delay,
        useNativeDriver: false,
      }),
      Animated.timing(opacity, {
        toValue: 1,
        duration: 280,
        delay,
        useNativeDriver: false,
      }),
    ]).start();
  }, [delay, opacity, translateY]);

  return (
    <View className={className} style={style}>
      <Animated.View style={{ opacity, transform: [{ translateY }] }}>{children}</Animated.View>
    </View>
  );
}

export function CircularProgressRing({
  progress,
  size = 86,
  strokeWidth = 8,
  centerLabel,
  centerSublabel,
  trackColor = 'rgba(255,255,255,0.2)',
  fillColor = '#34D399',
  textColor = '#FFFFFF',
  subTextColor = '#A7F3D0',
}: {
  progress: number;
  size?: number;
  strokeWidth?: number;
  centerLabel: string;
  centerSublabel?: string;
  trackColor?: string;
  fillColor?: string;
  textColor?: string;
  subTextColor?: string;
}) {
  const clamped = Math.max(0, Math.min(1, progress));
  const [animatedPct, setAnimatedPct] = useState(clamped);
  const animVal = useRef(new Animated.Value(clamped)).current;

  useEffect(() => {
    const id = animVal.addListener(({ value }) => setAnimatedPct(value));
    Animated.timing(animVal, {
      toValue: clamped,
      duration: 550,
      useNativeDriver: false,
    }).start();
    return () => animVal.removeListener(id);
  }, [animVal, clamped]);

  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference * (1 - animatedPct);

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Svg width={size} height={size}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={trackColor}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={fillColor}
          strokeWidth={strokeWidth}
          fill="none"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={strokeDashoffset}
          strokeLinecap="round"
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </Svg>
      <View
        style={{
          position: 'absolute',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        <Text style={{ color: textColor, fontSize: 18, fontWeight: '800' }}>{centerLabel}</Text>
        {centerSublabel && (
          <Text style={{ color: subTextColor, fontSize: 10.5, fontWeight: '700' }}>
            {centerSublabel}
          </Text>
        )}
      </View>
    </View>
  );
}

export function VoiceWaveform({
  active,
  color = Colors.primary,
}: {
  active: boolean;
  color?: string;
}) {
  const b1 = useRef(new Animated.Value(6)).current;
  const b2 = useRef(new Animated.Value(14)).current;
  const b3 = useRef(new Animated.Value(9)).current;
  const b4 = useRef(new Animated.Value(16)).current;

  useEffect(() => {
    if (!active) {
      b1.setValue(6);
      b2.setValue(10);
      b3.setValue(8);
      b4.setValue(6);
      return;
    }
    const mkBar = (val: Animated.Value, maxH: number, dur: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.timing(val, { toValue: maxH, duration: dur, useNativeDriver: false }),
          Animated.timing(val, { toValue: 5, duration: dur, useNativeDriver: false }),
        ])
      );
    const anim = Animated.parallel([
      mkBar(b1, 20, 280),
      mkBar(b2, 26, 220),
      mkBar(b3, 22, 310),
      mkBar(b4, 18, 250),
    ]);
    anim.start();
    return () => anim.stop();
  }, [active, b1, b2, b3, b4]);

  return (
    <View style={{ flexDirection: 'row', alignItems: 'center', gap: 3, height: 26 }}>
      {[b1, b2, b3, b4].map((val, idx) => (
        <Animated.View
          key={idx}
          style={{
            width: 4,
            height: val,
            borderRadius: 99,
            backgroundColor: color,
          }}
        />
      ))}
    </View>
  );
}

export function PulseRingHalo({
  active,
  size = 56,
  color = '#DC2626',
  children,
}: {
  active: boolean;
  size?: number;
  color?: string;
  children: React.ReactNode;
}) {
  const scale = useRef(new Animated.Value(1)).current;
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!active) {
      scale.setValue(1);
      opacity.setValue(0);
      return;
    }
    const loop = Animated.loop(
      Animated.parallel([
        Animated.timing(scale, { toValue: 1.38, duration: 950, useNativeDriver: true }),
        Animated.sequence([
          Animated.timing(opacity, { toValue: 0.45, duration: 250, useNativeDriver: true }),
          Animated.timing(opacity, { toValue: 0, duration: 700, useNativeDriver: true }),
        ]),
      ])
    );
    loop.start();
    return () => loop.stop();
  }, [active, opacity, scale]);

  return (
    <View style={{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }}>
      <Animated.View
        pointerEvents="none"
        style={{
          position: 'absolute',
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: color,
          opacity,
          transform: [{ scale }],
        }}
      />
      {children}
    </View>
  );
}

export function ToastBanner({
  message,
  tone = 'success',
}: {
  message: string | null;
  tone?: 'success' | 'info' | 'error';
}) {
  const translateY = useRef(new Animated.Value(-24)).current;
  const opacity = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    if (!message) {
      opacity.setValue(0);
      translateY.setValue(-24);
      return;
    }
    Animated.parallel([
      Animated.spring(translateY, { toValue: 0, useNativeDriver: true, speed: 24 }),
      Animated.timing(opacity, { toValue: 1, duration: 200, useNativeDriver: true }),
    ]).start();
  }, [message, opacity, translateY]);

  if (!message) return null;
  const palette =
    tone === 'error'
      ? { bg: '#991B1B', border: '#DC2626' }
      : tone === 'info'
        ? { bg: '#075985', border: '#0284C7' }
        : { bg: '#065F46', border: '#10B981' };

  return (
    <View
      pointerEvents="none"
      style={{
        position: 'absolute',
        top: 12,
        left: 16,
        right: 16,
        zIndex: 60,
        alignItems: 'center',
      }}
    >
      <Animated.View
        style={{
          opacity,
          transform: [{ translateY }],
          backgroundColor: palette.bg,
          borderColor: palette.border,
          borderWidth: 1,
          borderRadius: 999,
          paddingHorizontal: 18,
          paddingVertical: 10,
          maxWidth: 460,
          ...FloatingShadow,
        }}
      >
        <Text style={{ color: '#FFFFFF', fontWeight: '700', fontSize: 13.5, textAlign: 'center' }}>
          {message}
        </Text>
      </Animated.View>
    </View>
  );
}

export function AnimatedProgressBar({
  progress,
  height = 10,
  trackColor = 'rgba(255,255,255,0.22)',
  fillColor = '#34D399',
}: {
  progress: number;
  height?: number;
  trackColor?: string;
  fillColor?: string;
}) {
  const anim = useRef(new Animated.Value(0)).current;
  const clamped = Math.max(0, Math.min(1, progress));

  useEffect(() => {
    Animated.timing(anim, {
      toValue: clamped,
      duration: 500,
      useNativeDriver: false,
    }).start();
  }, [anim, clamped]);

  const widthInterpolated = anim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0%', '100%'],
  });

  return (
    <View style={[styles.progressTrack, { height, backgroundColor: trackColor }]}>
      <Animated.View style={[styles.progressFill, { width: widthInterpolated, height, backgroundColor: fillColor }]} />
    </View>
  );
}

export function Card({
  children,
  style,
  accentColor,
  className = '',
}: {
  children: React.ReactNode;
  style?: ViewStyle;
  accentColor?: string;
  className?: string;
}) {
  return (
    <View
      className={`bg-white rounded-[24px] p-5 border border-slate-200/80 mb-4 ${className}`}
      style={[
        CardShadow,
        accentColor ? { borderLeftWidth: 5, borderLeftColor: accentColor } : undefined,
        style,
      ]}
    >
      {children}
    </View>
  );
}

export function FormIconBadge({ form }: { form: string }) {
  const bgMap: Record<string, string> = {
    tablet: '#E6F4F1',
    capsule: '#DCFCE7',
    syrup: '#E0F2FE',
    inhaler: '#EDE9FE',
    drops: '#E0F2FE',
    injection: '#FEF3C7',
    other: '#F1F5F9',
  };
  const fgMap: Record<string, string> = {
    tablet: '#0D6E6E',
    capsule: '#059669',
    syrup: '#0284C7',
    inhaler: '#6D28D9',
    drops: '#0369A1',
    injection: '#B45309',
    other: '#475569',
  };

  return (
    <View
      className="w-12 h-12 rounded-2xl items-center justify-center mr-3"
      style={{ backgroundColor: bgMap[form] || '#E6F4F1' }}
    >
      {form === 'injection' || form === 'other' ? (
        <ShieldIcon size={22} color={fgMap[form] || Colors.primary} />
      ) : (
        <PillIcon size={22} color={fgMap[form] || Colors.primary} />
      )}
    </View>
  );
}

export function LabeledInput({
  label,
  ...props
}: TextInputProps & { label: string }) {
  const [focused, setFocused] = useState(false);

  return (
    <View className="mb-3.5">
      <Text className="text-[14px] font-semibold text-ink mb-1.5 tracking-tight">{label}</Text>
      <TextInput
        placeholderTextColor={Colors.textMuted}
        onFocus={(e) => {
          setFocused(true);
          props.onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          props.onBlur?.(e);
        }}
        className={`min-h-[50px] rounded-2xl px-4 text-[16px] text-ink bg-slate-50 border ${
          focused ? 'border-brand bg-white' : 'border-slate-200'
        }`}
        {...props}
      />
    </View>
  );
}

export function StatusBadge({ status }: { status: DoseStatus }) {
  const map: Record<DoseStatus, { label: string; bg: string; fg: string; dot: string }> = {
    pending: { label: 'Pending', bg: '#E0F2FE', fg: '#0369A1', dot: '#0284C7' },
    snoozed: { label: 'Snoozed', bg: '#FEF3C7', fg: '#B45309', dot: '#D97706' },
    taken_on_time: { label: 'Taken On Time', bg: '#DCFCE7', fg: '#15803D', dot: '#10B981' },
    taken_late: { label: 'Taken Late', bg: '#FEF3C7', fg: '#B45309', dot: '#D97706' },
    partially_taken: { label: 'Partially Taken', bg: '#FEF3C7', fg: '#B45309', dot: '#D97706' },
    explicitly_skipped: { label: 'Skipped', bg: '#E2E8F0', fg: '#475569', dot: '#64748B' },
    expired_unconfirmed: { label: 'Unconfirmed', bg: '#FEE2E2', fg: '#B91C1C', dot: '#DC2626' },
  };
  const cfg = map[status] || map.pending;
  return (
    <View
      className="self-start flex-row items-center px-3 py-1.5 rounded-full"
      style={{ backgroundColor: cfg.bg }}
    >
      <View className="w-2 h-2 rounded-full mr-1.5" style={{ backgroundColor: cfg.dot }} />
      <Text className="text-[12.5px] font-bold" style={{ color: cfg.fg }}>
        {cfg.label}
      </Text>
    </View>
  );
}

export function EmptyState({
  title,
  subtitle,
  actionLabel,
  onAction,
}: {
  title: string;
  subtitle: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <Card className="items-center py-8 px-6">
      <View className="w-14 h-14 rounded-2xl bg-brand-soft items-center justify-center mb-3">
        <BellIcon size={26} color={Colors.primary} />
      </View>
      <Text className="text-[19px] font-bold text-ink text-center mb-1.5">{title}</Text>
      <Text className="text-[15px] text-ink-muted text-center leading-6 max-w-md">{subtitle}</Text>
      {actionLabel && onAction && (
        <PrimaryButton title={actionLabel} onPress={onAction} className="mt-4" />
      )}
    </Card>
  );
}

const styles = StyleSheet.create({
  progressTrack: {
    width: '100%',
    borderRadius: 99,
    overflow: 'hidden',
  },
  progressFill: {
    borderRadius: 99,
  },
});
