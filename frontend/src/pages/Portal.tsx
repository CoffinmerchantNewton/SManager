import { useEffect, useState } from 'react';
import CesiumMap, { type MapProductLayer } from '../components/CesiumMap';
import { cities } from '../data/chinaMap';
import { productsApi } from '../services/api';
import type { ForecastProduct } from '../types';

export default function Portal() {
  const [productLayer, setProductLayer] = useState<MapProductLayer | null>(null);
  const [productStatus, setProductStatus] = useState('Using simulated city observations');

  useEffect(() => {
    let cancelled = false;

    const loadLatestProductLayer = async () => {
      try {
        const response = await productsApi.getAll({ status: 'ready', limit: 50 });
        const products = response.data as ForecastProduct[];
        const overlayMetadata = products.find(isOverlayMetadataProduct);
        if (overlayMetadata) {
          const content = await productsApi.content(overlayMetadata.id);
          const overlayLayer = buildOverlayLayer(overlayMetadata, content.data, products);
          if (cancelled) return;
          if (overlayLayer) {
            setProductLayer(overlayLayer);
            setProductStatus(`Overlay: ${overlayLayer.name}`);
            return;
          }
        }

        const product = products.find(isInlineMapProduct);
        if (!product) {
          setProductStatus('No map-ready product layer indexed yet');
          return;
        }
        const content = await productsApi.content(product.id);
        if (cancelled) return;
        setProductLayer({ kind: 'geojson', name: product.product_name, geojson: content.data });
        setProductStatus(`Layer: ${product.product_name}`);
      } catch (error) {
        console.error('Failed to load latest product layer:', error);
        if (!cancelled) {
          setProductStatus('Product layer unavailable; using simulated city observations');
        }
      }
    };

    void loadLatestProductLayer();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="min-h-screen bg-background text-on-background font-body-md">
      {/* TopNavBar */}
      <header className="fixed top-0 w-full h-14 flex justify-between items-center px-6 z-50 bg-slate-950/95 backdrop-blur-md font-inter tracking-tight antialiased text-sm border-b border-white/10">
        <div className="flex items-center gap-4">
          <div className="flex flex-col">
            <span className="text-lg font-black tracking-tighter text-white uppercase">中国花粉传播预报系统</span>
            <span className="text-[10px] text-slate-400 font-medium tracking-wide">
              基于 WRF-Pollen / WRF-Chem 的全国花粉扩散与业务预报平台
            </span>
          </div>
        </div>
        <div className="flex items-center gap-6">
          <div className="hidden md:flex gap-8">
            <a className="text-cyan-400 border-b-2 border-cyan-400 pb-1" href="#">
              Dashboard
            </a>
            <a className="text-slate-400 hover:text-cyan-300 transition-colors" href="#">
              Real-time Map
            </a>
            <a className="text-slate-400 hover:text-cyan-300 transition-colors" href="#">
              Forecasting
            </a>
            <a className="text-slate-400 hover:text-cyan-300 transition-colors" href="#">
              Archive
            </a>
          </div>
          <div className="flex items-center gap-4">
            <button className="material-symbols-outlined text-slate-400 hover:text-white transition-colors">
              notifications
            </button>
            <button className="material-symbols-outlined text-slate-400 hover:text-white transition-colors">
              account_circle
            </button>
            <a
              href="/login"
              className="bg-primary-container hover:bg-blue-600 text-white px-4 py-1.5 rounded-lg font-semibold tracking-tight transition-all active:scale-95 shadow-lg shadow-blue-900/20"
            >
              控制台
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="relative mt-14 h-[calc(100vh-3.5rem)] overflow-hidden flex flex-col">
        {/* WebGIS Map Container - Cesium */}
        <div className="relative flex-grow bg-slate-950 overflow-hidden">
          <CesiumMap cities={cities} productLayer={productLayer} />
          <div className="absolute inset-0 pointer-events-none border border-white/5"></div>

          {/* Floating Controls: Left */}
          <div className="absolute left-margin top-margin flex flex-col gap-4 w-64 z-20">
            {/* System Status Card */}
            <div className="glass-panel p-md rounded-xl border border-white/10 glow-border">
              <div className="flex items-center justify-between mb-sm">
                <span className="font-label-caps text-on-surface-variant uppercase">Current Status</span>
                <span className="flex h-2 w-2 rounded-full bg-tertiary animate-pulse"></span>
              </div>
              <div className="space-y-sm">
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest">Active Model</p>
                  <p className="font-data-mono text-white">WRF-Chem v4.2.1</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest">Map Product</p>
                  <p className="font-data-mono text-white break-words">{productStatus}</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest">Simulation Domain</p>
                  <p className="font-data-mono text-white">D02 (9km Resolution)</p>
                </div>
                <div>
                  <p className="text-[10px] text-slate-500 uppercase tracking-widest">System Load</p>
                  <div className="w-full h-1 bg-white/5 mt-1">
                    <div className="h-full bg-cyan-400 w-2/3 glow-border"></div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Floating Controls: Right */}
          <div className="absolute right-margin top-margin flex flex-col gap-4 w-72 z-20">
            {/* Current Product Info */}
            <div className="glass-panel p-md rounded-xl border border-white/10">
              <h3 className="font-label-caps text-on-surface-variant uppercase mb-md">Real-time Analytics</h3>
              <div className="grid grid-cols-2 gap-sm">
                <div className="bg-white/5 p-sm rounded border border-white/5">
                  <p className="text-[10px] text-slate-500 uppercase mb-xs">Peak Concen.</p>
                  <p className="font-data-mono text-xl text-error">
                    1,248<span className="text-[10px] ml-1">n/m³</span>
                  </p>
                </div>
                <div className="bg-white/5 p-sm rounded border border-white/5">
                  <p className="text-[10px] text-slate-500 uppercase mb-xs">Hotspot Count</p>
                  <p className="font-data-mono text-xl text-cyan-400">142</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom Analysis Area */}
        <section className="h-48 bg-slate-950 border-t border-white/10 flex items-center p-gutter gap-gutter overflow-x-auto">
          {/* Chart Card 1: Time Series */}
          <div className="min-w-[400px] h-full glass-panel p-md rounded-xl border border-white/10 flex flex-col">
            <div className="flex items-center justify-between mb-sm">
              <span className="font-label-caps text-on-surface-variant uppercase flex items-center gap-2">
                <span className="material-symbols-outlined text-xs">analytics</span> Time Series Analysis
              </span>
              <span className="text-[10px] font-data-mono text-cyan-400">Avg: 412 n/m³</span>
            </div>
            <div className="flex-grow relative flex items-end gap-1">
              {[30, 45, 60, 80, 65, 40, 35, 55, 90, 70].map((height, i) => (
                <div
                  key={i}
                  className="flex-grow bg-cyan-500/20 border-t border-cyan-500/40"
                  style={{ height: `${height}%` }}
                ></div>
              ))}
            </div>
          </div>

          {/* Chart Card 2: Regional Intensity */}
          <div className="min-w-[400px] h-full glass-panel p-md rounded-xl border border-white/10 flex flex-col">
            <div className="flex items-center justify-between mb-sm">
              <span className="font-label-caps text-on-surface-variant uppercase flex items-center gap-2">
                <span className="material-symbols-outlined text-xs">bar_chart</span> Regional Intensity
              </span>
              <span className="text-[10px] font-data-mono text-slate-500">Unit: Percentile</span>
            </div>
            <div className="flex-grow flex flex-col justify-between py-2">
              <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-error w-[85%]"></div>
              </div>
              <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-cyan-400 w-[60%]"></div>
              </div>
              <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-tertiary w-[40%]"></div>
              </div>
              <div className="w-full h-2 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-cyan-400 w-[55%]"></div>
              </div>
            </div>
          </div>

          {/* Chart Card 3: System Logs */}
          <div className="min-w-[300px] h-full glass-panel p-md rounded-xl border border-white/10 overflow-hidden">
            <p className="font-label-caps text-on-surface-variant uppercase mb-sm">System Logs</p>
            <div className="font-data-mono text-[10px] space-y-1 text-slate-500 overflow-y-auto h-full">
              <p>
                <span className="text-tertiary">[OK]</span> Model initialized: WRF-Pollen_v2.0
              </p>
              <p>
                <span className="text-tertiary">[OK]</span> Satellite data ingestion complete.
              </p>
              <p>
                <span className="text-cyan-400">[INFO]</span> Forecast grid updated for Beijing-Tianjin-Hebei.
              </p>
              <p>
                <span className="text-error">[WARN]</span> Anomaly detected in North China Plain region.
              </p>
              <p>
                <span className="text-slate-400">[WAIT]</span> Pending data stream from GFS-SFC.
              </p>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function isInlineMapProduct(product: ForecastProduct) {
  const type = product.product_type.toLowerCase();
  const path = product.file_path.toLowerCase();
  return (
    type.includes('geojson') ||
    path.endsWith('.geojson') ||
    (path.endsWith('.json') && !isOverlayMetadataProduct(product))
  );
}

function isOverlayMetadataProduct(product: ForecastProduct) {
  const type = product.product_type.toLowerCase();
  const path = product.file_path.toLowerCase();
  return type.includes('png_overlay_metadata') || path.endsWith('.overlay.json');
}

function isOverlayImageProduct(product: ForecastProduct) {
  const type = product.product_type.toLowerCase();
  const path = product.file_path.toLowerCase();
  return type === 'png_overlay' || type === 'map_png' || path.endsWith('.png');
}

function buildOverlayLayer(
  metadataProduct: ForecastProduct,
  metadata: any,
  products: ForecastProduct[],
): MapProductLayer | null {
  if (!isOverlayMetadata(metadata)) {
    return null;
  }
  const imageProduct = findOverlayImageProduct(metadataProduct, metadata, products);
  if (!imageProduct) {
    return null;
  }
  return {
    kind: 'image_overlay',
    name: metadataProduct.product_name,
    imageUrl: productsApi.downloadUrl(imageProduct.id),
    bounds: metadata.bounds,
    opacity: metadata.opacity,
  };
}

function findOverlayImageProduct(
  metadataProduct: ForecastProduct,
  metadata: PngOverlayMetadata,
  products: ForecastProduct[],
) {
  const runId = metadataProduct.product_name.split(':')[0];
  const expectedProductName = `${runId}:${metadata.image.name}`;
  return products.find((product) => {
    const path = product.file_path.toLowerCase();
    return (
      isOverlayImageProduct(product) &&
      (product.product_name === expectedProductName || path.endsWith(`/${metadata.image.name.toLowerCase()}`))
    );
  });
}

interface PngOverlayMetadata {
  type: 'png_overlay';
  image: {
    name: string;
  };
  bounds: {
    west: number;
    south: number;
    east: number;
    north: number;
  };
  opacity?: number;
}

function isOverlayMetadata(value: any): value is PngOverlayMetadata {
  return (
    value?.type === 'png_overlay' &&
    typeof value?.image?.name === 'string' &&
    typeof value?.bounds?.west === 'number' &&
    typeof value?.bounds?.south === 'number' &&
    typeof value?.bounds?.east === 'number' &&
    typeof value?.bounds?.north === 'number'
  );
}
