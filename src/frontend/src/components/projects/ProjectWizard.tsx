import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { createProject } from "../../api/projects";

const SLA_TYPES = ["bronze", "silver", "gold"] as const;
const PERF_TIERS = ["regular", "high_performance"] as const;

const QUOTA_MAP: Record<string, Record<string, { cpu: number; ram: number }>> = {
  bronze: { regular: { cpu: 2, ram: 4 }, high_performance: { cpu: 4, ram: 8 } },
  silver: { regular: { cpu: 4, ram: 16 }, high_performance: { cpu: 8, ram: 32 } },
  gold: { regular: { cpu: 8, ram: 32 }, high_performance: { cpu: 16, ram: 64 } },
};

interface Props {
  onClose: () => void;
}

export default function ProjectWizard({ onClose }: Props) {
  const qc = useQueryClient();
  const [step, setStep] = useState(1);
  const [site, setSite] = useState("");
  const [slaType, setSlaType] = useState<string>("bronze");
  const [tier, setTier] = useState<string>("regular");
  const [name, setName] = useState("");
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["projects"] });
      onClose();
    },
    onError: (err: Error) => setError(err.message),
  });

  const quota = QUOTA_MAP[slaType]?.[tier];

  const handleSubmit = () => {
    setError(null);
    mutation.mutate({ name, site, sla_type: slaType, performance_tier: tier });
  };

  return (
    <div style={{ border: "1px solid #ccc", padding: 24, maxWidth: 480 }}>
      <h2>New Project — Step {step}/3</h2>

      {step === 1 && (
        <>
          <label>
            Site
            <input value={site} onChange={(e) => setSite(e.target.value)} placeholder="e.g. berlin" />
          </label>
          <button onClick={() => setStep(2)} disabled={!site}>Next</button>
        </>
      )}

      {step === 2 && (
        <>
          <label>
            SLA type
            <select value={slaType} onChange={(e) => setSlaType(e.target.value)}>
              {SLA_TYPES.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </label>
          <label>
            Performance tier
            <select value={tier} onChange={(e) => setTier(e.target.value)}>
              {PERF_TIERS.map((t) => <option key={t} value={t}>{t}</option>)}
            </select>
          </label>
          {quota && (
            <p>Resource quota: {quota.cpu} CPU / {quota.ram} GB RAM</p>
          )}
          <button onClick={() => setStep(1)}>Back</button>
          <button onClick={() => setStep(3)}>Next</button>
        </>
      )}

      {step === 3 && (
        <>
          <label>
            Project name
            <input value={name} onChange={(e) => setName(e.target.value)} placeholder="my-project" />
          </label>
          <p>
            Summary: <strong>{name}</strong> at {site} — {slaType}/{tier} ({quota?.cpu} CPU / {quota?.ram} GB)
          </p>
          {error && <p role="alert" style={{ color: "red" }}>{error}</p>}
          <button onClick={() => setStep(2)}>Back</button>
          <button onClick={handleSubmit} disabled={!name || mutation.isPending}>
            {mutation.isPending ? "Creating…" : "Create"}
          </button>
        </>
      )}

      <button onClick={onClose} style={{ marginLeft: 8 }}>Cancel</button>
    </div>
  );
}
