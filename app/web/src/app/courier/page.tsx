import type { Metadata } from "next";
import { CourierConsole } from "../../components/courier-console";
import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export const metadata: Metadata = { title: "Entregador" };

export default function CourierPage() {
  return (
    <PlatformShell market={brazilMarket}>
      <CourierConsole />
    </PlatformShell>
  );
}
