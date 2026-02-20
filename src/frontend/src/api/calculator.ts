import { apiFetch } from "./client";

export interface ConversionResult {
  input_cpu: number;
  output_cpu: number;
  from_tier: string;
  to_tier: string;
  ratio_used: number;
}

export async function convertCpu(body: {
  cpu_count: number;
  from_tier: string;
  to_tier: string;
}): Promise<ConversionResult> {
  return apiFetch<ConversionResult>("/api/v1/calculator/convert", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
