import { useEffect, useRef } from 'react';
import * as Cesium from 'cesium';

interface CesiumMapProps {
  cities: Array<{
    name: string;
    longitude: number;
    latitude: number;
    concentration: number;
    risk: string;
  }>;
  productLayer?: {
    name: string;
    geojson: any;
  } | null;
}

export default function CesiumMap({ cities, productLayer }: CesiumMapProps) {
  const cesiumContainer = useRef<HTMLDivElement>(null);
  const viewerRef = useRef<Cesium.Viewer | null>(null);
  const citySourceRef = useRef<Cesium.CustomDataSource | null>(null);
  const productSourceRef = useRef<Cesium.GeoJsonDataSource | null>(null);

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

    return () => {
      isDisposed = true;
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

      citySource.entities.add({
        position: Cesium.Cartesian3.fromDegrees(city.longitude, city.latitude, 10000),
        ellipse: {
          semiMinorAxis: city.concentration * 500,
          semiMajorAxis: city.concentration * 500,
          material: color.withAlpha(0.3),
          outline: true,
          outlineColor: color,
          outlineWidth: 2,
        },
      });

      citySource.entities.add({
        position: Cesium.Cartesian3.fromDegrees(city.longitude, city.latitude, 50000),
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

    citySourceRef.current = citySource;
    void viewer.dataSources.add(citySource);
  }, [cities]);

  useEffect(() => {
    const viewer = viewerRef.current;
    if (!viewer || viewer.isDestroyed()) return;

    if (productSourceRef.current) {
      viewer.dataSources.remove(productSourceRef.current, true);
      productSourceRef.current = null;
    }
    if (!productLayer?.geojson) return;

    let cancelled = false;
    Cesium.GeoJsonDataSource.load(productLayer.geojson, {
      clampToGround: true,
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
    if (entity.polygon) {
      entity.polygon.fill = new Cesium.ConstantProperty(true);
      entity.polygon.material = new Cesium.ColorMaterialProperty(
        Cesium.Color.fromCssColorString('#ff8a4c').withAlpha(0.32),
      );
      entity.polygon.outline = new Cesium.ConstantProperty(true);
      entity.polygon.outlineColor = new Cesium.ConstantProperty(
        Cesium.Color.fromCssColorString('#ffcc66').withAlpha(0.95),
      );
      entity.polygon.outlineWidth = new Cesium.ConstantProperty(2);
    }
    if (entity.polyline) {
      entity.polyline.material = new Cesium.ColorMaterialProperty(
        Cesium.Color.fromCssColorString('#ffcc66').withAlpha(0.9),
      );
      entity.polyline.width = new Cesium.ConstantProperty(2);
    }
    if (entity.point) {
      entity.point.pixelSize = new Cesium.ConstantProperty(9);
      entity.point.color = new Cesium.ConstantProperty(Cesium.Color.fromCssColorString('#ffcc66'));
      entity.point.outlineColor = new Cesium.ConstantProperty(Cesium.Color.BLACK);
      entity.point.outlineWidth = new Cesium.ConstantProperty(1);
    }
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
