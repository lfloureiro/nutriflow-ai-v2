import type {RestaurantDiscoveryPlace} from "./api/restaurantDiscoveryTypes";

export function restaurantMapUrl(places:RestaurantDiscoveryPlace[], selectedId:string|null):string|null {
  const valid=places.filter(p=>Number.isFinite(Number(p.latitude))&&Number.isFinite(Number(p.longitude))&&Math.abs(Number(p.latitude))<=90&&Math.abs(Number(p.longitude))<=180);
  const selected=valid.find(p=>p.provider_place_id===selectedId)??valid[0];
  if(!selected)return null;
  const lat=Number(selected.latitude),lon=Number(selected.longitude);
  const bbox=[Math.max(-180,lon-0.008),Math.max(-90,lat-0.006),Math.min(180,lon+0.008),Math.min(90,lat+0.006)].join(",");
  return `https://www.openstreetmap.org/export/embed.html?${new URLSearchParams({bbox,layer:"mapnik",marker:`${lat},${lon}`})}`;
}
