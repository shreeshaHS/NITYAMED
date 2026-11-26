/** Elevated Auth Screen (Sign In, Create Account, 6-Digit Email Verification & Password Reset). */

import React, { useState } from 'react';
import {
  ScrollView,
  Text,
  TouchableOpacity,
  useWindowDimensions,
  View,
} from 'react-native';
import { Card, FadeSlideIn, LabeledInput, PrimaryButton } from '../components/AccessibleUI';
import { BrandMark } from '../components/BrandMark';
import { BellIcon, ClockIcon, ShieldIcon } from '../components/Icons';
import { t } from '../i18n/translations';
import { api, ApiError } from '../services/api';
import { tokenStore } from '../services/tokenStore';
import { Colors } from '../theme';
import type { SupportedLang } from '../types/api';

interface AuthScreenProps {
  lang: SupportedLang;
  onChangeLang: (lang: SupportedLang) => void;
  onAuthenticated: () => Promise<void>;
  onReplayIntro: () => void;
}

const LANG_OPTIONS: Array<{ code: SupportedLang; label: string }> = [
  { code: 'en', label: 'English' },
  { code: 'kn', label: 'ಕನ್ನಡ' },
  { code: 'hi', label: 'हिन्दी' },
];

export function AuthScreen({
  lang,
  onChangeLang,
  onAuthenticated,
  onReplayIntro,
}: AuthScreenProps) {
  const { width } = useWindowDimensions();
  const isWide = width >= 880;

  const [isRegister, setIsRegister] = useState(false);
  const [verifyMode, setVerifyMode] = useState(false);
  const [verifyFromRegister, setVerifyFromRegister] = useState(false);
  const [forgotMode, setForgotMode] = useState(false);
  const [resetRequested, setResetRequested] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [otpCode, setOtpCode] = useState('');
  const [devOtpHint, setDevOtpHint] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [infoMsg, setInfoMsg] = useState<string | null>(null);

  const handleSubmit = async () => {
    setErrorMsg(null);
    setInfoMsg(null);
    if (!email.trim() || !password) {
      setErrorMsg('Please enter email and password.');
      return;
    }
    if (isRegister && !displayName.trim()) {
      setErrorMsg('Please enter your name.');
      return;
    }

    setLoading(true);
    try {
      const tokens = isRegister
        ? await api.register({
            email: email.trim(),
            password,
            display_name: displayName.trim(),
            preferred_lang: lang,
          })
        : await api.login({ email: email.trim(), password });

      if (tokens.verification_required || !tokens.access_token || !tokens.refresh_token) {
        setVerifyFromRegister(isRegister);
        setVerifyMode(true);
        setDevOtpHint(tokens.dev_otp_preview || null);
        if (tokens.email_sent) {
          setInfoMsg('A 6-digit verification code has been sent to your email.');
        } else if (tokens.dev_otp_preview) {
          setInfoMsg('Enter the 6-digit dev verification code shown below.');
        } else {
          setErrorMsg('Unable to deliver verification email right now. Please try Resend.');
        }
        return;
      }

      await tokenStore.saveTokens(tokens.access_token, tokens.refresh_token);
      await onAuthenticated();
    } catch (err) {
      if (err instanceof ApiError && err.code === 'EMAIL_NOT_VERIFIED') {
        setVerifyFromRegister(true);
        setVerifyMode(true);
        try {
          const resent = await api.resendVerification(email.trim());
          setDevOtpHint(resent.dev_otp_preview || null);
          if (resent.email_sent) {
            setInfoMsg('Your new account verification was not finished yet. A fresh 6-digit code has been sent to your email.');
          } else if (resent.dev_otp_preview) {
            setInfoMsg('Account setup not finished yet. Enter the 6-digit dev code shown below.');
          } else {
            setErrorMsg('Account creation is pending verification, but email delivery failed. Please tap Resend.');
          }
        } catch (resendErr) {
          setErrorMsg(resendErr instanceof ApiError ? resendErr.message : err.message);
        }
      } else {
        setErrorMsg(err instanceof ApiError ? err.message : 'Unable to reach server. Check connection.');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    setErrorMsg(null);
    setInfoMsg(null);
    if (!/^\d{6}$/.test(otpCode.trim())) {
      setErrorMsg('Enter the 6-digit numeric verification code.');
      return;
    }
    setLoading(true);
    try {
      const tokens = await api.verifyEmail({
        email: email.trim(),
        otp_code: otpCode.trim(),
      });
      if (verifyFromRegister) {
        setVerifyMode(false);
        setVerifyFromRegister(false);
        setIsRegister(false);
        setOtpCode('');
        setPassword('');
        setDevOtpHint(null);
        setInfoMsg('Email verified and your account has been created! Please sign in.');
        return;
      }
      if (tokens.access_token && tokens.refresh_token) {
        await tokenStore.saveTokens(tokens.access_token, tokens.refresh_token);
        await onAuthenticated();
      }
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Verification failed.');
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    setErrorMsg(null);
    setInfoMsg(null);
    setLoading(true);
    try {
      const res = await api.resendVerification(email.trim());
      setDevOtpHint(res.dev_otp_preview || null);
      if (res.already_verified) {
        setInfoMsg('Your email is already verified. Please sign in.');
      } else if (res.email_sent) {
        setInfoMsg('A fresh verification code was sent to your email.');
      } else if (res.dev_otp_preview) {
        setInfoMsg('Enter the fresh dev verification code shown below.');
      } else {
        setErrorMsg('Unable to deliver verification email right now. Please check email settings.');
      }
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Unable to resend code.');
    } finally {
      setLoading(false);
    }
  };

  const handleRequestReset = async () => {
    setErrorMsg(null);
    setInfoMsg(null);
    if (!email.trim()) {
      setErrorMsg('Please enter your email address first.');
      return;
    }
    setLoading(true);
    try {
      const res = await api.forgotPassword(email.trim());
      if (!res.email_sent && !res.dev_otp_preview) {
        setErrorMsg('Unable to deliver reset email right now. Check server email settings and try again.');
        return;
      }
      setResetRequested(true);
      setDevOtpHint(res.dev_otp_preview || null);
      setInfoMsg(res.message);
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Unable to send reset code.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmReset = async () => {
    setErrorMsg(null);
    if (!/^\d{6}$/.test(otpCode.trim()) || newPassword.length < 8) {
      setErrorMsg('Enter the 6-digit code and a new password (min 8 characters).');
      return;
    }
    setLoading(true);
    try {
      await api.resetPassword({
        email: email.trim(),
        otp_code: otpCode.trim(),
        new_password: newPassword,
      });
      setForgotMode(false);
      setResetRequested(false);
      setOtpCode('');
      setNewPassword('');
      setDevOtpHint(null);
      setInfoMsg('Password reset successful! Please sign in with your new password.');
    } catch (err) {
      setErrorMsg(err instanceof ApiError ? err.message : 'Password reset failed.');
    } finally {
      setLoading(false);
    }
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
      <View className={`w-full max-w-5xl self-center ${isWide ? 'flex-row gap-8 items-stretch' : ''}`}>
        {/* Brand Showcase Column (Desktop Left / Mobile Top) */}
        <View
          className={
            isWide
              ? 'rounded-[32px] p-8 justify-between'
              : 'items-center mb-5'
          }
          style={
            isWide
              ? { flex: 1, minWidth: 0, backgroundColor: Colors.primaryDark }
              : undefined
          }
        >
          <View className={isWide ? '' : 'items-center'}>
            <View className="flex-row items-center mb-4">
              <BrandMark size={isWide ? 48 : 54} variant={isWide ? 'inverse' : 'default'} />
              <View className="ml-3">
                <Text
                  className={`text-[26px] font-extrabold tracking-tight ${
                    isWide ? 'text-white' : 'text-ink'
                  }`}
                >
                  {t(lang, 'appTitle')}
                </Text>
                <Text
                  className={`text-[13px] font-semibold ${
                    isWide ? 'text-emerald-300' : 'text-brand'
                  }`}
                >
                  Medication Continuity System
                </Text>
              </View>
            </View>

            {isWide && (
              <Text className="text-[16px] text-teal-50/90 leading-7 mt-3">
                Reliable daily dose schedules, accurate strip-and-tablet stock tracking, and
                privacy-safe reminders across Web and Android.
              </Text>
            )}
          </View>

          {isWide && (
            <View className="gap-4 mt-8">
              <View className="flex-row items-center bg-white/10 rounded-2xl p-4">
                <ClockIcon size={22} color="#34D399" />
                <View className="ml-3 flex-1">
                  <Text className="text-[15px] font-bold text-white">Consistent Daily Cadence</Text>
                  <Text className="text-[13px] text-teal-100/80">
                    Morning, afternoon, evening, and night schedule clarity
                  </Text>
                </View>
              </View>
              <View className="flex-row items-center bg-white/10 rounded-2xl p-4">
                <ShieldIcon size={22} color="#34D399" />
                <View className="ml-3 flex-1">
                  <Text className="text-[15px] font-bold text-white">Privacy-First Alerts</Text>
                  <Text className="text-[13px] text-teal-100/80">
                    Optional email & lockscreen alerts hide sensitive medicine names
                  </Text>
                </View>
              </View>
              <View className="flex-row items-center bg-white/10 rounded-2xl p-4">
                <BellIcon size={22} color="#34D399" />
                <View className="ml-3 flex-1">
                  <Text className="text-[15px] font-bold text-white">Proactive Refill Alerts</Text>
                  <Text className="text-[13px] text-teal-100/80">
                    Know exact days remaining before packs run empty
                  </Text>
                </View>
              </View>
            </View>
          )}
        </View>

        {/* Auth Form Card */}
        <View
          className={isWide ? 'justify-center' : 'w-full'}
          style={isWide ? { flex: 1, minWidth: 0 } : undefined}
        >
          {/* Language Pills */}
          <View className="flex-row justify-center gap-2 mb-4">
            {LANG_OPTIONS.map((opt) => (
              <TouchableOpacity
                key={opt.code}
                onPress={() => onChangeLang(opt.code)}
                className={`px-4 py-2 rounded-full border ${
                  lang === opt.code ? 'bg-brand border-brand' : 'bg-white border-slate-200'
                }`}
              >
                <Text
                  className={`text-[13.5px] font-bold ${
                    lang === opt.code ? 'text-white' : 'text-ink-muted'
                  }`}
                >
                  {opt.label}
                </Text>
              </TouchableOpacity>
            ))}
          </View>

          <FadeSlideIn delay={60}>
            <Card className="p-6">
              {verifyMode ? (
                <>
                  <Text className="text-[22px] font-extrabold text-ink mb-1">
                    {t(lang, 'verifyEmailTitle')}
                  </Text>
                  <Text className="text-[14.5px] text-ink-muted leading-6 mb-4">
                    {verifyFromRegister
                      ? `Your account will be created once you enter the 6-digit code sent to ${email.trim()}.`
                      : `Enter the 6-digit verification code sent to ${email.trim()}.`}
                  </Text>

                  {infoMsg && (
                    <View className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3.5 mb-3">
                      <Text className="text-[14px] font-semibold text-emerald-800">{infoMsg}</Text>
                    </View>
                  )}

                  {devOtpHint && (
                    <View className="bg-sky-50 border border-sky-200 rounded-2xl p-3.5 mb-3">
                      <Text className="text-[14px] font-bold text-sky-800 text-center">
                        Dev Verification Code: {devOtpHint}
                      </Text>
                    </View>
                  )}

                  {errorMsg && (
                    <View className="bg-red-50 border border-red-200 rounded-2xl p-3.5 mb-3">
                      <Text className="text-[14px] font-semibold text-red-700">{errorMsg}</Text>
                    </View>
                  )}

                  <LabeledInput
                    label="6-Digit Verification Code"
                    value={otpCode}
                    onChangeText={setOtpCode}
                    keyboardType="number-pad"
                    maxLength={6}
                    placeholder="123456"
                  />

                  <PrimaryButton
                    title={verifyFromRegister ? 'Verify & Create Account' : 'Verify & Continue'}
                    onPress={handleVerifyOtp}
                    loading={loading}
                    variant="emerald"
                    className="mt-1"
                  />

                  <TouchableOpacity onPress={handleResendOtp} className="mt-4 py-2 items-center">
                    <Text className="text-[15px] font-bold text-brand">{t(lang, 'resendOtp')}</Text>
                  </TouchableOpacity>

                  <TouchableOpacity
                    onPress={() => {
                      setVerifyMode(false);
                      setOtpCode('');
                      setErrorMsg(null);
                    }}
                    className="mt-1 py-2 items-center"
                  >
                    <Text className="text-[14px] font-semibold text-ink-soft">{t(lang, 'backToSignIn')}</Text>
                  </TouchableOpacity>
                </>
              ) : forgotMode ? (
                <>
                  <Text className="text-[22px] font-extrabold text-ink mb-1">{t(lang, 'resetPasswordTitle')}</Text>
                  <Text className="text-[14.5px] text-ink-muted leading-6 mb-4">
                    {resetRequested
                      ? `Enter the 6-digit code sent to ${email.trim()} and choose a new password.`
                      : 'Enter your registered email address to receive a 6-digit reset code.'}
                  </Text>

                  {infoMsg && (
                    <View className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3.5 mb-3">
                      <Text className="text-[14px] font-semibold text-emerald-800">{infoMsg}</Text>
                    </View>
                  )}

                  {devOtpHint && (
                    <View className="bg-sky-50 border border-sky-200 rounded-2xl p-3.5 mb-3">
                      <Text className="text-[14px] font-bold text-sky-800 text-center">
                        Dev Reset Code: {devOtpHint}
                      </Text>
                    </View>
                  )}

                  {errorMsg && (
                    <View className="bg-red-50 border border-red-200 rounded-2xl p-3.5 mb-3">
                      <Text className="text-[14px] font-semibold text-red-700">{errorMsg}</Text>
                    </View>
                  )}

                  <LabeledInput
                    label="Email Address"
                    value={email}
                    onChangeText={setEmail}
                    autoCapitalize="none"
                    keyboardType="email-address"
                    placeholder="you@example.com"
                  />

                  {resetRequested && (
                    <>
                      <LabeledInput
                        label="6-Digit Reset Code"
                        value={otpCode}
                        onChangeText={setOtpCode}
                        keyboardType="number-pad"
                        maxLength={6}
                        placeholder="123456"
                      />
                      <LabeledInput
                        label="New Password (min 8 characters)"
                        value={newPassword}
                        onChangeText={setNewPassword}
                        secureTextEntry
                        placeholder="Enter new password"
                      />
                    </>
                  )}

                  <PrimaryButton
                    title={resetRequested ? 'Update Password' : 'Send Reset Code'}
                    onPress={resetRequested ? handleConfirmReset : handleRequestReset}
                    loading={loading}
                    className="mt-1"
                  />

                  <TouchableOpacity
                    onPress={() => {
                      setForgotMode(false);
                      setResetRequested(false);
                      setOtpCode('');
                      setNewPassword('');
                      setDevOtpHint(null);
                      setErrorMsg(null);
                      setInfoMsg(null);
                    }}
                    className="mt-4 py-2 items-center"
                  >
                    <Text className="text-[14.5px] font-bold text-brand">{t(lang, 'backToSignIn')}</Text>
                  </TouchableOpacity>
                </>
              ) : (
                <>
                  {/* Mode Switcher Pills */}
                  <View className="flex-row bg-slate-100 p-1 rounded-2xl mb-5">
                    <TouchableOpacity
                      onPress={() => {
                        setIsRegister(false);
                        setErrorMsg(null);
                      }}
                      className={`flex-1 py-2.5 rounded-xl items-center ${
                        !isRegister ? 'bg-white shadow-sm' : ''
                      }`}
                    >
                      <Text
                        className={`text-[15px] font-bold ${
                          !isRegister ? 'text-brand-dark' : 'text-ink-muted'
                        }`}
                      >
                        {t(lang, 'signIn')}
                      </Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                      onPress={() => {
                        setIsRegister(true);
                        setErrorMsg(null);
                      }}
                      className={`flex-1 py-2.5 rounded-xl items-center ${
                        isRegister ? 'bg-white shadow-sm' : ''
                      }`}
                    >
                      <Text
                        className={`text-[15px] font-bold ${
                          isRegister ? 'text-brand-dark' : 'text-ink-muted'
                        }`}
                      >
                        {t(lang, 'createAccount')}
                      </Text>
                    </TouchableOpacity>
                  </View>

                  {infoMsg && (
                    <View className="bg-emerald-50 border border-emerald-200 rounded-2xl p-3.5 mb-3">
                      <Text className="text-[14px] font-semibold text-emerald-800">{infoMsg}</Text>
                    </View>
                  )}

                  {errorMsg && (
                    <View className="bg-red-50 border border-red-200 rounded-2xl p-3.5 mb-3">
                      <Text className="text-[14px] font-semibold text-red-700">{errorMsg}</Text>
                    </View>
                  )}

                  {isRegister && (
                    <LabeledInput
                      label={t(lang, 'fullName')}
                      value={displayName}
                      onChangeText={setDisplayName}
                      placeholder="e.g. Ramesh Kulkarni"
                    />
                  )}

                  <LabeledInput
                    label={t(lang, 'email')}
                    value={email}
                    onChangeText={setEmail}
                    autoCapitalize="none"
                    keyboardType="email-address"
                    placeholder="you@example.com"
                  />

                  <LabeledInput
                    label={t(lang, 'password')}
                    value={password}
                    onChangeText={setPassword}
                    secureTextEntry
                    placeholder="Minimum 8 characters"
                  />

                  {!isRegister && (
                    <TouchableOpacity
                      onPress={() => {
                        setForgotMode(true);
                        setErrorMsg(null);
                        setInfoMsg(null);
                      }}
                      className="self-end mb-4 -mt-1 py-1"
                    >
                      <Text className="text-[14px] font-bold text-brand">{t(lang, 'forgotPassword')}</Text>
                    </TouchableOpacity>
                  )}

                  <PrimaryButton
                    title={isRegister ? t(lang, 'createAccount') : t(lang, 'signIn')}
                    onPress={handleSubmit}
                    loading={loading}
                    variant={isRegister ? 'emerald' : 'primary'}
                  />
                </>
              )}
            </Card>
          </FadeSlideIn>

          <TouchableOpacity onPress={onReplayIntro} className="mt-2 py-2 items-center">
            <Text className="text-[14px] font-semibold text-ink-soft">{t(lang, 'viewIntroGuide')}</Text>
          </TouchableOpacity>
        </View>
      </View>
    </ScrollView>
  );
}
