import type { en } from "./en";

type WidenStrings<T> = {
  [K in keyof T]: T[K] extends (...args: infer A) => unknown
    ? (...args: A) => string
    : T[K] extends Record<string, unknown>
      ? WidenStrings<T[K]>
      : string;
};

export type Strings = WidenStrings<typeof en>;
