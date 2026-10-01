// Registry of interactive lesson explorers, keyed by the `explorer` id a
// lesson's animation block names (backend .../data/animations.json).
//
// Each explorer is its own lazily-loaded chunk (next/dynamic), so a lesson
// costs nothing extra until the student presses "Explore". All limit
// lessons share one generic component driven by a preset.
import dynamic from "next/dynamic";
import type { ComponentType } from "react";

import { LIMIT_PRESET_IDS } from "./limitPresetIds";

function Loading() {
  return <div className="h-72 animate-pulse rounded-xl bg-slate-100" aria-busy />;
}

const LimitExplorer = dynamic(() => import("./LimitExplorer"), { ssr: false, loading: Loading });

const cache = new Map<string, ComponentType>();

export function getExplorer(id: string): ComponentType | null {
  if (!LIMIT_PRESET_IDS.includes(id)) return null;
  let c = cache.get(id);
  if (!c) {
    const Bound = () => <LimitExplorer presetId={id} />;
    Bound.displayName = `LimitExplorer(${id})`;
    c = Bound;
    cache.set(id, c);
  }
  return c;
}
