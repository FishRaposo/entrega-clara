import type { Metadata } from "next";
import { OperationsPanel } from "../../components/operations-panel";
import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export const metadata: Metadata = { title: "Operações" };

export default function AdminPage() {
  return (
    <PlatformShell market={brazilMarket}>
      <OperationsPanel />
    </PlatformShell>
  );
}
