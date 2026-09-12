"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { useLanguage } from "@/context/LanguageContext";

export default function SignupPage() {
  const { lang, t } = useLanguage();
  const { signup } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setBusy(true);
    try {
      await signup(email, password);
      router.push("/practice");
    } catch (err) {
      setError(err instanceof Error ? err.message : (lang === "km" ? "ការចុះឈ្មោះមិនបានជោគជ័យ" : "Signup failed"));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="max-w-sm mx-auto px-4 py-16">
      <h1 className="text-2xl font-bold text-center text-slate-900">{t("btn_create_account")}</h1>
      <form onSubmit={submit} className="mt-6 bg-white border border-slate-200 rounded-lg p-6 space-y-4 shadow-sm">
        <div>
          <label className="block text-sm font-medium text-slate-700">{lang === "km" ? "អ៊ីមែល" : "Email"}</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-md"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-slate-700">{lang === "km" ? "ពាក្យសម្ងាត់" : "Password"}</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={6}
            className="mt-1 w-full px-3 py-2 border border-slate-300 rounded-md"
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
        <button
          type="submit"
          disabled={busy}
          className="w-full px-4 py-2 rounded-md bg-slate-900 text-white font-medium hover:bg-slate-700 disabled:opacity-50"
        >
          {busy ? (lang === "km" ? "កំពុងបង្កើត..." : "Creating...") : t("nav_signup")}
        </button>
        <p className="text-sm text-slate-500 text-center">
          {lang === "km" ? "មានគណនីរួចហើយ? " : "Have an account? "}
          <Link href="/login" className="text-slate-900 underline">
            {t("nav_login")}
          </Link>
        </p>
      </form>
    </div>
  );
}
