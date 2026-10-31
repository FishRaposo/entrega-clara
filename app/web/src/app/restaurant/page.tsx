import { PlatformShell } from "../../components/platform-shell";
import { RestaurantQueue } from "../../components/restaurant-queue";
import { brazilMarket } from "../../lib/market-config";

export default function RestaurantPage() {
  return (
    <PlatformShell market={brazilMarket}>
      <RestaurantQueue />
    </PlatformShell>
  );
}
