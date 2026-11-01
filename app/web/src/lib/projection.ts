/** Geographic bounds and the lat/lon → canvas projection shared by the map and the lab. */

export type GeoBounds = {
  minLatitude: number;
  maxLatitude: number;
  minLongitude: number;
  maxLongitude: number;
};

export type ProjectionOptions = {
  width?: number;
  height?: number;
  /** Fraction of the span added as margin on every side. */
  padding?: number;
  /** Never collapse to a zero span (a single point still needs a box). */
  minSpanDegrees?: number;
};

export type Projection = {
  width: number;
  height: number;
  bounds: GeoBounds;
  project(latitude: number, longitude: number): [number, number];
  invert(x: number, y: number): { latitude: number; longitude: number };
};

export function boundsOf(
  points: Iterable<{ latitude: number; longitude: number }>,
): GeoBounds {
  let minLatitude = Infinity;
  let maxLatitude = -Infinity;
  let minLongitude = Infinity;
  let maxLongitude = -Infinity;
  for (const point of points) {
    minLatitude = Math.min(minLatitude, point.latitude);
    maxLatitude = Math.max(maxLatitude, point.latitude);
    minLongitude = Math.min(minLongitude, point.longitude);
    maxLongitude = Math.max(maxLongitude, point.longitude);
  }
  if (!Number.isFinite(minLatitude)) {
    return { minLatitude: 0, maxLatitude: 0, minLongitude: 0, maxLongitude: 0 };
  }
  return { minLatitude, maxLatitude, minLongitude, maxLongitude };
}

export function createProjection(
  bounds: GeoBounds,
  options: ProjectionOptions = {},
): Projection {
  const width = options.width ?? 640;
  const height = options.height ?? 420;
  const padding = options.padding ?? 0.08;
  const minSpan = options.minSpanDegrees ?? 0.001;

  const centerLatitude = (bounds.minLatitude + bounds.maxLatitude) / 2;
  const centerLongitude = (bounds.minLongitude + bounds.maxLongitude) / 2;
  const latitudeSpan = Math.max(bounds.maxLatitude - bounds.minLatitude, minSpan);
  const longitudeSpan = Math.max(bounds.maxLongitude - bounds.minLongitude, minSpan);
  const paddedLatitudeSpan = latitudeSpan * (1 + 2 * padding);
  const paddedLongitudeSpan = longitudeSpan * (1 + 2 * padding);

  const south = centerLatitude - paddedLatitudeSpan / 2;
  const north = centerLatitude + paddedLatitudeSpan / 2;
  const west = centerLongitude - paddedLongitudeSpan / 2;
  const east = centerLongitude + paddedLongitudeSpan / 2;

  return {
    width,
    height,
    bounds: { minLatitude: south, maxLatitude: north, minLongitude: west, maxLongitude: east },
    project(latitude: number, longitude: number): [number, number] {
      return [
        ((longitude - west) / (east - west)) * width,
        (1 - (latitude - south) / (north - south)) * height,
      ];
    },
    invert(x: number, y: number) {
      return {
        longitude: Math.min(east, Math.max(west, west + (x / width) * (east - west))),
        latitude: Math.min(north, Math.max(south, south + (1 - y / height) * (north - south))),
      };
    },
  };
}
