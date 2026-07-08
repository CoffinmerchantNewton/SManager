import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';

export type MapProductLayer =
  | {
      kind: 'geojson';
      name: string;
      geojson: GeoJsonObject;
    }
  | {
      kind: 'image_overlay';
      name: string;
      imageUrl: string;
      bounds: {
        west: number;
        south: number;
        east: number;
        north: number;
      };
      opacity?: number;
    };

interface CesiumMapProps {
  cities: Array<{
    name: string;
    longitude: number;
    latitude: number;
    concentration: number;
    risk: string;
  }>;
  productLayer?: MapProductLayer | null;
  selectedCityName?: string;
  cityMarkerMode?: CityMarkerMode;
  onCitySelect?: (cityName: string) => void;
}

export type GeoJsonObject = Record<string, unknown>;
type CityMarkerMode = 'concentration' | 'compact';

export default function CesiumMap({
  cities,
  productLayer,
  selectedCityName,
  cityMarkerMode = 'concentration',
  onCitySelect,
}: CesiumMapProps) {
  const cesiumContainer = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const citySourceRef = useRef<Cesium.CustomDataSource | null>(null);
  const productSourceRef = useRef<Cesium.GeoJsonDataSource | null>(null);
  const productImageLayerRef = useRef<Cesium.ImageryLayer | null>(null);
  const productImageBoundsKeyRef = useRef<string>('');
  const onCitySelectRef = useRef(onCitySelect);

  useEffect(() => {
    onCitySelectRef.current = onCitySelect;
  }, [onCitySelect]);

  useEffect(() => {
    if (!cesiumContainer.current) return;

    const viewer = new Cesium.Viewer(cesiumContainer.current, {
      terrainProvider: new Cesium.EllipsoidTerrainProvider(),
      baseLayerPicker: false,
      geocoder: false,
      homeButton: false,
      sceneModePicker: false,
      navigationHelpButton: false,
      animation: false,
      timeline: false,
      fullscreenButton: false,
      vrButton: false,
      infoBox: false,
      selectionIndicator: false,
      baseLayer: false,
    });
    viewer.scene.globe.baseColor = Cesium.Color.fromCssColorString('#07111f');
    if (viewer.scene.skyAtmosphere) {
      viewer.scene.skyAtmosphere.show = false;
    }
    viewer.scene.fog.enabled = false;
    const clickHandler = new Cesium.ScreenSpaceEventHandler(viewer.scene.canvas);
    clickHandler.setInputAction((movement: Cesium.ScreenSpaceEventHandler.PositionedEvent) => {
      const picked = viewer.scene.pick(movement.position);
      const cityName = picked?.id?.properties?.cityName?.getValue?.();
      if (typeof cityName === 'string') {
        onCitySelectRef.current?.(cityName);
      }
    }, Cesium.ScreenSpaceEventType.LEFT_CLICK);

    viewerRef.current = viewer;

    // Set camera to China
    viewer.camera.setView({
      destination: Cesium.Cartesian3.fromDegrees(105.0, 35.0, 5000000),
      orientation: {
        heading: 0.0,
        pitch: -Cesium.Math.PI_OVER_TWO,
        roll: 0.0,
      },
    });

    let isDisposed = false;

    const loadBoundaryLayers = async () => {
      try {
        const [countryDataSource, provinceDataSource] = await Promise.all([
          Cesium.GeoJsonDataSource.load('/china-country-outline.geojson', {
            clampToGround: false,
            stroke: Cesium.Color.fromCssColorString('#00f1fe').withAlpha(0.95),
            fill: Cesium.Color.fromCssColorString('#00f1fe').withAlpha(0.06),
            strokeWidth: 4,
          }),
          Cesium.GeoJsonDataSource.load('/china-provinces-outline.geojson', {
            clampToGround: false,
            stroke: Cesium.Color.fromCssColorString('#7fdcff').withAlpha(0.55),
            fill: Cesium.Color.TRANSPARENT,
            strokeWidth: 1.5,
          }),
        ]);

        if (isDisposed || viewer.isDestroyed()) {
          return;
        }

        applyBoundaryStyle(countryDataSource, {
          strokeColor: Cesium.Color.fromCssColorString('#00f1fe').withAlpha(0.95),
          fillColor: Cesium.Color.fromCssColorString('#00f1fe').withAlpha(0.06),
          outlineWidth: 4,
        });
        applyBoundaryStyle(provinceDataSource, {
          strokeColor: Cesium.Color.fromCssColorString('#7fdcff').withAlpha(0.55),
          fillColor: Cesium.Color.TRANSPARENT,
          outlineWidth: 1.5,
        });

        await viewer.dataSources.add(countryDataSource);
        await viewer.dataSources.add(provinceDataSource);
      } catch (error) {
        console.error('Failed to load China boundary layers for Cesium map:', error);
      }
    };

    void loadBoundaryLayers();

    return () => {
      isDisposed = true;
      clickHandler.destroy();
      if (viewerRef.current) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, []);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    if (citySourceRef.current) {
      viewer.dataSources.remove(citySourceRef.current, true);
    }

    const citySource = new Cesium.CustomDataSource('pollen-city-markers');
    cities.forEach((city) => {
      const color = getRiskColorCesium(city.risk);
      const isSelected = city.name === selectedCityName;
      const markerRadius = markerRadiusMeters(city.concentration, isSelected, cityMarkerMode);
      const fillAlpha = cityMarkerMode === 'compact' ? (isSelected ? 0.28 : 0.14) : (isSelected ? 0.48 : 0.28);

      citySource.entities.add({
        properties: { cityName: city.name },
        position: Cesium.Cartesian3.fromDegrees(city.longitude, city.latitude, 10000),
        ellipse: {
          semiMinorAxis: markerRadius,
          semiMajorAxis: markerRadius,
          height: 0,
          material: color.withAlpha(fillAlpha),
          outline: true,
          outlineColor: isSelected ? Cesium.Color.WHITE : color,
          outlineWidth: isSelected ? 3 : 2,
        },
      });

      citySource.entities.add({
        properties: { cityName: city.name },
        position: Cesium.Cartesian3.fromDegrees(city.longitude, city.latitude, 50000),
        label: {
          text: cityMarkerMode === 'compact' ? city.name : `${city.name}\n${formatConcentration(city.concentration)}`,
          font: '14px sans-serif',
          fillColor: color,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -10),
        },
        point: {
          pixelSize: isSelected ? 12 : 8,
          color: color,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
        },
      });
    });

    citySourceRef.current = citySource;
    void viewer.dataSources.add(citySource);
  }, [cities, selectedCityName, cityMarkerMode]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed() || !selectedCityName) return;
    const city = cities.find((item) => item.name === selectedCityName);
    if (!city) return;
    void viewer.camera.flyTo({
      destination: Cesium.Cartesian3.fromDegrees(city.longitude, city.latitude, 900000),
      duration: 0.7,
    });
  }, [cities, selectedCityName]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    if (productSourceRef.current) {
      viewer.dataSources.remove(productSourceRef.current, true);
      productSourceRef.current = null;
    }
    if (productImageLayerRef.current) {
      viewer.imageryLayers.remove(productImageLayerRef.current, true);
      productImageLayerRef.current = null;
    }
    if (!productLayer) return;

    if (productLayer.kind === 'image_overlay') {
      const rectangle = Cesium.Rectangle.fromDegrees(
        productLayer.bounds.west,
        productLayer.bounds.south,
        productLayer.bounds.east,
        productLayer.bounds.north,
      );
      const layer = viewer.imageryLayers.addImageryProvider(
        new Cesium.SingleTileImageryProvider({
          url: productLayer.imageUrl,
          rectangle,
        }),
      );
      layer.alpha = productLayer.opacity ?? 0.72;
      productImageLayerRef.current = layer;
      const boundsKey = [
        productLayer.bounds.west,
        productLayer.bounds.south,
        productLayer.bounds.east,
        productLayer.bounds.north,
      ].join(',');
      if (productImageBoundsKeyRef.current !== boundsKey) {
        productImageBoundsKeyRef.current = boundsKey;
        void viewer.camera.flyTo({
          destination: rectangle,
          duration: 0.8,
        });
      }
      return;
    }

    let cancelled = false;
    Cesium.GeoJsonDataSource.load(productLayer.geojson, {
      clampToGround: false,
      stroke: Cesium.Color.fromCssColorString('#ffcc66').withAlpha(0.95),
      fill: Cesium.Color.fromCssColorString('#ff8a4c').withAlpha(0.32),
      markerColor: Cesium.Color.fromCssColorString('#ffcc66'),
      strokeWidth: 2,
    })
      .then(async (source) => {
        if (cancelled || viewer.isDestroyed()) {
          return;
        }
        source.name = productLayer.name;
        applyProductLayerStyle(source);
        productSourceRef.current = source;
        await viewer.dataSources.add(source);
      })
      .catch((error) => {
        console.error('Failed to load pollen product layer:', error);
      });

    return () => {
      cancelled = true;
    };
  }, [productLayer]);

  return <div ref={cesiumContainer} className="w-full h-full" />;
}

