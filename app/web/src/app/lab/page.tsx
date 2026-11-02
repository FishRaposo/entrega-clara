import type { Metadata } from "next";
import { AlgorithmLab } from "../../components/algorithm-lab";
import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export const metadata: Metadata = { title: "Laboratório" };

export default function LabPage() {
  return (
    <PlatformShell market={brazilMarket}>
      <AlgorithmLab />
    </PlatformShell>
  );
}
