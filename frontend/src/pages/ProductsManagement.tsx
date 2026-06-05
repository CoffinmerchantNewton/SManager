import { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation } from 'react-router-dom';
import { productsApi, runsApi } from '../services/api';
import type { ForecastProduct } from '../types/index';

export default function ProductsManagement() {
  const location = useLocation();
  const initialRunId = new URLSearchParams(location.search).get('run_id') ?? '';
  const [products, setProducts] = useState<ForecastProduct[]>([]);
  const [loading, setLoading] = useState(true);
  const [runId, setRunId] = useState(initialRunId);
  const [syncing, setSyncing] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [category, setCategory] = useState('all');

  const loadProducts = useCallback(async (targetRunId: string) => {
    const normalizedRunId = targetRunId.trim();
    try {
      setLoading(true);
      setErrorMessage(null);
      const response = await productsApi.getAll(normalizedRunId ? { run_id: normalizedRunId } : undefined);
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to load products:', error);
      setErrorMessage('Failed to load products.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadProducts(initialRunId);
  }, [initialRunId, loadProducts]);

  const togglePublish = async (productId: number, currentStatus: boolean) => {
    try {
      await productsApi.togglePublish(productId, !currentStatus);
      void loadProducts(runId);
    } catch (error) {
      console.error('Failed to toggle publish status:', error);
    }
  };

  const deleteProduct = async (productId: number) => {
    if (confirm('Are you sure you want to delete this product?')) {
      try {
        await productsApi.delete(productId);
        void loadProducts(runId);
      } catch (error) {
        console.error('Failed to delete product:', error);
      }
    }
  };

  const syncRunProducts = async () => {
    const normalizedRunId = runId.trim();
    if (!normalizedRunId) {
      setErrorMessage('Enter a run ID before syncing products.');
      return;
    }

    try {
      setSyncing(true);
      setMessage(null);
      setErrorMessage(null);
      const response = await runsApi.syncProducts(normalizedRunId);
      const indexedCount = response.data?.data?.indexed_count ?? 0;
      setMessage(`Indexed ${indexedCount} products for ${normalizedRunId}.`);
      await loadProducts(normalizedRunId);
    } catch (error) {
      console.error('Failed to sync products:', error);
      setErrorMessage('Failed to sync products for this run.');
    } finally {
      setSyncing(false);
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'ready':
        return 'text-tertiary';
      case 'error':
        return 'text-error';
      default:
        return 'text-secondary-container';
    }
  };

  const categories = useMemo(
    () => [
      { key: 'all', label: 'All', count: products.length },
      { key: 'map', label: 'Map Layers', count: products.filter((product) => productMatchesCategory(product, 'map')).length },
      { key: 'station', label: 'Station Curves', count: products.filter((product) => productMatchesCategory(product, 'station')).length },
      { key: 'evaluation', label: 'Evaluation', count: products.filter((product) => productMatchesCategory(product, 'evaluation')).length },
      { key: 'history', label: 'History', count: products.filter((product) => productMatchesCategory(product, 'history')).length },
      { key: 'capability', label: 'Capability', count: products.filter((product) => productMatchesCategory(product, 'capability')).length },
    ],
    [products],
  );
  const visibleProducts = useMemo(
    () => (category === 'all' ? products : products.filter((product) => productMatchesCategory(product, category))),
    [category, products],
  );

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <div className="text-cyan-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header & Action Bar */}
      <div className="flex flex-col gap-6 mb-8">
        <div className="flex justify-between items-end">
          <div>
            <h1 className="font-headline-xl text-headline-xl text-on-background mb-1">Forecast Products</h1>
            <p className="text-on-surface-variant font-body-md">
              Scientific archive of generated pollen dispersal simulations and regional plots.
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => void loadProducts(runId)}
              className="flex items-center gap-2 bg-surface-container-high px-4 py-2 border border-outline-variant hover:bg-surface-variant transition-colors rounded-lg"
            >
              <span className="material-symbols-outlined scale-75">cloud_download</span>
              <span className="font-label-caps text-label-caps">Refresh Index</span>
            </button>
            <button
              onClick={syncRunProducts}
              disabled={syncing || !runId.trim()}
              className="flex items-center gap-2 bg-primary-container px-4 py-2 hover:bg-primary-container/80 transition-colors rounded-lg disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined scale-75">refresh</span>
              <span className="font-label-caps text-label-caps">{syncing ? 'Syncing' : 'Sync Run Products'}</span>
            </button>
          </div>
        </div>

        <div className="flex flex-wrap items-end gap-3 bg-surface-container-low border border-white/5 rounded-xl p-4">
          <label className="flex-1 min-w-[260px]">
            <span className="block font-label-caps text-label-caps text-on-surface-variant mb-2 uppercase">
              Run ID
            </span>
            <input
              value={runId}
              onChange={(event) => setRunId(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  void loadProducts(runId);
                }
              }}
              className="w-full bg-surface-container-high border border-outline-variant rounded-lg px-3 py-2 font-data-mono text-data-mono text-on-surface focus:outline-none focus:border-cyan-500/60"
              placeholder="2026060400"
            />
          </label>
          <button
            onClick={() => void loadProducts(runId)}
            className="flex items-center gap-2 bg-surface-container-high px-4 py-2 border border-outline-variant hover:bg-surface-variant transition-colors rounded-lg"
          >
            <span className="material-symbols-outlined scale-75">filter_alt</span>
            <span className="font-label-caps text-label-caps">Apply Filter</span>
          </button>
          <button
            onClick={() => {
              setRunId('');
              void loadProducts('');
            }}
            className="flex items-center gap-2 bg-surface-container-high px-4 py-2 border border-outline-variant hover:bg-surface-variant transition-colors rounded-lg"
          >
            <span className="material-symbols-outlined scale-75">filter_alt_off</span>
            <span className="font-label-caps text-label-caps">Clear</span>
          </button>
        </div>

        {(message || errorMessage) && (
          <div
            className={`border rounded-lg px-4 py-3 font-body-md text-body-md ${
              errorMessage
                ? 'bg-error-container/10 border-error/30 text-error'
                : 'bg-tertiary/10 border-tertiary/30 text-tertiary'
            }`}
          >
            {errorMessage || message}
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {categories.map((item) => (
            <button
              key={item.key}
              type="button"
              onClick={() => setCategory(item.key)}
              className={`inline-flex items-center gap-2 rounded border px-3 py-1.5 text-xs transition-colors ${
                category === item.key
                  ? 'border-cyan-300/60 bg-cyan-300/15 text-cyan-200'
                  : 'border-white/10 bg-surface-container-low text-on-surface-variant hover:border-white/25'
              }`}
            >
              <span>{item.label}</span>
              <span className="font-data-mono text-[10px]">{item.count}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Hybrid List/Card View */}
      <div className="space-y-4">
        {/* Table Header */}
        <div className="grid grid-cols-12 gap-gutter px-4 font-label-caps text-label-caps text-on-surface-variant uppercase tracking-wider mb-2">
          <div className="col-span-5">Product Identity & Preview</div>
          <div className="col-span-2">Release Time</div>
          <div className="col-span-2">Workflow & Node</div>
          <div className="col-span-1 text-center">Status</div>
          <div className="col-span-2 text-right">Operational Actions</div>
        </div>

        {/* List Items */}
        {visibleProducts.map((product) => (
          <div
            key={product.id}
            className="grid grid-cols-12 gap-gutter bg-surface-container-low border border-white/5 p-3 rounded-xl items-center hover:bg-surface-container transition-all group"
          >
            <div className="col-span-5 flex items-center gap-4">
              <div className="w-20 h-14 rounded-lg bg-surface-container-highest overflow-hidden border border-white/10">
                <div className="w-full h-full bg-gradient-to-br from-cyan-500/20 to-blue-500/20"></div>
              </div>
              <div>
                <h3 className="font-data-mono text-data-mono text-white">{product.product_name}</h3>
                <div className="flex flex-wrap gap-2 mt-1">
                  <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 uppercase">
                    {product.product_type}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] bg-white/5 text-slate-400 border border-white/10 uppercase">
                    {product.resolution}
                  </span>
                  {product.variable && (
                    <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 uppercase">
                      {product.variable}{product.unit ? ` · ${product.unit}` : ''}
                    </span>
                  )}
                  {product.subtype && (
                    <span className="px-2 py-0.5 rounded text-[10px] bg-violet-500/10 text-violet-200 border border-violet-500/20 uppercase">
                      {product.subtype}
                    </span>
                  )}
                  {product.capability_status && (
                    <span className="px-2 py-0.5 rounded text-[10px] bg-amber-500/10 text-amber-200 border border-amber-500/20 uppercase">
                      {product.capability_status}
                    </span>
                  )}
                  {product.lead_time && (
                    <span className="px-2 py-0.5 rounded text-[10px] bg-sky-500/10 text-sky-200 border border-sky-500/20 uppercase">
                      {product.lead_time}
                    </span>
                  )}
                </div>
              </div>
            </div>
            <div className="col-span-2">
              <p className="font-data-mono text-white text-xs">
                {new Date(product.release_time).toLocaleString()}
              </p>
              <p className="text-[10px] text-on-surface-variant font-label-caps">UTC +8:00</p>
            </div>
            <div className="col-span-2">
              <div className="flex items-center gap-2">
                <span className="material-symbols-outlined text-[14px] text-tertiary">memory</span>
                <p className="font-data-mono text-on-surface-variant text-xs">{product.workflow_node}</p>
              </div>
              <p className="text-[10px] text-on-surface-variant font-label-caps ml-5">
                {product.workflow_version}
              </p>
            </div>
            <div className="col-span-1 flex justify-center">
              <div
                className={`flex items-center gap-1.5 px-2 py-1 rounded ${
                  product.status === 'ready'
                    ? 'bg-tertiary/10 border border-tertiary/20'
                    : product.status === 'error'
                    ? 'bg-error-container/10 border border-error/20'
                    : 'bg-secondary-container/10 border border-secondary-container/20'
                }`}
              >
                {product.status === 'ready' && (
                  <div className="w-1.5 h-1.5 rounded-full bg-tertiary animate-pulse"></div>
                )}
                <span className={`text-[10px] font-bold uppercase ${getStatusColor(product.status)}`}>
                  {product.status}
                </span>
              </div>
            </div>
            <div className="col-span-2 flex justify-end items-center gap-3">
              <div className="flex items-center gap-2 mr-4">
                <span className="text-[10px] text-on-surface-variant font-label-caps">Live</span>
                <button
                  onClick={() => togglePublish(product.id, product.is_published)}
                  className={`w-8 h-4 rounded-full relative ${
                    product.is_published ? 'bg-tertiary/40' : 'bg-slate-700'
                  }`}
                >
                  <div
                    className={`absolute top-0.5 w-3 h-3 rounded-full transition-all ${
                      product.is_published
                        ? 'right-0.5 bg-tertiary'
                        : 'left-0.5 bg-slate-500'
                    }`}
                  ></div>
                </button>
              </div>
              <a
                href={productsApi.downloadUrl(product.id)}
                target="_blank"
                rel="noreferrer"
                aria-label={`Download ${product.product_name}`}
                title={`Download ${product.file_path}`}
                className="p-2 bg-surface-container-high border border-outline-variant hover:border-cyan-500/50 hover:text-cyan-400 transition-all rounded-lg"
              >
                <span className="material-symbols-outlined scale-90">download</span>
              </a>
              <button
                onClick={() => deleteProduct(product.id)}
                className="p-2 bg-surface-container-high border border-outline-variant hover:border-error/50 hover:text-error transition-all rounded-lg"
              >
                <span className="material-symbols-outlined scale-90">delete</span>
              </button>
            </div>
          </div>
        ))}
        {visibleProducts.length === 0 && (
          <div className="rounded-xl border border-white/10 bg-surface-container-low p-8 text-center text-on-surface-variant">
            No products match this category.
          </div>
        )}
      </div>

      {/* Pagination / Status Footer */}
      <div className="mt-8 flex justify-between items-center text-[11px] font-label-caps text-on-surface-variant border-t border-white/5 pt-4">
        <div className="flex gap-4">
          <span>Total Items: {products.length}</span>
          <span>Visible: {visibleProducts.length}</span>
          <span className="text-tertiary">Operational: {products.filter((p) => p.status === 'ready').length}</span>
          <span className="text-error">Errors: {products.filter((p) => p.status === 'error').length}</span>
        </div>
      </div>
    </div>
  );
}

function productMatchesCategory(product: ForecastProduct, category: string) {
  const haystack = [
    product.product_name,
    product.product_type,
    product.subtype,
    product.variable,
    product.workflow_node,
    product.file_path,
    product.capability_status,
  ]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  if (category === 'map') return /map|geojson|geotiff|overlay|contour|raster|png/.test(haystack);
  if (category === 'station') return /station|site|city|curve|timeseries|time_series|forecast_json/.test(haystack);
  if (category === 'evaluation') return /eval|error|rmse|mae|bias|score/.test(haystack);
  if (category === 'history') return /history|archive|compare|previous/.test(haystack) || Boolean(product.source_run_id);
  if (category === 'capability') return /capability|skipped|fallback/.test(haystack);
  return true;
}
