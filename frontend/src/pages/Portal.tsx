import { useEffect, useMemo, useState, type ReactNode } from 'react';
import CesiumMap, { type MapProductLayer } from '../components/CesiumMap';
import { cities as fallbackCities } from '../data/chinaMap';
import { useThemeMode, type ThemeMode } from '../hooks/useThemeMode';
import { LanguageSelector, type Locale, useI18n } from '../i18n';
import { productsApi } from '../services/api';
import type { ForecastProduct } from '../types';

const DEFAULT_SERVER_SUBPATH = 'spring/beijing/2026/0621';

const PORTAL_REGIONS = [
  { key: 'beijing', code: 'Beijing', label: '北京' },
  { key: 'innermg', code: 'InnerMG', label: '内蒙古' },
  { key: 'shaanxi', code: 'Shaanxi', label: '陕西' },
  { key: 'yulin', code: 'Yulin', label: '榆林' },
  { key: 'china', code: 'China', label: '全国' },
] as const;

const SPECIES_LABELS: Record<Locale, Record<number, string>> = {
  en: {
    1: 'Evergreen conifer',
    2: 'Poplar / willow',
    3: 'Oak',
    4: 'Elm',
    5: 'Birch',
    6: 'Larch',
    7: 'Grass',
    8: 'Artemisia',
    9: 'Chenopodiaceae',
  },
  'zh-CN': {
    1: '常绿针叶',
    2: '杨柳',
    3: '栎树',
    4: '榆树',
    5: '白桦',
    6: '落叶松',
    7: '禾本科',
    8: '蒿属',
    9: '藜科',
  },
  'zh-TW': {
    1: '常綠針葉',
    2: '楊柳',
    3: '櫟樹',
    4: '榆樹',
    5: '白樺',
    6: '落葉松',
    7: '禾本科',
    8: '蒿屬',
    9: '藜科',
  },
};

const RISK_STYLE: Record<string, { color: string; bg: string; rank: number }> = {
  low: { color: '#50e167', bg: 'rgba(80,225,103,0.16)', rank: 1 },
  medium: { color: '#00f1fe', bg: 'rgba(0,241,254,0.16)', rank: 2 },
  high: { color: '#ff8a80', bg: 'rgba(255,138,128,0.18)', rank: 3 },
  critical: { color: '#ffb4ab', bg: 'rgba(255,180,171,0.22)', rank: 4 },
  unknown: { color: '#8c90a1', bg: 'rgba(140,144,161,0.14)', rank: 0 },
};

interface ProductBundle {
  key: string;
  runId: string;
  region: string;
  regionKey: string;
  subpath?: string;
  label: string;
  releaseTime: string;
  products: ForecastProduct[];
  cityProduct?: ForecastProduct;
  animationMapProduct?: ForecastProduct;
  forecastMapProduct?: ForecastProduct;
  inlineMapProduct?: ForecastProduct;
}

interface LatestServerBundle {
  region: string;
  region_key: string;
  season: string;
  subpath: string;
  day: string;
  release_time?: string;
  products: ForecastProduct[];
}

