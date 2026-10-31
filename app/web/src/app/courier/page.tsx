import { CourierConsole } from "../../components/courier-console";
import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export default function CourierPage() {
  return (
    <PlatformShell market={brazilMarket}>
      <CourierConsole />
    </PlatformShell>
  );
}
