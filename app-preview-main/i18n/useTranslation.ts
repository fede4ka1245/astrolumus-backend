import { useMemo } from 'react';
import * as en from './locales/en.json';
import * as ru from './locales/ru.json';
import * as uk from './locales/uk.json';
import * as pl from './locales/pl.json';
import * as be from './locales/be.json';

type Language = 'en' | 'ru' | 'uk' | 'pl' | 'be';

const translations = {
  en: en as any,
  ru: ru as any,
  uk: uk as any,
  pl: pl as any,
  be: be as any,
};

/**
 * Hook for accessing translations
 * @param language - Current language code
 * @returns Object with `t` function for accessing translations
 */
export function useTranslation(language: Language) {
  const currentTranslations = translations[language] || translations.en;

  return useMemo(
    () => ({
      t: (key: string, vars?: Record<string, string | number>) => {
        // Navigate nested keys like "payment.title"
        let value: any = currentTranslations;
        const keys = key.split('.');

        for (const k of keys) {
          if (value && typeof value === 'object') {
            value = value[k];
          } else {
            return key; // Return key if not found
          }
        }

        // Replace variables like {{days}}
        if (typeof value === 'string' && vars) {
          return value.replace(/\{\{(\w+)\}\}/g, (match, varName) => {
            return String(vars[varName] ?? match);
          });
        }

        return value || key;
      },
    }),
    [currentTranslations]
  );
}

/**
 * Static function for accessing translations outside of React components
 * @param language - Language code
 * @param key - Translation key (e.g., "payment.title")
 * @param vars - Optional variables for interpolation
 * @returns Translated string
 */
export function getTranslation(
  language: Language,
  key: string,
  vars?: Record<string, string | number>
): string {
  const currentTranslations = translations[language] || translations.en;
  let value: any = currentTranslations;
  const keys = key.split('.');

  for (const k of keys) {
    if (value && typeof value === 'object') {
      value = value[k];
    } else {
      return key;
    }
  }

  if (typeof value === 'string' && vars) {
    return value.replace(/\{\{(\w+)\}\}/g, (match, varName) => {
      return String(vars[varName] ?? match);
    });
  }

  return value || key;
}