function applyBoundaryStyle(
  dataSource: Cesium.GeoJsonDataSource,
  {
    strokeColor,
    fillColor,
    outlineWidth,
  }: {
    strokeColor: Cesium.Color;
    fillColor: Cesium.Color;
    outlineWidth: number;
  },
) {
  for (const entity of dataSource.entities.values) {
    if (!entity.polygon) {
      continue;
    }

    entity.polygon.fill = new Cesium.ConstantProperty(fillColor.alpha > 0);
    entity.polygon.material = new Cesium.ColorMaterialProperty(fillColor);
    entity.polygon.height = new Cesium.ConstantProperty(0);
    entity.polygon.outline = new Cesium.ConstantProperty(true);
    entity.polygon.outlineColor = new Cesium.ConstantProperty(strokeColor);
    entity.polygon.outlineWidth = new Cesium.ConstantProperty(outlineWidth);
    entity.polygon.classificationType = new Cesium.ConstantProperty(
      Cesium.ClassificationType.BOTH,
    );
  }
}

function applyProductLayerStyle(dataSource: Cesium.GeoJsonDataSource) {
  for (const entity of dataSource.entities.values) {
    const pollenTotal = readEntityNumber(entity.properties?.pollen_total);
    const risk = readEntityString(entity.properties?.risk);
    const fillColor = pollenTotal != null ? colorForPollenValue(pollenTotal) : Cesium.Color.fromCssColorString('#ff8a4c').withAlpha(0.32);
    const strokeColor = risk ? getRiskColorCesium(risk) : Cesium.Color.fromCssColorString('#ffcc66').withAlpha(0.95);

    if (entity.polygon) {
      entity.polygon.fill = new Cesium.ConstantProperty(true);
      entity.polygon.material = new Cesium.ColorMaterialProperty(fillColor);
      entity.polygon.height = new Cesium.ConstantProperty(0);
      entity.polygon.outline = new Cesium.ConstantProperty(true);
      entity.polygon.outlineColor = new Cesium.ConstantProperty(strokeColor);
      entity.polygon.outlineWidth = new Cesium.ConstantProperty(2);
    }
    if (entity.polyline) {
      entity.polyline.material = new Cesium.ColorMaterialProperty(strokeColor);
      entity.polyline.width = new Cesium.ConstantProperty(2);
    }
    if (entity.point) {
      entity.point.pixelSize = new Cesium.ConstantProperty(pollenTotal != null ? 7 + Math.min(12, pollenTotal / 50) : 9);
      entity.point.color = new Cesium.ConstantProperty(strokeColor);
      entity.point.outlineColor = new Cesium.ConstantProperty(Cesium.Color.WHITE);
      entity.point.outlineWidth = new Cesium.ConstantProperty(1);
    }
  }
}

