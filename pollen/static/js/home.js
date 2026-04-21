(function () {
  const mapContainer = document.getElementById("forecast-map");
  if (!mapContainer) {
    return;
  }

  const pollenSelect = document.getElementById("pollen-type");
  const domainSelect = document.getElementById("domain-select");
  const timeRange = document.getElementById("time-range");
  const timeLabel = document.getElementById("time-label");
  const profileSelect = document.getElementById("profile-select");
  const metricLabel = document.getElementById("map-metrics");
  const insightList = document.getElementById("insight-list");

  let products = [];
  let domains = [];
  let map;
  let productLayer;
  let chartProfile;
  let chartDomain;

  function initMap() {
    const view = new ol.View({
      center: ol.proj.fromLonLat([104, 35.5]),
      zoom: 4.5,
    });

    const domainFeatures = [];
    const domainStyles = {};
    map = new ol.Map({
      target: mapContainer,
      layers: [
        new ol.layer.Vector({
          source: new ol.source.Vector({ features: domainFeatures }),
          style: function (feature) {
            const code = feature.get("code");
            if (!domainStyles[code]) {
              domainStyles[code] = new ol.style.Style({
                stroke: new ol.style.Stroke({ color: code === "d02" ? "#ffd166" : "#69c0ff", width: 2 }),
                fill: new ol.style.Fill({ color: code === "d02" ? "rgba(255,209,102,0.08)" : "rgba(105,192,255,0.08)" }),
              });
            }
            return domainStyles[code];
          },
        }),
      ],
      view,
      controls: ol.control.defaults.defaults({ attribution: false }),
    });

    fetch("/api/home/summary/")
      .then((response) => response.json())
      .then((payload) => {
        domains = payload.domains || [];
        const vectorSource = map.getLayers().item(0).getSource();
        domains.forEach((domain) => {
          if (!domain.extent || domain.extent.length !== 4) {
            return;
          }
          const extent = ol.proj.transformExtent(domain.extent, "EPSG:4326", "EPSG:3857");
          const polygon = ol.geom.Polygon.fromExtent(extent);
          const feature = new ol.Feature({ geometry: polygon, code: domain.code });
          vectorSource.addFeature(feature);
        });
      });
  }

  function ensureCharts() {
    if (!chartProfile) {
      chartProfile = echarts.init(document.getElementById("profile-chart"));
      chartDomain = echarts.init(document.getElementById("domain-chart"));
    }
  }

  function renderInsights(product) {
    if (!product) {
      insightList.innerHTML = "<p>暂无已发布业务产物。</p>";
      return;
    }
    const stats = product.metadata || {};
    const items = [
      `业务时间：${new Date(product.run_time).toLocaleString("zh-CN")}`,
      `预报时效：+${product.forecast_hour} 小时`,
      `域内最大浓度：${stats.max_concentration || "--"}`,
      `域内平均浓度：${stats.mean_concentration || "--"}`,
    ];
    insightList.innerHTML = items
      .map((item) => `<div class="insight-item">${item}</div>`)
      .join("");
  }

  function addOrReplaceProductLayer(product) {
    if (!map) {
      return;
    }
    if (productLayer) {
      map.removeLayer(productLayer);
      productLayer = null;
    }
    if (!product) {
      metricLabel.textContent = "暂无已发布产物";
      renderInsights(null);
      return;
    }
    const extent4326 = (product.domain && product.domain.extent) || [73, 18, 135, 54];
    const extent = ol.proj.transformExtent(extent4326, "EPSG:4326", "EPSG:3857");
    if (product.tile_url_template) {
      productLayer = new ol.layer.Tile({
        opacity: product.domain.default_opacity || 0.72,
        source: new ol.source.XYZ({ url: product.tile_url_template }),
      });
    } else if (product.preview_image_path) {
      productLayer = new ol.layer.Image({
        opacity: product.domain.default_opacity || 0.72,
        source: new ol.source.ImageStatic({
          url: `/static/${product.preview_image_path}`,
          imageExtent: extent,
          projection: "EPSG:3857",
        }),
      });
    }
    if (productLayer) {
      map.addLayer(productLayer);
      map.getView().fit(extent, { padding: [30, 30, 30, 30], duration: 450 });
    }
    metricLabel.textContent = `FH${product.forecast_hour} · ${product.domain.code} · ${product.pollen_type.name}`;
    renderInsights(product);
  }

  function renderDomainChart(selectedProducts) {
    ensureCharts();
    const aggregated = {};
    selectedProducts.forEach((product) => {
      const code = product.domain.code;
      if (!aggregated[code]) {
        aggregated[code] = [];
      }
      aggregated[code].push((product.metadata && product.metadata.max_concentration) || 0);
    });
    chartDomain.setOption({
      backgroundColor: "transparent",
      textStyle: { color: "#eff7ff" },
      xAxis: {
        type: "category",
        data: Object.keys(aggregated),
        axisLabel: { color: "#9bb4cc" },
      },
      yAxis: {
        type: "value",
        axisLabel: { color: "#9bb4cc" },
        splitLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
      },
      series: [
        {
          type: "bar",
          data: Object.values(aggregated).map((values) => {
            const sum = values.reduce((acc, value) => acc + value, 0);
            return Number((sum / Math.max(values.length, 1)).toFixed(2));
          }),
          itemStyle: {
            borderRadius: [10, 10, 0, 0],
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "#7ce7ff" },
              { offset: 1, color: "#1ba2ff" },
            ]),
          },
        },
      ],
    });
  }

  function renderProfileChart(profileId) {
    if (!profileId) {
      return;
    }
    ensureCharts();
    fetch(`/api/home/point-profiles/${profileId}/series/`)
      .then((response) => response.json())
      .then((payload) => {
        chartProfile.setOption({
          backgroundColor: "transparent",
          textStyle: { color: "#eff7ff" },
          tooltip: { trigger: "axis" },
          xAxis: {
            type: "category",
            data: payload.series.map((point) => new Date(point.time).toLocaleString("zh-CN", { hour: "2-digit", minute: "2-digit" })),
            axisLabel: { color: "#9bb4cc" },
          },
          yAxis: {
            type: "value",
            axisLabel: { color: "#9bb4cc" },
            splitLine: { lineStyle: { color: "rgba(255,255,255,0.1)" } },
          },
          series: [
            {
              type: "line",
              smooth: true,
              areaStyle: {},
              lineStyle: { width: 3, color: "#ffd166" },
              itemStyle: { color: "#ffd166" },
              data: payload.series.map((point) => point.value),
            },
          ],
        });
      });
  }

  function updateProductView() {
    const filtered = products.filter((product) => {
      return product.domain.code === domainSelect.value && product.pollen_type.code === pollenSelect.value;
    });
    if (!filtered.length) {
      addOrReplaceProductLayer(null);
      timeRange.max = 0;
      timeRange.value = 0;
      timeLabel.textContent = "--";
      return;
    }
    filtered.sort((left, right) => new Date(left.valid_time) - new Date(right.valid_time));
    timeRange.max = String(filtered.length - 1);
    const index = Math.min(Number(timeRange.value || 0), filtered.length - 1);
    const current = filtered[index];
    timeLabel.textContent = new Date(current.valid_time).toLocaleString("zh-CN");
    addOrReplaceProductLayer(current);
    renderDomainChart(filtered);
  }

  function loadProducts() {
    const params = new URLSearchParams();
    if (domainSelect.value) {
      params.set("domain", domainSelect.value);
    }
    if (pollenSelect.value) {
      params.set("pollen", pollenSelect.value);
    }
    fetch(`/api/home/products/?${params.toString()}`)
      .then((response) => response.json())
      .then((payload) => {
        products = payload;
        timeRange.value = 0;
        updateProductView();
      });
  }

  initMap();
  ensureCharts();
  renderProfileChart(profileSelect && profileSelect.value);
  loadProducts();

  pollenSelect.addEventListener("change", loadProducts);
  domainSelect.addEventListener("change", loadProducts);
  timeRange.addEventListener("input", updateProductView);
  if (profileSelect) {
    profileSelect.addEventListener("change", function () {
      renderProfileChart(this.value);
    });
  }
  window.addEventListener("resize", function () {
    if (chartProfile) {
      chartProfile.resize();
      chartDomain.resize();
    }
  });
})();
