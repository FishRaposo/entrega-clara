import type { Metadata } from "next";
import { CustomerFlow } from "../../components/customer-flow";
import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export const metadata: Metadata = { title: "Cliente" };

export default function CustomerPage() {
  return (
    <PlatformShell market={brazilMarket}>
      <CustomerFlow />
    </PlatformShell>
  );
}
