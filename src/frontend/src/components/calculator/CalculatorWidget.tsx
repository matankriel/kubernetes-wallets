import { useEffect, useState } from "react";
import { convertCpu } from "../../api/calculator";
import type { ConversionResult } from "../../api/calculator";

const TIERS = ["regular", "high_performance"] as const;

function useDebounce<T>(value: T, ms: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setDebounced(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return debounced;
}

export default function CalculatorWidget() {
  const [cpuCount, setCpuCount] = useState(8);
  const [fromTier, setFromTier] = useState<string>("high_performance");
  const [toTier, setToTier] = useState<string>("regular");
  const [result, setResult] = useState<ConversionResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const debouncedCount = useDebounce(cpuCount, 300);

  useEffect(() => {
    if (fromTier === toTier || debouncedCount <= 0) {
      setResult(null);
      return;
    }
    convertCpu({ cpu_count: debouncedCount, from_tier: fromTier, to_tier: toTier })
      .then((r) => { setResult(r); setError(null); })
      .catch((e: Error) => setError(e.message));
  }, [debouncedCount, fromTier, toTier]);

  return (
    <div style={{ padding: 16, border: "1px solid #eee", maxWidth: 320 }}>
      <h3>CPU Tier Calculator</h3>
      <label>
        CPU count
        <input
          type="number"
          min={1}
          value={cpuCount}
          onChange={(e) => setCpuCount(Number(e.target.value))}
        />
      </label>
      <label>
        From tier
        <select value={fromTier} onChange={(e) => setFromTier(e.target.value)}>
          {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </label>
      <label>
        To tier
        <select value={toTier} onChange={(e) => setToTier(e.target.value)}>
          {TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
      </label>
      {error && <p role="alert" style={{ color: "red" }}>{error}</p>}
      {result && (
        <p>
          {result.input_cpu} {result.from_tier} = <strong>{result.output_cpu}</strong> {result.to_tier}
        </p>
      )}
    </div>
  );
}
