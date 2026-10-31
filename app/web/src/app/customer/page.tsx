import { CustomerFlow } from "../../components/customer-flow";
import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export default function CustomerPage() {
  return (
    <PlatformShell market={brazilMarket}>
      <CustomerFlow />
    </PlatformShell>
  );
}
