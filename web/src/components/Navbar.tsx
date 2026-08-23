"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function Navbar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  return (
    <nav className="bg-white border-b border-slate-200">
      <div className="max-w-5xl mx-auto px-4 py-3 flex items-center gap-6">
        <Link href="/" className="font-bold text-lg text-slate-900">
          BACII Math
        </Link>
        {user && (
          <div className="flex items-center gap-4 text-sm">
            <Link href="/practice" className="text-slate-600 hover:text-slate-900">Practice</Link>
            <Link href="/history" className="text-slate-600 hover:text-slate-900">History</Link>
            <Link href="/stats" className="text-slate-600 hover:text-slate-900">Stats</Link>
            <Link href="/admin" className="text-slate-600 hover:text-slate-900">Admin</Link>
          </div>
        )}
        <div className="ml-auto flex items-center gap-3 text-sm">
          {user ? (
            <>
              <span className="text-slate-500">{user.email}</span>
              <button
                onClick={() => {
                  logout();
                  router.push("/");
                }}
                className="px-3 py-1.5 rounded bg-slate-100 text-slate-700 hover:bg-slate-200"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link href="/login" className="px-3 py-1.5 rounded text-slate-700 hover:bg-slate-100">Log in</Link>
              <Link href="/signup" className="px-3 py-1.5 rounded bg-slate-900 text-white hover:bg-slate-700">
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  );
}
