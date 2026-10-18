import {describe,it,expect} from "vitest";
import {restaurantMapUrl} from "./restaurantMap";
import type {RestaurantDiscoveryPlace} from "./api/restaurantDiscoveryTypes";
const places=[{provider_place_id:"a",latitude:"38.7",longitude:"-9.1"},{provider_place_id:"b",latitude:"38.8",longitude:"-9.2"}] as RestaurantDiscoveryPlace[];
describe("restaurant selection map",()=>{
  it("moves the public marker to the selected restaurant",()=>{
    expect(new URL(restaurantMapUrl(places,"b")!).searchParams.get("marker")).toBe("38.8,-9.2");
    expect(new URL(restaurantMapUrl(places,"a")!).searchParams.get("marker")).toBe("38.7,-9.1");
  });
  it("uses the first available restaurant when results change and rejects invalid coordinates",()=>{
    expect(new URL(restaurantMapUrl(places,"missing")!).searchParams.get("marker")).toBe("38.7,-9.1");
    expect(restaurantMapUrl([],null)).toBeNull();
    expect(restaurantMapUrl([{...places[0]!,latitude:"not-a-number"}],null)).toBeNull();
  });
});
