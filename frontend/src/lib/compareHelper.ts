import { VehicleItem } from "@/types";

export function getSmartPeerVehicle(current: VehicleItem, all: VehicleItem[]): VehicleItem {
  if (!all || all.length === 0) return current;

  // If Electric, pick other Electric
  if (current.category === "Born Electric SUV") {
    const peer = all.find((v) => v.id !== current.id && v.category === "Born Electric SUV");
    if (peer) return peer;
  }
  // Smart peer mapping
  if (current.id === "thar_roxx") {
    const peer = all.find((v) => v.id === "scorpio_n" || v.id === "thar_3door");
    if (peer) return peer;
  }
  if (current.id === "scorpio_n") {
    const peer = all.find((v) => v.id === "xuv700" || v.id === "thar_roxx");
    if (peer) return peer;
  }
  if (current.id === "xuv700") {
    const peer = all.find((v) => v.id === "scorpio_n" || v.id === "xuv_3xo");
    if (peer) return peer;
  }
  if (current.id === "be_6e") {
    const peer = all.find((v) => v.id === "xev_9e" || v.id === "xuv400_ev");
    if (peer) return peer;
  }
  if (current.id === "xev_9e") {
    const peer = all.find((v) => v.id === "be_6e");
    if (peer) return peer;
  }
  if (current.id === "xuv_3xo") {
    const peer = all.find((v) => v.id === "xuv700" || v.id === "xuv400_ev");
    if (peer) return peer;
  }
  if (current.id === "bolero_neo") {
    const peer = all.find((v) => v.id === "bolero" || v.id === "scorpio_classic");
    if (peer) return peer;
  }
  if (current.id === "bolero") {
    const peer = all.find((v) => v.id === "bolero_neo" || v.id === "bolero_maxx");
    if (peer) return peer;
  }
  if (current.id === "thar_3door") {
    const peer = all.find((v) => v.id === "thar_roxx");
    if (peer) return peer;
  }

  // Fallback to any other vehicle
  const other = all.find((v) => v.id !== current.id);
  return other || all[0];
}