function readEntityNumber(value: Cesium.Property | undefined): number | null {
  const raw = value?.getValue?.(Cesium.JulianDate.now());
  return typeof raw === 'number' && Number.isFinite(raw) ? raw : null;
}

function readEntityString(value: Cesium.Property | undefined): string | null {
  const raw = value?.getValue?.(Cesium.JulianDate.now());
  return typeof raw === 'string' ? raw : null;
}

function colorForPollenValue(value: number): Cesium.Color {
  if (value >= 300) return Cesium.Color.fromCssColorString('#dc2626').withAlpha(0.45);
  if (value >= 150) return Cesium.Color.fromCssColorString('#fb923c').withAlpha(0.42);
  if (value >= 60) return Cesium.Color.fromCssColorString('#fde047').withAlpha(0.38);
  if (value >= 20) return Cesium.Color.fromCssColorString('#22c55e').withAlpha(0.34);
  return Cesium.Color.fromCssColorString('#2563eb').withAlpha(0.3);
}

function getRiskColorCesium(risk: string): Cesium.Color {
  switch (risk) {
    case 'critical':
      return Cesium.Color.fromCssColorString('#ffb4ab');
    case 'high':
      return Cesium.Color.fromCssColorString('#ff8a80');
    case 'medium':
      return Cesium.Color.fromCssColorString('#00f1fe');
    case 'low':
      return Cesium.Color.fromCssColorString('#50e167');
    default:
      return Cesium.Color.fromCssColorString('#8c90a1');
  }
}

function markerRadiusMeters(concentration: number, selected: boolean, mode: CityMarkerMode): number {
  if (mode === 'compact') {
    return selected ? 28000 : 18000;
  }
  const value = Number.isFinite(concentration) ? Math.max(0, concentration) : 0;
  const base = Math.sqrt(value) * 5500;
  const capped = Math.max(14000, Math.min(180000, base));
  return selected ? capped * 1.25 : capped;
}

function formatConcentration(value: number): string {
  if (!Number.isFinite(value)) {
    return '--';
  }
  if (value >= 1000) {
    return `${Math.round(value).toLocaleString()} grains/kg`;
  }
  return `${Math.round(value * 10) / 10} grains/kg`;
}
