"use client";

import Link from "next/link";
import { useLanguage } from "@/context/LanguageContext";

export default function LandingPage() {
  const { t } = useLanguage();

  return (
    <div className="max-w-4xl mx-auto px-4 py-20 text-center">
      <h1 className="text-4xl font-extrabold text-slate-900 sm:text-5xl">
        {t("hero_title")}
      </h1>
      <p className="mt-4 text-lg text-slate-600 max-w-2xl mx-auto leading-relaxed">
        {t("hero_subtitle")}
      </p>
      <div className="mt-8 flex items-center justify-center gap-4">
        <Link
          href="/practice"
          className="px-5 py-2.5 rounded-lg bg-slate-900 text-white font-medium hover:bg-slate-700"
        >
          {t("btn_start_practicing")}
        </Link>
        <Link
          href="/signup"
          className="px-5 py-2.5 rounded-lg border border-slate-300 text-slate-700 font-medium hover:bg-slate-50"
        >
          {t("btn_create_account")}
        </Link>
      </div>
      <div className="mt-16 grid gap-6 sm:grid-cols-3">
        <div className="bg-white border border-slate-200 rounded-lg p-6 text-left">
          <h3 className="font-semibold text-slate-900">{t("feat_handwrite_title")}</h3>
          <p className="mt-2 text-sm text-slate-600">
            {t("feat_handwrite_desc")}
          </p>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-6 text-left">
          <h3 className="font-semibold text-slate-900">{t("feat_grading_title")}</h3>
          <p className="mt-2 text-sm text-slate-600">
            {t("feat_grading_desc")}
          </p>
        </div>
        <div className="bg-white border border-slate-200 rounded-lg p-6 text-left">
          <h3 className="font-semibold text-slate-900">{t("feat_step_title")}</h3>
          <p className="mt-2 text-sm text-slate-600">
            {t("feat_step_desc")}
          </p>
        </div>
      </div>
    </div>
  );
}
