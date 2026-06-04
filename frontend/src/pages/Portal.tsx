import { useEffect, useMemo, useState, type ReactNode } from 'react';
import CesiumMap, { type MapProductLayer } from '../components/CesiumMap';
import { cities as fallbackCities } from '../data/chinaMap';
import { productsApi } from '../services/api';
import type { ForecastProduct } from '../types';

const SPECIES_LABELS: Record<number, string> = {
  1: '常绿针叶',
  2: '杨柳',
  3: '栎树',
  4: '榆树',
  5: '白桦',
  6: '落叶松',
  7: '禾本科',
  8: '蒿属',
  9: '藜科',
};

const RISK_META: Record<string, { label: string; color: string; bg: string; rank: number }> = {
  low: { label: '低', color: '#50e167', bg: 'rgba(80,225,103,0.16)', rank: 1 },
  medium: { label: '中', color: '#00f1fe', bg: 'rgba(0,241,254,0.16)', rank: 2 },
  high: { label: '高', color: '#ff8a80', bg: 'rgba(255,138,128,0.18)', rank: 3 },
  critical: { label: '极高', color: '#ffb4ab', bg: 'rgba(255,180,171,0.22)', rank: 4 },
  unknown: { label: '未知', color: '#8c90a1', bg: 'rgba(140,144,161,0.14)', rank: 0 },
};

