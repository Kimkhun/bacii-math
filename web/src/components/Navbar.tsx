"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";
import { useLanguage } from "@/context/LanguageContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const { lang, setLang, t } = useLanguage();
  const router = useRouter();

  return (
    <nav className="sticky top-0 z-[100] bg-white border-b border-slate-200 h-14">
      <div className="max-w-5xl mx-auto px-4 h-full flex items-center gap-6">
        <Link href="/" className="font-bold text-lg text-slate-900 shrink-0">
          BACII Math
        </Link>
        {user && (
          <div className="flex items-center gap-4 text-sm overflow-x-auto">
            <Link href="/profile" className="text-slate-600 hover:text-slate-900 whitespace-nowrap">{t("nav_profile")}</Link>
            <Link href="/practice" className="text-slate-600 hover:text-slate-900 whitespace-nowrap">{t("nav_practice")}</Link>
            <Link href="/exam" className="text-slate-600 hover:text-slate-900 whitespace-nowrap">{t("nav_exam")}</Link>
            <Link href="/history" className="text-slate-600 hover:text-slate-900 whitespace-nowrap">{t("nav_history")}</Link>
            <Link href="/stats" className="text-slate-600 hover:text-slate-900 whitespace-nowrap">{t("nav_stats")}</Link>
            <Link href="/formulas" className="text-slate-600 hover:text-slate-900 whitespace-nowrap">{t("nav_formulas")}</Link>
            {user.is_admin && (
              <Link href="/admin" className="text-slate-600 hover:text-slate-900 whitespace-nowrap">{t("nav_admin")}</Link>
            )}
          </div>
        )}
        <div className="ml-auto flex items-center gap-3 text-sm shrink-0">
          {/* Language mode switcher */}
          <div className="flex items-center rounded-lg border border-slate-200 bg-slate-100/80 p-0.5 text-xs">
            <button
              onClick={() => setLang("km")}
              className={`px-2 py-1 rounded font-medium transition-all ${
                lang === "km"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-800"
              }`}
              title="ប្តូរទៅភាសាខ្មែរ (Khmer mode)"
            >
              🇰🇭 ខ្មែរ
            </button>
            <button
              onClick={() => setLang("en")}
              className={`px-2 py-1 rounded font-medium transition-all ${
                lang === "en"
                  ? "bg-white text-slate-900 shadow-sm"
                  : "text-slate-500 hover:text-slate-800"
              }`}
              title="Switch to English mode"
            >
              🇬🇧 EN
            </button>
          </div>

          {user ? (
            <>
              <span className="text-slate-500 hidden sm:inline">{user.email}</span>
              <button
                onClick={() => {
                  logout();
                  router.push("/");
                }}
                className="px-3 py-1.5 rounded bg-slate-100 text-slate-700 hover:bg-slate-200"
              >
                {t("nav_logout")}
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="px-3 py-1.5 rounded text-slate-700 hover:bg-slate-100">{t("nav_login")}</Link>
              <Link href="/signup" className="px-3 py-1.5 rounded bg-slate-900 text-white hover:bg-slate-700">
                {t("nav_signup")}
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
