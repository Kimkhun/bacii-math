"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/context/AuthContext";

export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) router.replace("/login");
    else if (!user.is_admin) router.replace("/practice");
  }, [loading, user, router]);

  if (loading) {
    return <div className="p-10 text-center text-slate-500">Loading...</div>;
  }
  if (!user || !user.is_admin) return null;

  return <>{children}</>;
}