export default function Portal() {
  const [productLayer, setProductLayer] = useState<MapProductLayer | null>(null);
  const [cityForecast, setCityForecast] = useState<CityForecastPayload | null>(null);
  const [productStatus, setProductStatus] = useState('等待地图产品');
  const [cityStatus, setCityStatus] = useState('等待城市预报产品');
  const [query, setQuery] = useState('');
  const [selectedCityName, setSelectedCityName] = useState('北京');
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const loadLatestProducts = async () => {
      setIsLoading(true);
      try {
        const response = await productsApi.getAll({ status: 'ready', limit: 80 });
        const products = response.data as ForecastProduct[];

        const cityProduct = products.find(isCityForecastProduct);
        if (cityProduct) {
          const content = await productsApi.content(cityProduct.id);
          if (!cancelled && isCityForecastPayload(content.data)) {
            const payload = content.data;
            setCityForecast(payload);
            setCityStatus(`城市预报: ${cityProduct.product_name}`);
            const firstCity = payload.cities[0];
            if (firstCity) {
              setSelectedCityName((current) =>
                payload.cities.some((city) => city.name === current) ? current : firstCity.name,
              );
            }
          }
        } else if (!cancelled) {
          setCityStatus('未索引 city_forecast_json，使用示例城市点');
        }

        const overlayMetadata = products.find(isOverlayMetadataProduct);
        if (overlayMetadata) {
          const content = await productsApi.content(overlayMetadata.id);
          const overlayLayer = buildOverlayLayer(overlayMetadata, content.data, products);
          if (cancelled) return;
          if (overlayLayer) {
            setProductLayer(overlayLayer);
            setProductStatus(`浓度底图: ${overlayLayer.name}`);
            return;
          }
        }

        const product = products.find(isInlineMapProduct);
        if (!product) {
          if (!cancelled) {
            setProductStatus('未索引可渲染地图产品');
          }
          return;
        }
        const content = await productsApi.content(product.id);
        if (cancelled) return;
        setProductLayer({ kind: 'geojson', name: product.product_name, geojson: content.data });
        setProductStatus(`采样图层: ${product.product_name}`);
      } catch (error) {
        console.warn('Latest pollen products are unavailable:', error);
        if (!cancelled) {
          setProductStatus('地图产品暂不可用');
          setCityStatus('城市预报暂不可用');
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    void loadLatestProducts();
    return () => {
      cancelled = true;
    };
  }, []);

  const forecastCities = cityForecast?.cities ?? [];
  const hasForecast = forecastCities.length > 0;
  const selectedCity = useMemo(
    () => forecastCities.find((city) => city.name === selectedCityName) ?? forecastCities[0],
    [forecastCities, selectedCityName],
  );
  const selectedFallbackCity = useMemo(
    () => fallbackCities.find((city) => city.name === selectedCityName) ?? fallbackCities[0],
    [selectedCityName],
  );
  const activeForecast = selectedCity?.forecast ?? [];
  const activeDayIndex = clampIndex(selectedDayIndex, activeForecast.length || 1);
  const activeStep = activeForecast[activeDayIndex] ?? fallbackStep(selectedFallbackCity);
  const timeline = activeForecast.length > 0 ? activeForecast : fallbackTimeline(selectedFallbackCity);
  const cityOptions = useMemo(() => {
    const source = hasForecast
      ? forecastCities.map((city) => ({ name: city.name, longitude: city.longitude, latitude: city.latitude }))
      : fallbackCities.map((city) => ({ name: city.name, longitude: city.longitude, latitude: city.latitude }));
    const normalized = query.trim().toLowerCase();
    if (!normalized) {
      return source.slice(0, 12);
    }
    return source.filter((city) => city.name.toLowerCase().includes(normalized)).slice(0, 12);
  }, [forecastCities, hasForecast, query]);
  const mapCities = useMemo(
    () =>
      hasForecast
        ? forecastCities.map((city) => {
            const step = city.forecast[activeDayIndex] ?? city.forecast[0];
            return {
              name: city.name,
              longitude: city.longitude,
              latitude: city.latitude,
              concentration: safeNumber(step?.pollen_total),
              risk: step?.risk ?? 'unknown',
            };
          })
        : fallbackCities,
    [activeDayIndex, forecastCities, hasForecast],
  );
  const risk = riskMeta(activeStep.risk);
  const peak = maxForecastValue(timeline);
  const dominantSpecies = formatSpecies(activeStep);

  return (
    <div className="min-h-screen bg-background text-on-background font-body-md">
      <header className="fixed top-0 z-50 flex h-14 w-full items-center justify-between border-b border-white/10 bg-slate-950/95 px-5 backdrop-blur-md">
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-base font-black uppercase tracking-wide text-white">中国花粉传播预报系统</span>
          <span className="hidden text-[10px] font-medium uppercase tracking-[0.18em] text-slate-400 sm:block">
            WRF-Pollen operational forecast
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-2 rounded border border-white/10 bg-white/5 px-3 py-1.5 text-[11px] text-slate-300 md:flex">
            <span className={`h-2 w-2 rounded-full ${isLoading ? 'bg-amber-300' : 'bg-tertiary'}`} />
            <span>{isLoading ? '加载中' : '产品就绪'}</span>
          </div>
          <a
            href="/login"
            className="rounded bg-primary-container px-3 py-1.5 text-sm font-semibold text-white shadow-lg shadow-blue-900/20 transition-colors hover:bg-primary-container/80"
          >
            控制台
          </a>
        </div>
      </header>

      <main className="relative mt-14 h-[calc(100vh-3.5rem)] overflow-hidden bg-slate-950">
        <CesiumMap cities={mapCities} productLayer={productLayer} selectedCityName={selectedCityName} />
        <div className="pointer-events-none absolute inset-0 border border-white/5" />

        <section className="absolute left-4 top-4 z-20 hidden w-72 flex-col gap-3 lg:flex">
          <Panel title="图层">
            <div className="space-y-3">
              <StatusLine icon="layers" label="底图" value={productStatus} />
              <StatusLine icon="location_city" label="城市预报" value={cityStatus} />
              <StatusLine icon="schedule" label="预报步长" value={`${timeline.length} 天`} />
            </div>
          </Panel>
          <Panel title="色带">
            <div
              className="h-3 rounded"
              style={{
                background:
                  'linear-gradient(90deg, #2563eb 0%, #22c55e 34%, #fde047 62%, #fb923c 80%, #dc2626 100%)',
              }}
            />
            <div className="mt-2 flex justify-between text-[10px] text-slate-400">
              <span>低</span>
              <span>中</span>
              <span>高</span>
              <span>极高</span>
            </div>
          </Panel>
        </section>

        <section className="absolute right-4 top-4 bottom-32 z-20 hidden w-[360px] flex-col gap-3 overflow-y-auto xl:flex">
          <Panel title="城市查询">
            <div className="relative">
              <span className="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-base text-slate-500">
                search
              </span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="w-full rounded border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-cyan-300/60"
                placeholder="搜索城市"
              />
            </div>
            <div className="mt-3 grid grid-cols-2 gap-2">
              {cityOptions.map((city) => (
                <button
                  key={city.name}
                  onClick={() => {
                    setSelectedCityName(city.name);
                    setQuery('');
                  }}
                  className={`rounded border px-3 py-2 text-left text-sm transition-colors ${
                    city.name === selectedCityName
                      ? 'border-cyan-300/70 bg-cyan-300/15 text-white'
                      : 'border-white/10 bg-white/5 text-slate-300 hover:border-white/25'
                  }`}
                >
                  {city.name}
                </button>
              ))}
            </div>
          </Panel>

          <Panel title={selectedCity?.name ?? selectedFallbackCity.name}>
            <div className="flex items-start justify-between gap-3">
              <div>
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Risk</p>
                <div className="mt-1 flex items-center gap-2">
                  <span className="rounded px-2 py-1 text-sm font-bold" style={{ color: risk.color, background: risk.bg }}>
                    {risk.label}
                  </span>
                  <span className="text-xs text-slate-400">第 {activeStep.forecast_day} 天</span>
                </div>
              </div>
              <div className="text-right">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">Pollen</p>
                <p className="font-data-mono text-2xl text-white">{formatNumber(activeStep.pollen_total)}</p>
                <p className="text-[10px] text-slate-500">grains/kg-dryair</p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <Metric icon="thermostat" label="气温" value={formatUnit(activeStep.t2_c, '°C')} />
              <Metric icon="air" label="风速" value={formatUnit(activeStep.wind10_ms, 'm/s')} />
              <Metric icon="water_drop" label="降水" value={formatUnit(activeStep.precip_step_mm, 'mm')} />
              <Metric icon="eco" label="主导物种" value={dominantSpecies} />
            </div>
          </Panel>
        </section>

        <section className="absolute bottom-4 left-4 right-4 z-20">
          <div className="grid gap-3 rounded-lg border border-white/10 bg-slate-950/88 p-3 shadow-2xl backdrop-blur-md lg:grid-cols-[minmax(260px,360px)_1fr]">
            <div className="min-w-0">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">{selectedCity?.name ?? selectedFallbackCity.name}</p>
                  <p className="truncate text-[11px] text-slate-400">{hasForecast ? '城市预报产品' : '示例城市点'}</p>
                </div>
                <span className="rounded px-2 py-1 text-xs font-bold" style={{ color: risk.color, background: risk.bg }}>
                  {risk.label}
                </span>
              </div>
              <div className="mt-3 grid grid-cols-4 gap-2 text-center">
                <CompactStat label="花粉" value={formatNumber(activeStep.pollen_total)} />
                <CompactStat label="气温" value={formatNumber(activeStep.t2_c)} />
                <CompactStat label="风速" value={formatNumber(activeStep.wind10_ms)} />
                <CompactStat label="降水" value={formatNumber(activeStep.precip_step_mm)} />
              </div>
            </div>

            <div className="grid grid-cols-7 gap-2">
              {timeline.slice(0, 7).map((step, index) => {
                const meta = riskMeta(step.risk);
                const height = peak > 0 ? Math.max(8, Math.round((safeNumber(step.pollen_total) / peak) * 46)) : 8;
                return (
                  <button
                    key={`${step.time_index}-${index}`}
                    onClick={() => setSelectedDayIndex(index)}
                    className={`flex min-h-[92px] flex-col justify-between rounded border p-2 text-left transition-colors ${
                      index === activeDayIndex
                        ? 'border-cyan-300/70 bg-cyan-300/15'
                        : 'border-white/10 bg-white/5 hover:border-white/25'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-semibold text-white">D+{index}</span>
                      <span className="text-[10px]" style={{ color: meta.color }}>
                        {meta.label}
                      </span>
                    </div>
                    <div className="flex h-12 items-end">
                      <div className="w-full rounded-sm" style={{ height, background: meta.color }} />
                    </div>
                    <div className="font-data-mono text-xs text-slate-300">{formatNumber(step.pollen_total)}</div>
                  </button>
                );
              })}
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}

function Panel({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="rounded-lg border border-white/10 bg-slate-950/82 p-4 shadow-2xl backdrop-blur-md">
      <h2 className="mb-3 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">{title}</h2>
      {children}
    </div>
  );
}

function StatusLine({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div className="flex items-start gap-3">
      <span className="material-symbols-outlined mt-0.5 text-base text-cyan-300">{icon}</span>
      <div className="min-w-0">
        <p className="text-[10px] uppercase tracking-[0.18em] text-slate-500">{label}</p>
        <p className="break-words text-xs text-slate-200">{value}</p>
      </div>
    </div>
  );
}

function Metric({ icon, label, value }: { icon: string; label: string; value: string }) {
  return (
    <div className="rounded border border-white/10 bg-white/5 p-3">
      <div className="mb-2 flex items-center gap-2 text-slate-400">
        <span className="material-symbols-outlined text-base">{icon}</span>
        <span className="text-[10px] uppercase tracking-[0.16em]">{label}</span>
      </div>
      <p className="truncate text-sm font-semibold text-white">{value}</p>
    </div>
  );
}

function CompactStat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-white/10 bg-white/5 px-2 py-1.5">
      <p className="text-[10px] text-slate-500">{label}</p>
      <p className="font-data-mono text-xs text-white">{value}</p>
    </div>
  );
}

function isCityForecastProduct(product: ForecastProduct) {
  const type = product.product_type.toLowerCase();
  const path = product.file_path.toLowerCase();
  return type.includes('city_forecast') || path.endsWith('city_forecast.json');
}

function isInlineMapProduct(product: ForecastProduct) {
  const type = product.product_type.toLowerCase();
  const path = product.file_path.toLowerCase();
  return type.includes('geojson') || path.endsWith('.geojson');
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
  metadata: unknown,
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

function riskMeta(risk: string | undefined) {
  return RISK_META[risk ?? 'unknown'] ?? RISK_META.unknown;
}

function formatSpecies(step: CityForecastStep) {
  const index = step.dominant_species_index;
  if (typeof index === 'number' && SPECIES_LABELS[Math.round(index)]) {
    return SPECIES_LABELS[Math.round(index)];
  }
  return step.dominant_species ?? '--';
}

function formatNumber(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    return '--';
  }
  if (Math.abs(value) >= 1000) {
    return Math.round(value).toLocaleString();
  }
  if (Math.abs(value) >= 100) {
    return value.toFixed(0);
  }
  return value.toFixed(1);
}

function formatUnit(value: number | null | undefined, unit: string) {
  const formatted = formatNumber(value);
  return formatted === '--' ? '--' : `${formatted} ${unit}`;
}

function safeNumber(value: number | null | undefined) {
  return typeof value === 'number' && Number.isFinite(value) ? value : 0;
}

function clampIndex(index: number, length: number) {
  return Math.max(0, Math.min(index, Math.max(0, length - 1)));
}

function maxForecastValue(steps: CityForecastStep[]) {
  return Math.max(0, ...steps.map((step) => safeNumber(step.pollen_total)));
}

function fallbackStep(city: (typeof fallbackCities)[number]): CityForecastStep {
  return {
    time_index: 0,
    forecast_day: 1,
    lead_hours: 0,
    pollen_total: city.concentration,
    risk: city.risk,
    dominant_species_index: null,
    dominant_species: null,
    t2_c: null,
    wind10_ms: null,
    precip_step_mm: null,
    precip_accum_mm: null,
  };
}

function fallbackTimeline(city: (typeof fallbackCities)[number]) {
  const base = fallbackStep(city);
  return Array.from({ length: 7 }, (_, index) => ({
    ...base,
    time_index: index,
    forecast_day: index + 1,
    lead_hours: index * 24,
    pollen_total: Math.max(0, city.concentration * (0.82 + index * 0.04)),
  }));
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

function isOverlayMetadata(value: unknown): value is PngOverlayMetadata {
  const candidate = value as PngOverlayMetadata;
  return (
    candidate?.type === 'png_overlay' &&
    typeof candidate?.image?.name === 'string' &&
    typeof candidate?.bounds?.west === 'number' &&
    typeof candidate?.bounds?.south === 'number' &&
    typeof candidate?.bounds?.east === 'number' &&
    typeof candidate?.bounds?.north === 'number'
  );
}

interface CityForecastPayload {
  type: 'city_forecast';
  source: string;
  generated_at: string;
  variables: string[];
  cities: CityForecastCity[];
}

interface CityForecastCity {
  name: string;
  longitude: number;
  latitude: number;
  forecast: CityForecastStep[];
}

interface CityForecastStep {
  time_index: number;
  forecast_day: number;
  lead_hours: number;
  pollen_total: number | null;
  risk: string;
  dominant_species_index?: number | null;
  dominant_species?: string | null;
  t2_c?: number | null;
  wind10_ms?: number | null;
  precip_step_mm?: number | null;
  precip_accum_mm?: number | null;
}

function isCityForecastPayload(value: unknown): value is CityForecastPayload {
  const candidate = value as CityForecastPayload;
  return (
    candidate?.type === 'city_forecast' &&
    Array.isArray(candidate?.cities) &&
    candidate.cities.every(
      (city) =>
        typeof city?.name === 'string' &&
        typeof city?.longitude === 'number' &&
        typeof city?.latitude === 'number' &&
        Array.isArray(city?.forecast),
    )
  );
}
