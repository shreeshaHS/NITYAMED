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
import { CardShadow, Colors, Spacing } from '../theme';
import type { DoseStatus } from '../types/api';
import { BellIcon, PillIcon, ShieldIcon } from './Icons';

interface ButtonProps {
  title: string;
  onPress: () => void;
  variant?: 'primary' | 'emerald' | 'secondary' | 'danger' | 'outline';
  loading?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
  className?: string;
}

export function PrimaryButton({
  title,
  onPress,
  variant = 'primary',
  loading = false,
  disabled = false,
  style,
  className = '',
}: ButtonProps) {
  const scale = useRef(new Animated.Value(1)).current;

  const variantClasses: Record<NonNullable<ButtonProps['variant']>, string> = {
    primary: 'bg-brand border border-brand',
    emerald: 'bg-brand-mint border border-brand-mint',
    secondary: 'bg-brand-soft border border-brand/15',
    danger: 'bg-red-700 border border-red-700',
    outline: 'bg-white border-2 border-brand',
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
      speed: 38,
      bounciness: 5,
    }).start();
  };

  return (
    <Animated.View style={[{ transform: [{ scale }] }, style]}>
      <Pressable
        disabled={disabled || loading}
        onPress={onPress}
        onPressIn={() => animateTo(0.97)}
        onPressOut={() => animateTo(1)}
        className={`min-h-[50px] px-5 py-3 rounded-2xl items-center justify-center flex-row ${variantClasses[variant]} ${disabled ? 'opacity-50' : ''} ${className}`}
      >
        {loading ? (
          <ActivityIndicator color={spinnerColor} />
        ) : (
          <Text className={`text-[16px] font-bold text-center tracking-tight ${textClasses[variant]}`}>
            {title}
          </Text>
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
  const translateY = useRef(new Animated.Value(8)).current;

  useEffect(() => {
    Animated.timing(translateY, {
      toValue: 0,
      duration: 240,
      delay,
      useNativeDriver: false,
    }).start();
  }, [delay, translateY]);

  return (
    <Animated.View className={className} style={[{ transform: [{ translateY }] }, style]}>
      {children}
    </Animated.View>
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
      className={`bg-white rounded-3xl p-5 border border-slate-200/90 mb-4 ${className}`}
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
