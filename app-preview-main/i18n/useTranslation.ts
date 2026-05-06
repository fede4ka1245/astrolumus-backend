import { useMemo, useEffect, useState } from 'react';
import * as enFallback from './locales/en.json';
import * as ruFallback from './locales/ru.json';
import * as ukFallback from './locales/uk.json';
import * as plFallback from './locales/pl.json';
import * as beFallback from './locales/be.json';

type Language = 'en' | 'ru' | 'uk' | 'pl' | 'be';

const S3_TRANSLATIONS_BASE = process.env.NEXT_PUBLIC_TRANSLATIONS_URL
  || 'https://media.alpha-astro.com/alpha/translations/app-preview';

// Bundled fallback translations
const fallbackTranslations: Record<string, any> = {
  en: enFallback,
  ru: ruFallback,
  uk: ukFallback,
  pl: plFallback,
  be: beFallback,
};

// Cache for S3-loaded translations
const s3Cache: Record<string, any> = {};

async function fetchTranslations(lang: string): Promise<any> {
  if (s3Cache[lang]) return s3Cache[lang];

  try {
    const res = await fetch(`${S3_TRANSLATIONS_BASE}/${lang}.json`);
    if (res.ok) {
      const data = await res.json();
      s3Cache[lang] = data;
      return data;
    }
  } catch {
    // S3 unavailable, use fallback
  }
  return fallbackTranslations[lang] || fallbackTranslations.en;
}

const translations: Record<string, any> = { ...fallbackTranslations };

/**
 * Hook for accessing translations
 * @param language - Current language code
 * @returns Object with `t` function for accessing translations
 */
export function useTranslation(language: Language) {
  const [currentTranslations, setCurrentTranslations] = useState<any>(
    translations[language] || translations.en
  );

  useEffect(() => {
    fetchTranslations(language).then((data) => {
      translations[language] = data;
      setCurrentTranslations(data);
    });
  }, [language]);

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


