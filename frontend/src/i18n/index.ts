import { applyPlatformBranding } from "../branding";
import { en } from "./en";
import { is } from "./is";
import type { Strings } from "./types";

export type { Strings } from "./types";

/** Register new locales here and add a matching catalog file. */
export const LOCALE_DEFINITIONS = {
  en: { label: "English", tag: "en-GB", strings: en },
  is: { label: "Íslenska", tag: "is-IS", strings: is },
} as const;

export type Locale = keyof typeof LOCALE_DEFINITIONS;

export const LOCALES = Object.keys(LOCALE_DEFINITIONS) as Locale[];

export const DEFAULT_LOCALE: Locale = "en";

export function isLocale(value: string): value is Locale {
  return value in LOCALE_DEFINITIONS;
}

export function getStrings(locale: Locale): Strings {
  return applyPlatformBranding(LOCALE_DEFINITIONS[locale].strings);
}

export function localeTag(locale: Locale): string {
  return LOCALE_DEFINITIONS[locale].tag;
}
