import type { Metadata } from "next";
import { PlatformShell } from "../../components/platform-shell";
import { RestaurantQueue } from "../../components/restaurant-queue";
import { brazilMarket } from "../../lib/market-config";

export const metadata: Metadata = { title: "Restaurante" };

export default function RestaurantPage() {
  return (
    <PlatformShell market={brazilMarket}>
      <RestaurantQueue />
    </PlatformShell>
  );
}
