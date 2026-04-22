import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';

interface CesiumMapProps {
  cities: Array<{
    name: string;
    x: number;
    y: number;
    concentration: number;
    risk: string;
  }>;
}

export default function CesiumMap({ cities }: CesiumMapProps) {
  const cesiumContainer = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);

  useEffect(() => {
    if (!cesiumContainer.current) return;

    // Set Cesium Ion access token (use default for now)
    Cesium.Ion.defaultAccessToken = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJqdGkiOiJlYWE1OWUxNy1mMWZiLTQzYjYtYTQ0OS1kMWFjYmFkNjc5YzciLCJpZCI6NTc3MzMsImlhdCI6MTYyNzg0NTE4Mn0.XcKpgANiY19MC4bdFUXMVEBToBmqS8kuYpUlxJHYZxk';

    // Create Cesium Viewer
    const viewer = new Cesium.Viewer(cesiumContainer.current, {
      terrain: Cesium.Terrain.fromWorldTerrain(),
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
      baseLayer: Cesium.ImageryLayer.fromProviderAsync(
        Cesium.IonImageryProvider.fromAssetId(3954),
      ),
    });

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
            clampToGround: true,
            stroke: Cesium.Color.fromCssColorString('#00f1fe').withAlpha(0.95),
            fill: Cesium.Color.fromCssColorString('#00f1fe').withAlpha(0.06),
            strokeWidth: 4,
          }),
          Cesium.GeoJsonDataSource.load('/china-provinces-outline.geojson', {
            clampToGround: true,
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

    // Add city markers with pollen concentration
    cities.forEach((city) => {
      const lon = 73.5 + (city.x / 900) * (135.0 - 73.5);
      const lat = 18.0 + ((700 - city.y) / 700) * (53.5 - 18.0);

      const color = getRiskColorCesium(city.risk);

      // Add circle for concentration
      viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(lon, lat, 10000),
        ellipse: {
          semiMinorAxis: city.concentration * 500,
          semiMajorAxis: city.concentration * 500,
          material: color.withAlpha(0.3),
          outline: true,
          outlineColor: color,
          outlineWidth: 2,
        },
      });

      // Add city label
      viewer.entities.add({
        position: Cesium.Cartesian3.fromDegrees(lon, lat, 50000),
        label: {
          text: `${city.name}\n${city.concentration} n/m³`,
          font: '14px sans-serif',
          fillColor: color,
          outlineColor: Cesium.Color.BLACK,
          outlineWidth: 2,
          style: Cesium.LabelStyle.FILL_AND_OUTLINE,
          verticalOrigin: Cesium.VerticalOrigin.BOTTOM,
          pixelOffset: new Cesium.Cartesian2(0, -10),
        },
        point: {
          pixelSize: 8,
          color: color,
          outlineColor: Cesium.Color.WHITE,
          outlineWidth: 2,
        },
      });
    });

    return () => {
      isDisposed = true;
      if (viewerRef.current) {
        viewerRef.current.destroy();
        viewerRef.current = null;
      }
    };
  }, [cities]);

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
    entity.polygon.outline = new Cesium.ConstantProperty(true);
    entity.polygon.outlineColor = new Cesium.ConstantProperty(strokeColor);
    entity.polygon.outlineWidth = new Cesium.ConstantProperty(outlineWidth);
    entity.polygon.classificationType = new Cesium.ConstantProperty(
      Cesium.ClassificationType.BOTH,
    );
  }
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
