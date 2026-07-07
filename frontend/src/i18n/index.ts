import { en } from "./en";
import { is } from "./is";
import type { Strings } from "./types";

export type { Strings } from "./types";
export type Locale = "is" | "en";

const catalogs: Record<Locale, Strings> = { is, en };

export const DEFAULT_LOCALE: Locale = "is";

export function getStrings(locale: Locale): Strings {
  return catalogs[locale];
}

export function localeTag(locale: Locale): string {
  return locale === "is" ? "is-IS" : "en-GB";
}