export default function Portal() {
  const { theme, switchTheme } = useThemeMode();
  const { locale, t } = useI18n();
  const [productLayer, setProductLayer] = useState<MapProductLayer | null>(null);
  const [cityForecast, setCityForecast] = useState<CityForecastPayload | null>(null);
  const [forecastMapAnimationPayload, setForecastMapAnimationPayload] = useState<PollenMapAnimationPayload | null>(null);
  const [forecastMapPayload, setForecastMapPayload] = useState<PollenMapForecastPayload | null>(null);
  const [productBundles, setProductBundles] = useState<ProductBundle[]>([]);
  const [activeRegionKey, setActiveRegionKey] = useState<string>(PORTAL_REGIONS[0].key);
  const [activeBundleKey, setActiveBundleKey] = useState('');
  const [query, setQuery] = useState('');
  const [selectedCityName, setSelectedCityName] = useState(fallbackCities[0]?.name ?? '');
  const [selectedDayIndex, setSelectedDayIndex] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;

    const loadProductCatalog = async () => {
      setIsLoading(true);
      try {
        const latestResponse = await productsApi.latestServerBundles();
        const latestBundles = normalizeLatestServerBundles(latestResponse.data?.bundles, locale);
        let bundles = latestBundles;
        if (bundles.length === 0) {
          let response = await productsApi.getAll({ status: 'ready', limit: 80 });
          let products = response.data as ForecastProduct[];
          if (products.length === 0) {
            response = await productsApi.getAll({ status: 'ready', limit: 80, subpath: DEFAULT_SERVER_SUBPATH });
            products = response.data as ForecastProduct[];
          }
          bundles = buildProductBundles(products, locale);
        }
        if (cancelled) return;
        setProductBundles(bundles);
        setActiveRegionKey((current) => {
          if (bundles.some((bundle) => bundle.regionKey === current)) return current;
          return bundles[0]?.regionKey ?? PORTAL_REGIONS[0].key;
        });
        setActiveBundleKey((current) => {
          if (bundles.some((bundle) => bundle.key === current)) return current;
          return bundles[0]?.key ?? '';
        });
        if (bundles.length === 0) {
          setProductLayer(null);
          setCityForecast(null);
        }
      } catch (error) {
        console.warn('Latest pollen products are unavailable:', error);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    void loadProductCatalog();
    return () => {
      cancelled = true;
    };
  }, [locale, t]);

  const regionBundles = useMemo(
    () => productBundles.filter((bundle) => bundle.regionKey === activeRegionKey),
    [activeRegionKey, productBundles],
  );
  const activeBundle = useMemo(
    () => regionBundles.find((bundle) => bundle.key === activeBundleKey) ?? regionBundles[0] ?? productBundles[0],
    [activeBundleKey, productBundles, regionBundles],
  );

  useEffect(() => {
    if (!regionBundles.length) return;
    setActiveBundleKey((current) => {
      if (regionBundles.some((bundle) => bundle.key === current)) return current;
      return regionBundles[0]?.key ?? '';
    });
  }, [regionBundles]);

  useEffect(() => {
    if (!activeBundle) return;
    let cancelled = false;

    const loadBundleProducts = async () => {
      setIsLoading(true);
      setProductLayer(null);
      setCityForecast(null);
      setForecastMapAnimationPayload(null);
      setForecastMapPayload(null);
      setSelectedDayIndex(0);
      try {
        if (activeBundle.cityProduct) {
          const payload = await loadProductJson(activeBundle.cityProduct);
          if (!cancelled && isCityForecastPayload(payload)) {
            setCityForecast(payload);
            setSelectedDayIndex(firstSignalDayIndex(payload));
            const firstCity = payload.cities[0];
            if (firstCity) {
              setSelectedCityName((current) =>
                payload.cities.some((city) => city.name === current) ? current : firstCity.name,
              );
            }
          }
        }

        if (activeBundle.animationMapProduct) {
          const payload = await loadProductJson(activeBundle.animationMapProduct);
          if (!cancelled && isPollenMapAnimationPayload(payload)) {
            setForecastMapAnimationPayload(payload);
            return;
          }
        }

        if (activeBundle.forecastMapProduct) {
          const payload = await loadProductJson(activeBundle.forecastMapProduct);
          if (!cancelled && isPollenMapForecastPayload(payload)) {
            setForecastMapPayload(payload);
            return;
          }
        }

        if (activeBundle.inlineMapProduct) {
          const geojson = await loadProductJson(activeBundle.inlineMapProduct);
          if (cancelled) return;
          setProductLayer({ kind: 'geojson', name: activeBundle.inlineMapProduct.product_name, geojson });
          return;
        }
      } catch (error) {
        console.warn('Selected pollen products are unavailable:', error);
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };

    void loadBundleProducts();
    return () => {
      cancelled = true;
    };
  }, [activeBundle, t]);

  const dailyAnimationFrames = useMemo(
    () => (forecastMapAnimationPayload ? pickDailyAnimationFrames(forecastMapAnimationPayload.frames) : []),
    [forecastMapAnimationPayload],
  );
  const dailyMapFrames = useMemo(
    () => (forecastMapPayload ? pickDailyMapFrames(forecastMapPayload.frames) : []),
    [forecastMapPayload],
  );

  useEffect(() => {
    if (dailyAnimationFrames.length && activeBundle) {
      const dayIndex = clampIndex(selectedDayIndex, dailyAnimationFrames.length);
      const frame = dailyAnimationFrames[dayIndex] ?? dailyAnimationFrames[0];
      const bounds = frame.bounds ?? forecastMapAnimationPayload?.bounds;
      if (!frame?.image_path || !bounds) return;
      setProductLayer({
        kind: 'image_overlay',
        name: `${forecastMapAnimationPayload?.variable ?? 'pollen'}-d${frame.forecast_day}`,
        imageUrl: buildBundleAssetUrl(activeBundle, frame.image_path, forecastMapAnimationPayload?.generated_at),
        bounds,
        opacity: frame.opacity ?? forecastMapAnimationPayload?.color_scale?.opacity ?? 0.75,
      });
      return;
    }
    if (!dailyMapFrames.length) return;
    const dayIndex = clampIndex(selectedDayIndex, dailyMapFrames.length);
    const frame = dailyMapFrames[dayIndex] ?? dailyMapFrames[0];
    if (!frame?.geojson) return;
    setProductLayer({
      kind: 'geojson',
      name: `${forecastMapPayload?.variable ?? 'pollen'}-d${frame.forecast_day}`,
      geojson: frame.geojson,
    });
  }, [
    activeBundle,
    dailyAnimationFrames,
    dailyMapFrames,
    forecastMapAnimationPayload?.bounds,
    forecastMapAnimationPayload?.color_scale?.opacity,
    forecastMapAnimationPayload?.variable,
    forecastMapPayload?.variable,
    selectedDayIndex,
  ]);

  const forecastCities = useMemo(() => cityForecast?.cities ?? [], [cityForecast]);
  const hasForecast = forecastCities.length > 0;
  const selectedCity = useMemo(
    () => forecastCities.find((city) => city.name === selectedCityName) ?? forecastCities[0],
    [forecastCities, selectedCityName],
  );
  const selectedFallbackCity = useMemo(
    () => fallbackCities.find((city) => city.name === selectedCityName) ?? fallbackCities[0],
    [selectedCityName],
  );
  const cityDailyTimeline = useMemo(
    () => (selectedCity?.forecast?.length ? collapseForecastToDailySteps(selectedCity.forecast) : []),
    [selectedCity],
  );
  const animationPeakTimeline = useMemo(
    () => (dailyAnimationFrames.length ? buildAnimationPeakTimeline(dailyAnimationFrames) : []),
    [dailyAnimationFrames],
  );
  const mapSampleTimeline = useMemo(() => {
    if (!dailyMapFrames.length) return [];
    const lon = selectedCity?.longitude ?? selectedFallbackCity.longitude;
    const lat = selectedCity?.latitude ?? selectedFallbackCity.latitude;
    return buildMapSampleTimeline(dailyMapFrames, lon, lat);
  }, [dailyMapFrames, selectedCity, selectedFallbackCity]);
  const mapPeakTimeline = useMemo(
    () => (dailyMapFrames.length ? buildMapDomainPeakTimeline(dailyMapFrames) : []),
    [dailyMapFrames],
  );
  const cityPollenFlat = cityDailyTimeline.length > 0 && maxForecastValue(cityDailyTimeline) === 0;
  const useMapPeakTimeline =
    cityPollenFlat && mapPeakTimeline.length > 0 && maxForecastValue(mapPeakTimeline) > 0;
  const useMapSampleTimeline =
    cityPollenFlat && !useMapPeakTimeline && mapSampleTimeline.length > 0 && maxForecastValue(mapSampleTimeline) > 0;
  const timeline = animationPeakTimeline.length > 0
    ? animationPeakTimeline
    : useMapPeakTimeline
      ? mapPeakTimeline
      : useMapSampleTimeline
        ? mapSampleTimeline
        : cityDailyTimeline.length > 0
          ? cityDailyTimeline
          : fallbackTimeline(selectedFallbackCity);
  const activeDayIndex = clampIndex(selectedDayIndex, timeline.length || 1);
  const rawActiveStep = timeline[activeDayIndex] ?? fallbackStep(selectedFallbackCity);
  const activeStep = mergeTimelineDisplayStep(
    rawActiveStep,
    cityDailyTimeline.find((step) => step.forecast_day === rawActiveStep.forecast_day) ?? cityDailyTimeline[activeDayIndex],
  );
  const cityOptions = useMemo(() => {
    const source = hasForecast
      ? forecastCities.map((city) => ({ name: city.name, longitude: city.longitude, latitude: city.latitude }))
      : fallbackCities.map((city) => ({ name: city.name, longitude: city.longitude, latitude: city.latitude }));
    const normalized = query.trim().toLowerCase();
    if (!normalized) return source.slice(0, 12);
    return source.filter((city) => city.name.toLowerCase().includes(normalized)).slice(0, 12);
  }, [forecastCities, hasForecast, query]);
  const mapCities = useMemo(
    () =>
      hasForecast
        ? forecastCities.map((city) => {
            const daily = collapseForecastToDailySteps(city.forecast);
            const step = daily[activeDayIndex] ?? daily[0];
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
  const risk = riskMeta(activeStep.risk, t);
  const peak = maxForecastValue(timeline);
  const dominantSpecies = formatSpecies(activeStep, locale);
  const readinessLabel = isLoading ? t('loading') : productBundles.length > 0 ? t('productReady') : t('sampleMode');

  useEffect(() => {
    if (!isPlaying) return;
    const timer = window.setInterval(() => {
      setSelectedDayIndex((current) => (current + 1) % Math.max(1, timeline.length));
    }, 1200);
    return () => window.clearInterval(timer);
  }, [isPlaying, timeline]);

  return (
    <div data-theme={theme} className="min-h-screen bg-background text-on-background font-body-md">
      <header className="fixed top-0 z-50 flex h-14 w-full items-center justify-between border-b border-outline-variant bg-surface-container-lowest/95 px-5 backdrop-blur-md">
        <div className="flex min-w-0 flex-col">
          <span className="truncate text-base font-black uppercase tracking-wide text-on-surface">{t('appName')}</span>
          <span className="hidden text-[10px] font-medium uppercase tracking-[0.18em] text-on-surface-variant sm:block">
            {t('portalSubtitle')}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="hidden w-40 sm:block">
            <LanguageSelector compact />
          </div>
          <ThemeSwitch theme={theme} onChange={switchTheme} />
          <div className="hidden items-center gap-2 rounded border border-outline-variant bg-surface-container-high px-3 py-1.5 text-[11px] text-on-surface-variant md:flex">
            <span className={`h-2 w-2 rounded-full ${isLoading ? 'bg-amber-300' : 'bg-tertiary'}`} />
            <span>{readinessLabel}</span>
          </div>
          <a
            href="/login"
            className="rounded bg-primary-container px-3 py-1.5 text-sm font-semibold text-on-primary-container shadow-lg shadow-black/20 transition-colors hover:bg-primary-container/80"
          >
            {t('portalAdmin')}
          </a>
        </div>
      </header>

      <main className="relative mt-14 h-[calc(100vh-3.5rem)] overflow-hidden bg-background">
        <CesiumMap
          cities={mapCities}
          productLayer={productLayer}
          selectedCityName={selectedCityName}
          cityMarkerMode={dailyAnimationFrames.length ? 'compact' : 'concentration'}
          onCitySelect={(cityName) => {
            setSelectedCityName(cityName);
            setQuery('');
          }}
        />
        <div className="pointer-events-none absolute inset-0 border border-white/5" />

        <section className="absolute left-4 top-4 z-20 hidden w-72 flex-col gap-3 lg:flex">
          <Panel title={t('layers')}>
            <div className="space-y-3">
              <div>
                <span className="mb-1 block text-[10px] uppercase tracking-[0.18em] text-slate-500">Region</span>
                <div className="grid grid-cols-2 gap-2">
                  {PORTAL_REGIONS.map((region) => {
                    const available = productBundles.some((bundle) => bundle.regionKey === region.key);
                    const active = activeRegionKey === region.key;
                    return (
                      <button
                        key={region.key}
                        type="button"
                        onClick={() => setActiveRegionKey(region.key)}
                        disabled={!available}
                        className={`rounded border px-2 py-2 text-left text-xs font-semibold transition-colors ${
                          active
                            ? 'border-cyan-300/70 bg-cyan-300/15 text-white'
                            : available
                              ? 'border-outline-variant bg-surface-container-high text-on-surface-variant hover:border-white/25'
                              : 'border-white/5 bg-surface-container-low text-slate-600'
                        }`}
                      >
                        {region.label}
                      </button>
                    );
                  })}
                </div>
              </div>
              {productBundles.length > 0 ? (
                <label className="block">
                  <span className="mb-1 block text-[10px] uppercase tracking-[0.18em] text-slate-500">{t('forecastProduct')}</span>
                  <select
                    value={activeBundle?.key ?? ''}
                    onChange={(event) => setActiveBundleKey(event.target.value)}
                    className="w-full rounded border border-outline-variant bg-surface-container-high px-2 py-2 text-xs text-on-surface outline-none focus:border-secondary-container/60"
                  >
                    {(regionBundles.length ? regionBundles : productBundles).map((bundle) => (
                      <option key={bundle.key} value={bundle.key} className="bg-surface text-on-surface">
                        {bundle.label}
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
            </div>
          </Panel>
          <Panel title={t('colorRamp')}>
            <div
              className="h-3 rounded"
              style={{
                background:
                  'linear-gradient(90deg, #2563eb 0%, #22c55e 34%, #fde047 62%, #fb923c 80%, #dc2626 100%)',
              }}
            />
            <div className="mt-2 flex justify-between text-[10px] text-slate-400">
              <span>{t('low')}</span>
              <span>{t('medium')}</span>
              <span>{t('high')}</span>
              <span>{t('critical')}</span>
            </div>
          </Panel>
        </section>

        <section className="absolute bottom-32 right-4 top-4 z-20 hidden w-[360px] flex-col gap-3 overflow-y-auto xl:flex">
          <Panel title={t('citySearch')}>
            <div className="relative">
              <span className="material-symbols-outlined pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-base text-slate-500">
                search
              </span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                className="w-full rounded border border-white/10 bg-white/5 py-2 pl-9 pr-3 text-sm text-white outline-none transition-colors placeholder:text-slate-500 focus:border-cyan-300/60"
                placeholder={t('searchCity')}
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
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{t('risk')}</p>
                <div className="mt-1 flex items-center gap-2">
                  <span className="rounded px-2 py-1 text-sm font-bold" style={{ color: risk.color, background: risk.bg }}>
                    {risk.label}
                  </span>
                  <span className="text-xs text-slate-400">{formatTimelineDate(activeStep, activeBundle, locale)}</span>
                </div>
              </div>
              <div className="text-right">
                <p className="text-[11px] uppercase tracking-[0.18em] text-slate-500">{t('pollen')}</p>
                <p className="font-data-mono text-2xl text-white">{formatNumber(activeStep.pollen_total)}</p>
                <p className="text-[10px] text-slate-500">grains/kg-dryair</p>
              </div>
            </div>

            <div className="mt-4 grid grid-cols-2 gap-2">
              <Metric icon="thermostat" label={t('temperature')} value={formatUnit(activeStep.t2_c, '°C')} />
              <Metric icon="air" label={t('windSpeed')} value={formatUnit(activeStep.wind10_ms, 'm/s')} />
              <Metric icon="water_drop" label={t('precipitation')} value={formatUnit(activeStep.precip_step_mm, 'mm')} />
              <Metric icon="eco" label={t('dominantSpecies')} value={dominantSpecies} />
            </div>
          </Panel>
        </section>

        <section className="absolute bottom-4 left-4 right-4 z-20">
          <div className="grid gap-3 rounded-lg border border-outline-variant bg-surface-container-lowest/88 p-3 shadow-2xl backdrop-blur-md lg:grid-cols-[minmax(260px,360px)_1fr]">
            <div className="min-w-0">
              <div className="flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-white">{selectedCity?.name ?? selectedFallbackCity.name}</p>
                  <p className="truncate text-[11px] text-slate-400">{hasForecast ? t('cityForecastProduct') : t('sampleCityPoint')}</p>
                </div>
                <span className="rounded px-2 py-1 text-xs font-bold" style={{ color: risk.color, background: risk.bg }}>
                  {risk.label}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setIsPlaying((current) => !current)}
                className="mt-3 inline-flex items-center gap-2 rounded border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-200 transition-colors hover:border-white/25"
              >
                <span className="material-symbols-outlined text-sm">{isPlaying ? 'pause' : 'play_arrow'}</span>
                {isPlaying ? t('pauseTimeline') : t('playTimeline')}
              </button>
              <div className="mt-3 grid grid-cols-4 gap-2 text-center">
                <CompactStat label={t('pollen')} value={formatNumber(activeStep.pollen_total)} />
                <CompactStat label={t('temperature')} value={formatNumber(activeStep.t2_c)} />
                <CompactStat label={t('windSpeed')} value={formatNumber(activeStep.wind10_ms)} />
                <CompactStat label={t('precipitation')} value={formatNumber(activeStep.precip_step_mm)} />
              </div>
            </div>

            <div className="grid grid-cols-7 gap-2">
              {timeline.map((step, index) => {
                const meta = riskMeta(step.risk, t);
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
                      <span className="text-xs font-semibold text-white">{formatTimelineDate(step, activeBundle, locale)}</span>
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
    <div className="rounded-lg border border-outline-variant bg-surface-container-lowest/82 p-4 shadow-2xl backdrop-blur-md">
      <h2 className="mb-3 text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">{title}</h2>
      {children}
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
      <p className="truncate text-[10px] text-slate-500">{label}</p>
      <p className="font-data-mono text-xs text-white">{value}</p>
    </div>
  );
}

function ThemeSwitch({ theme, onChange }: { theme: ThemeMode; onChange: (theme: ThemeMode) => void }) {
  const { t } = useI18n();
  return (
    <div className="flex h-8 items-center rounded border border-outline-variant bg-surface-container-high p-1">
      {(['research', 'pig'] as ThemeMode[]).map((mode) => (
        <button
          key={mode}
          type="button"
          onClick={() => onChange(mode)}
          aria-pressed={theme === mode}
          className={`min-w-[48px] rounded px-2 py-1 text-[11px] font-semibold transition-colors ${
            theme === mode ? 'bg-primary-container text-on-primary-container' : 'text-on-surface-variant hover:text-on-surface'
          }`}
        >
          {mode === 'research' ? t('themeResearch') : t('themePig')}
        </button>
      ))}
    </div>
  );
}

function loadProductJson(product: ForecastProduct) {
  if (product.id != null) {
    return productsApi.content(product.id).then((response) => response.data);
  }
  if (product.server_path) {
    return productsApi.serverContent(product.server_path).then((response) => response.data);
  }
  return Promise.resolve(null);
}

function buildBundleAssetUrl(bundle: ProductBundle, relativePath: string, cacheKey?: string) {
  const cleanPath = relativePath.replace(/^\/+/, '');
  if (!bundle.subpath) return cleanPath;
  const url = productsApi.serverDownloadUrl(`${bundle.subpath}/${cleanPath}`);
  if (!cacheKey) return url;
  const separator = url.includes('?') ? '&' : '?';
  return `${url}${separator}v=${encodeURIComponent(cacheKey)}`;
}

function normalizeLatestServerBundles(value: unknown, locale: Locale): ProductBundle[] {
  if (!Array.isArray(value)) return [];
  return value
    .filter(isLatestServerBundle)
    .map((bundle) => {
      const sorted = [...bundle.products].sort(compareProductTimeDesc);
      const key = bundle.subpath;
      return {
        key,
        runId: key,
        region: bundle.region,
        regionKey: normalizeRegionKey(bundle.region_key || bundle.region),
        subpath: bundle.subpath,
        label: formatBundleLabel(key, sorted, locale),
        releaseTime: bundle.release_time || sorted[0]?.release_time || '',
        products: sorted,
        cityProduct: sorted.find(isCityForecastProduct),
        animationMapProduct: sorted.find(isAnimationMapProduct),
        forecastMapProduct: sorted.find(isForecastMapProduct),
        inlineMapProduct: sorted.find(isInlineMapProduct),
      };
    })
    .filter((bundle) => bundle.cityProduct || bundle.animationMapProduct || bundle.forecastMapProduct || bundle.inlineMapProduct)
    .sort((a, b) => compareNullableTimeDesc(a.releaseTime, b.releaseTime));
}

function isLatestServerBundle(value: unknown): value is LatestServerBundle {
  const candidate = value as LatestServerBundle;
  return (
    typeof candidate?.region === 'string' &&
    typeof candidate?.region_key === 'string' &&
    typeof candidate?.subpath === 'string' &&
    Array.isArray(candidate?.products)
  );
}

function buildProductBundles(products: ForecastProduct[], locale: Locale): ProductBundle[] {
  const groups = new Map<string, ForecastProduct[]>();
  products
    .filter((product) => isCityForecastProduct(product) || isAnimationMapProduct(product) || isForecastMapProduct(product) || isInlineMapProduct(product))
    .forEach((product) => {
      const key = productRunKey(product);
      groups.set(key, [...(groups.get(key) ?? []), product]);
    });

  return Array.from(groups.entries())
    .map(([key, items]) => {
      const sorted = [...items].sort(compareProductTimeDesc);
      return {
        key,
        runId: key,
        region: sorted[0]?.region ?? '',
        regionKey: normalizeRegionKey(sorted[0]?.region ?? key.split('/')[1] ?? ''),
        label: formatBundleLabel(key, sorted, locale),
        releaseTime: sorted[0]?.release_time ?? '',
        products: sorted,
        cityProduct: sorted.find(isCityForecastProduct),
        animationMapProduct: sorted.find(isAnimationMapProduct),
        forecastMapProduct: sorted.find(isForecastMapProduct),
        inlineMapProduct: sorted.find(isInlineMapProduct),
      };
    })
    .filter((bundle) => bundle.cityProduct || bundle.animationMapProduct || bundle.forecastMapProduct || bundle.inlineMapProduct)
    .sort((a, b) => compareNullableTimeDesc(a.releaseTime, b.releaseTime));
}

function normalizeRegionKey(value: string) {
  const normalized = value.toLowerCase().replace(/[_\s-]/g, '');
  if (normalized === 'innermg' || normalized === 'inner mongolia') return 'innermg';
  return normalized;
}

function productRunKey(product: ForecastProduct) {
  const separator = product.product_name.indexOf(':');
  if (separator > 0) return product.product_name.slice(0, separator);
  return product.workflow_version || `product-${product.id}`;
}

function formatBundleLabel(runId: string, products: ForecastProduct[], locale: Locale) {
  const releaseTime = products[0]?.release_time;
  if (!releaseTime) return runId;
  const date = new Date(releaseTime);
  if (Number.isNaN(date.getTime())) return runId;
  return `${runId} / ${date.toLocaleString(locale, { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })}`;
}

function compareProductTimeDesc(a: ForecastProduct, b: ForecastProduct) {
  return compareNullableTimeDesc(a.release_time, b.release_time);
}

function compareNullableTimeDesc(a?: string | null, b?: string | null) {
  return Date.parse(b ?? '') - Date.parse(a ?? '');
}

function isCityForecastProduct(product: ForecastProduct) {
  const type = product.product_type.toLowerCase();
  const path = product.file_path.toLowerCase();
  return type.includes('city_forecast') || path.endsWith('city_forecast.json');
}

function isForecastMapProduct(product: ForecastProduct) {
  const type = product.product_type.toLowerCase();
  const path = product.file_path.toLowerCase();
  return type.includes('pollen_map_forecast') || path.endsWith('pollen_map_forecast.json');
}

function isAnimationMapProduct(product: ForecastProduct) {
  const type = product.product_type.toLowerCase();
  const path = product.file_path.toLowerCase();
  return type.includes('pollen_map_animation') || path.endsWith('pollen_map_animation.json');
}

function isInlineMapProduct(product: ForecastProduct) {
  if (isCityForecastProduct(product) || isAnimationMapProduct(product) || isForecastMapProduct(product)) return false;
  const type = product.product_type.toLowerCase();
  const path = product.file_path.toLowerCase();
  return type.includes('geojson') || path.endsWith('.geojson');
}

function mergeTimelineDisplayStep(primary: CityForecastStep, cityStep?: CityForecastStep): CityForecastStep {
  if (!cityStep) return primary;
  return {
    ...primary,
    t2_c: primary.t2_c ?? cityStep.t2_c ?? null,
    wind10_ms: primary.wind10_ms ?? cityStep.wind10_ms ?? null,
    precip_step_mm: primary.precip_step_mm ?? cityStep.precip_step_mm ?? null,
    precip_accum_mm: primary.precip_accum_mm ?? cityStep.precip_accum_mm ?? null,
    dominant_species_index: primary.dominant_species_index ?? cityStep.dominant_species_index ?? null,
    dominant_species: primary.dominant_species ?? cityStep.dominant_species ?? null,
  };
}

function riskMeta(risk: string | undefined, t: (key: string) => string) {
  const key = risk ?? 'unknown';
  const style = RISK_STYLE[key] ?? RISK_STYLE.unknown;
  return { ...style, label: t(key) };
}

function formatSpecies(step: CityForecastStep, locale: Locale) {
  const index = step.dominant_species_index;
  if (typeof index === 'number' && SPECIES_LABELS[locale][Math.round(index)]) {
    return SPECIES_LABELS[locale][Math.round(index)];
  }
  return step.dominant_species ?? '--';
}

function formatNumber(value: number | null | undefined) {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '--';
  if (Math.abs(value) >= 1000) return Math.round(value).toLocaleString();
  if (Math.abs(value) >= 100) return value.toFixed(0);
  return value.toFixed(1);
}

function formatTimelineDate(step: CityForecastStep, bundle: ProductBundle | undefined, locale: Locale) {
  const date = dateFromStep(step, bundle);
  if (!date) return `D+${Math.max(0, step.forecast_day - 1)}`;
  return new Intl.DateTimeFormat(locale, {
    month: 'numeric',
    day: 'numeric',
  }).format(date);
}

function dateFromStep(step: CityForecastStep, bundle: ProductBundle | undefined) {
  if (step.valid_time) {
    const parsed = new Date(step.valid_time);
    if (!Number.isNaN(parsed.getTime())) return parsed;
  }
  const parts = bundle?.subpath?.split('/') ?? [];
  const year = Number(parts[2]);
  const day = parts[3] ?? '';
  if (!Number.isFinite(year) || !/^\d{4}$/.test(day)) return null;
  const month = Number(day.slice(0, 2));
  const date = Number(day.slice(2, 4));
  if (!month || !date) return null;
  return new Date(year, month - 1, date + Math.max(0, step.forecast_day - 1));
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

interface PollenMapForecastPayload {
  type: 'pollen_map_forecast';
  variable?: string;
  unit?: string;
  generated_at?: string;
  frames: PollenMapForecastFrame[];
}

interface PollenMapAnimationPayload {
  type: 'pollen_map_animation';
  variable?: string;
  unit?: string;
  generated_at?: string;
  bounds?: MapFrameBounds;
  color_scale?: {
    opacity?: number;
  };
  frames: PollenMapAnimationFrame[];
}

interface PollenMapAnimationFrame {
  forecast_day: number;
  lead_hours: number;
  time_index: number;
  valid_time?: string;
  image_path: string;
  bounds?: MapFrameBounds;
  max_value?: number;
  opacity?: number;
}

interface MapFrameBounds {
  west: number;
  south: number;
  east: number;
  north: number;
}

interface PollenMapForecastFrame {
  forecast_day: number;
  lead_hours: number;
  time_index: number;
  valid_time?: string;
  geojson: Record<string, unknown>;
}

function isPollenMapAnimationPayload(value: unknown): value is PollenMapAnimationPayload {
  const candidate = value as PollenMapAnimationPayload;
  return (
    candidate?.type === 'pollen_map_animation' &&
    Array.isArray(candidate.frames) &&
    candidate.frames.length > 0 &&
    (!candidate.bounds || isMapFrameBounds(candidate.bounds)) &&
    candidate.frames.every(
      (frame) =>
        typeof frame?.forecast_day === 'number' &&
        typeof frame?.image_path === 'string' &&
        (!frame.bounds || isMapFrameBounds(frame.bounds)),
    )
  );
}

function isMapFrameBounds(value: unknown): value is MapFrameBounds {
  const candidate = value as MapFrameBounds;
  return (
    typeof candidate?.west === 'number' &&
    typeof candidate?.south === 'number' &&
    typeof candidate?.east === 'number' &&
    typeof candidate?.north === 'number'
  );
}

function isPollenMapForecastPayload(value: unknown): value is PollenMapForecastPayload {
  const candidate = value as PollenMapForecastPayload;
  return (
    candidate?.type === 'pollen_map_forecast' &&
    Array.isArray(candidate.frames) &&
    candidate.frames.length > 0 &&
    candidate.frames.every(
      (frame) =>
        typeof frame?.forecast_day === 'number' &&
        frame.geojson &&
        typeof frame.geojson === 'object',
    )
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
  valid_time?: string;
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

function firstSignalDayIndex(payload: CityForecastPayload) {
  for (const city of payload.cities) {
    const daily = collapseForecastToDailySteps(city.forecast);
    for (let index = 0; index < daily.length; index += 1) {
      if (safeNumber(daily[index]?.pollen_total) > 0) return index;
    }
  }
  return 0;
}

function collapseForecastToDailySteps(forecast: CityForecastStep[]): CityForecastStep[] {
  const grouped = new Map<number, CityForecastStep[]>();
  for (const step of forecast) {
    const bucket = grouped.get(step.forecast_day) ?? [];
    bucket.push(step);
    grouped.set(step.forecast_day, bucket);
  }
  return Array.from(grouped.entries())
    .sort(([left], [right]) => left - right)
    .slice(0, 7)
    .map(([, steps]) => {
      const peak = [...steps].sort((left, right) => safeNumber(right.pollen_total) - safeNumber(left.pollen_total))[0];
      if (safeNumber(peak?.pollen_total) > 0) return peak;
      const midday = steps.find((step) => step.lead_hours % 24 === 12);
      return midday ?? steps[steps.length - 1];
    });
}

function pickDailyAnimationFrames(frames: PollenMapAnimationFrame[]): PollenMapAnimationFrame[] {
  const grouped = new Map<number, PollenMapAnimationFrame[]>();
  for (const frame of frames) {
    const bucket = grouped.get(frame.forecast_day) ?? [];
    bucket.push(frame);
    grouped.set(frame.forecast_day, bucket);
  }
  return Array.from(grouped.entries())
    .sort(([left], [right]) => left - right)
    .slice(0, 7)
    .map(([, dayFrames]) =>
      dayFrames.reduce((best, current) =>
        safeNumber(current.max_value) > safeNumber(best.max_value) ? current : best,
      ),
    );
}

function buildAnimationPeakTimeline(frames: PollenMapAnimationFrame[]): CityForecastStep[] {
  return frames.map((frame, index) => {
    const pollenTotal = safeNumber(frame.max_value);
    return {
      time_index: frame.time_index ?? index,
      forecast_day: frame.forecast_day,
      lead_hours: frame.lead_hours,
      valid_time: frame.valid_time,
      pollen_total: pollenTotal,
      risk: riskFromPollenValue(pollenTotal),
      dominant_species_index: null,
      dominant_species: null,
      t2_c: null,
      wind10_ms: null,
      precip_step_mm: null,
      precip_accum_mm: null,
    };
  });
}

function pickDailyMapFrames(frames: PollenMapForecastFrame[]): PollenMapForecastFrame[] {
  const grouped = new Map<number, PollenMapForecastFrame[]>();
  for (const frame of frames) {
    const bucket = grouped.get(frame.forecast_day) ?? [];
    bucket.push(frame);
    grouped.set(frame.forecast_day, bucket);
  }
  return Array.from(grouped.entries())
    .sort(([left], [right]) => left - right)
    .slice(0, 7)
    .map(([, dayFrames]) =>
      dayFrames.reduce((best, current) =>
        maxGeoJsonPollen(current.geojson) > maxGeoJsonPollen(best.geojson) ? current : best,
      ),
    );
}

function riskFromPollenValue(value: number) {
  if (value < 50) return 'low';
  if (value < 200) return 'medium';
  if (value < 500) return 'high';
  return 'critical';
}

function maxGeoJsonPollen(geojson: Record<string, unknown>): number {
  const features = (geojson as { features?: Array<{ properties?: Record<string, unknown> }> }).features ?? [];
  let peak = 0;
  for (const feature of features) {
    const value = feature.properties?.pollen_total;
    if (typeof value === 'number' && Number.isFinite(value)) {
      peak = Math.max(peak, value);
    }
  }
  return peak;
}

function buildMapDomainPeakTimeline(frames: PollenMapForecastFrame[]): CityForecastStep[] {
  return frames.map((frame, index) => {
    const peakFeature = findPeakGeoJsonFeature(frame.geojson);
    const properties = peakFeature?.properties ?? {};
    const pollenTotal = properties.pollen_total;
    const risk = properties.risk;
    const speciesIndex = properties.species_index;
    return {
      time_index: frame.time_index ?? index,
      forecast_day: frame.forecast_day,
      lead_hours: frame.lead_hours,
      valid_time: frame.valid_time,
      pollen_total: typeof pollenTotal === 'number' && Number.isFinite(pollenTotal) ? pollenTotal : 0,
      risk: typeof risk === 'string' ? risk : 'unknown',
      dominant_species_index: typeof speciesIndex === 'number' ? speciesIndex : null,
      dominant_species: null,
      t2_c: null,
      wind10_ms: null,
      precip_step_mm: null,
      precip_accum_mm: null,
    };
  });
}

function findPeakGeoJsonFeature(geojson: Record<string, unknown>) {
  const features =
    (geojson as { features?: Array<{ properties?: Record<string, unknown> }> }).features ?? [];
  let peakFeature = features[0];
  let peakValue = -1;
  for (const feature of features) {
    const value = feature.properties?.pollen_total;
    if (typeof value === 'number' && Number.isFinite(value) && value > peakValue) {
      peakValue = value;
      peakFeature = feature;
    }
  }
  return peakFeature;
}

function buildMapSampleTimeline(
  frames: PollenMapForecastFrame[],
  longitude: number,
  latitude: number,
): CityForecastStep[] {
  return frames.map((frame, index) => {
    const sample = sampleGeoJsonPoint(frame.geojson, longitude, latitude);
    return {
      time_index: frame.time_index ?? index,
      forecast_day: frame.forecast_day,
      lead_hours: frame.lead_hours,
      valid_time: frame.valid_time,
      pollen_total: sample?.pollen_total ?? 0,
      risk: sample?.risk ?? 'unknown',
      dominant_species_index: sample?.species_index ?? null,
      dominant_species: null,
      t2_c: null,
      wind10_ms: null,
      precip_step_mm: null,
      precip_accum_mm: null,
    };
  });
}

function sampleGeoJsonPoint(
  geojson: Record<string, unknown>,
  longitude: number,
  latitude: number,
): { pollen_total: number; risk: string; species_index: number | null } | null {
  const features =
    (geojson as { features?: Array<{ geometry?: { type?: string; coordinates?: number[] }; properties?: Record<string, unknown> }> })
      .features ?? [];
  if (!features.length) return null;

  let nearest = features[0];
  let nearestDistance = Number.POSITIVE_INFINITY;
  for (const feature of features) {
    const coordinates = feature.geometry?.coordinates;
    if (!Array.isArray(coordinates) || coordinates.length < 2) continue;
    const [lon, lat] = coordinates;
    if (typeof lon !== 'number' || typeof lat !== 'number') continue;
    const distance = (lon - longitude) ** 2 + (lat - latitude) ** 2;
    if (distance < nearestDistance) {
      nearestDistance = distance;
      nearest = feature;
    }
  }

  const properties = nearest.properties ?? {};
  const pollenTotal = properties.pollen_total;
  const risk = properties.risk;
  const speciesIndex = properties.species_index;
  return {
    pollen_total: typeof pollenTotal === 'number' && Number.isFinite(pollenTotal) ? pollenTotal : 0,
    risk: typeof risk === 'string' ? risk : 'unknown',
    species_index: typeof speciesIndex === 'number' ? speciesIndex : null,
  };
}
