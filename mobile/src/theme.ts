/** Refined Healthcare Palette, Typography & Elevation Tokens for NityaMed (Tailwind-aligned). */

export const Colors = {
  primary: '#0D6E6E',
  primaryDark: '#094D4D',
  primaryDeep: '#063737',
  primaryLight: '#E6F4F1',
  emerald: '#10B981',
  emeraldDark: '#059669',
  accent: '#0284C7',
  background: '#F3F6FA',
  surface: '#FFFFFF',
  surfaceSubtle: '#F8FAFC',
  border: '#E2E8F0',
  text: '#0F172A',
  textSecondary: '#475569',
  textMuted: '#64748B',
  success: '#15803D',
  successBg: '#DCFCE7',
  warning: '#B45309',
  warningBg: '#FEF3C7',
  danger: '#B91C1C',
  dangerBg: '#FEE2E2',
  infoBg: '#E0F2FE',
  infoText: '#0369A1',
  morningBg: '#FEF3C7',
  morningText: '#B45309',
  afternoonBg: '#E0F2FE',
  afternoonText: '#0369A1',
  eveningBg: '#EDE9FE',
  eveningText: '#6D28D9',
  nightBg: '#E2E8F0',
  nightText: '#334155',
};

export const Typography = {
  hero: { fontSize: 28, fontWeight: '800' as const, color: Colors.text, letterSpacing: -0.4 },
  title: { fontSize: 20, fontWeight: '700' as const, color: Colors.text, letterSpacing: -0.2 },
  subtitle: { fontSize: 17, fontWeight: '600' as const, color: Colors.text },
  body: { fontSize: 16, fontWeight: '400' as const, color: Colors.text, lineHeight: 24 },
  caption: { fontSize: 14, fontWeight: '500' as const, color: Colors.textSecondary },
  button: { fontSize: 16, fontWeight: '700' as const },
};

export const Spacing = {
  xs: 6,
  sm: 10,
  md: 16,
  lg: 24,
  minTouchHeight: 50,
};

export const CardShadow = {
  shadowColor: '#0F172A',
  shadowOffset: { width: 0, height: 6 },
  shadowOpacity: 0.05,
  shadowRadius: 16,
  elevation: 2,
};
