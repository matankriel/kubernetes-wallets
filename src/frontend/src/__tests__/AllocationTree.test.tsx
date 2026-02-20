import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import * as allocationsApi from "../api/allocations";
import AllocationTree from "../components/allocation/AllocationTree";

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

describe("AllocationTree", () => {
  it("renders loading state initially", () => {
    vi.spyOn(allocationsApi, "getAllocationTree").mockReturnValue(new Promise(() => {}));
    render(<AllocationTree />, { wrapper });
    expect(screen.getByText(/loading/i)).toBeInTheDocument();
  });

  it("renders tree with correct center count", async () => {
    const mockData: allocationsApi.AllocationTreeResponse = {
      centers: [
        {
          center_id: "c-1",
          center_name: "Center Alpha",
          fields: [
            {
              field_id: "f-1",
              field_name: "Field One",
              site: "berlin",
              total_cpu: 100,
              total_ram_gb: 200,
              departments: [
                {
                  dept_id: "d-1",
                  dept_name: "Dept Engineering",
                  site: "berlin",
                  cpu_limit: 50,
                  ram_gb_limit: 100,
                  cpu_used: 10,
                  ram_gb_used: 20,
                  teams: [
                    {
                      team_id: "t-1",
                      team_name: "Team Platform",
                      site: "berlin",
                      cpu_limit: 20,
                      ram_gb_limit: 40,
                      cpu_used: 5,
                      ram_gb_used: 10,
                    },
                  ],
                },
              ],
            },
          ],
        },
        {
          center_id: "c-2",
          center_name: "Center Beta",
          fields: [],
        },
      ],
    };

    vi.spyOn(allocationsApi, "getAllocationTree").mockResolvedValue(mockData);
    render(<AllocationTree />, { wrapper });

    expect(await screen.findByText("Center Alpha")).toBeInTheDocument();
    expect(screen.getByText("Center Beta")).toBeInTheDocument();
    expect(screen.getByText("Field One")).toBeInTheDocument();
    expect(screen.getByText("Team Platform")).toBeInTheDocument();
  });

  it("renders empty message when no centers", async () => {
    vi.spyOn(allocationsApi, "getAllocationTree").mockResolvedValue({ centers: [] });
    render(<AllocationTree />, { wrapper });
    expect(await screen.findByText(/no allocation data/i)).toBeInTheDocument();
  });
});
