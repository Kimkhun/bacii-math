"use client";

import { createContext, useContext, useEffect, useState, useCallback, ReactNode } from "react";
import { Language, Translations, TRANSLATIONS } from "@/lib/i18n";

interface LanguageContextValue {
  lang: Language;
  setLang: (lang: Language) => void;
  toggleLang: () => void;
  t: (key: keyof Translations) => string;
}

const LanguageContext = createContext<LanguageContextValue | null>(null);

const STORAGE_KEY = "bacii_lang";

function persist(lang: Language) {
  try {
    localStorage.setItem(STORAGE_KEY, lang);
    document.documentElement.lang = lang;
  } catch {
    // Private mode / blocked storage: the choice just won't outlive the tab.
  }
}

export function LanguageProvider({ children }: { children: ReactNode }) {
  // Starts at the server-rendered default and resolves on mount; the inline
  // script in the root layout has already set <html lang> by this point, so
  // only the rendered strings swap. See the comment there.
  const [lang, setLangState] = useState<Language>("en");

  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === "en" || stored === "km") {
        setLangState(stored);
        document.documentElement.lang = stored;
      }
    } catch {
      // Ignore localStorage errors
    }
  }, []);

  const setLang = useCallback((newLang: Language) => {
    setLangState(newLang);
    persist(newLang);
  }, []);

  const toggleLang = useCallback(() => {
    setLangState((prev) => {
      const next = prev === "en" ? "km" : "en";
      persist(next);
      return next;
    });
  }, []);

  const t = useCallback(
    (key: keyof Translations): string => {
      return TRANSLATIONS[lang]?.[key] ?? TRANSLATIONS.en[key] ?? key;
    },
    [lang]
  );

  return (
    <LanguageContext.Provider value={{ lang, setLang, toggleLang, t }}>
      {children}
    </LanguageContext.Provider>
  );
}

export function useLanguage(): LanguageContextValue {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    // Fallback if rendered outside provider
    return {
      lang: "en",
      setLang: () => {},
      toggleLang: () => {},
      t: (key: keyof Translations) => TRANSLATIONS.en[key] ?? key,
    };
  }
  return ctx;
}
