import { AlgorithmLab } from "../../components/algorithm-lab";
import { PlatformShell } from "../../components/platform-shell";
import { brazilMarket } from "../../lib/market-config";

export default function LabPage() {
  return (
    <PlatformShell market={brazilMarket}>
      <AlgorithmLab />
    </PlatformShell>
  );
}
