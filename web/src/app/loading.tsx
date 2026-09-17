export default function Loading() {
  return (
    <div className="min-h-[60vh] flex flex-col items-center justify-center p-6 text-center animate-fade-in">
      <div className="relative mb-4">
        {/* Warm amber compass / math ring */}
        <div className="w-12 h-12 rounded-full border-2 border-amber-200 border-t-amber-600 animate-spin" />
        <div className="absolute inset-0 flex items-center justify-center text-amber-700 font-serif text-sm font-semibold select-none">
          ∫
        </div>
      </div>
      <p className="text-sm font-medium text-slate-700 tracking-wide">
        កំពុងផ្ទុក...
      </p>
      <p className="text-xs text-slate-400 mt-1">
        BAC II Math
      </p>
    </div>
  );
}
