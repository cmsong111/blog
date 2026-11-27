/**
 * 남주의 커밋로그(namju.kim) Chirpy 네이티브 Chart.js 조건부 렌더러
 * - Front Matter에 `chart: true`가 선언된 글에서만 로드됩니다.
 * - Markdown에서 ```json ... ``` 직후 `{: .chart-js }`를 붙인 블록을
 *   Chirpy 카드 디자인과 어우러지는 반응형 Chart.js 차트(bar/line/doughnut/scatter/bubble/radar/polarArea)로 변환합니다.
 * - 카드 헤더의 `JSON 보기` 토글 버튼으로 원본 설정 JSON을 즉시 펼쳐 볼 수 있습니다.
 * - Chirpy 다크/라이트 모드(`data-bs-theme` / `theme-updated`) 전환 시 색상을 실시간 동기화합니다.
 */
(function () {
  'use strict';

  var FONT_FAMILY =
    "'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif";

  var PALETTE_LIGHT = [
    '#2563eb',
    '#10b981',
    '#f59e0b',
    '#8b5cf6',
    '#ef4444',
    '#06b6d4',
    '#ec4899',
    '#6366f1'
  ];

  var PALETTE_DARK = [
    '#60a5fa',
    '#34d399',
    '#fbbf24',
    '#a78bfa',
    '#f87171',
    '#22d3ee',
    '#f472b6',
    '#818cf8'
  ];

  var instances = [];

  function isDarkMode() {
    var attr =
      document.documentElement.getAttribute('data-bs-theme') ||
      document.documentElement.getAttribute('data-mode');
    if (attr === 'dark') return true;
    if (attr === 'light') return false;
    if (window.Theme && typeof window.Theme.isDark === 'boolean') {
      return window.Theme.isDark;
    }
    return window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  function readCssVar(name, fallback) {
    var val = window.getComputedStyle(document.documentElement).getPropertyValue(name);
    return val && val.trim() ? val.trim() : fallback;
  }

  function hexToRgba(hex, alpha) {
    var clean = hex.replace('#', '');
    if (clean.length !== 6) return hex;
    var r = parseInt(clean.slice(0, 2), 16);
    var g = parseInt(clean.slice(2, 4), 16);
    var b = parseInt(clean.slice(4, 6), 16);
    return 'rgba(' + r + ', ' + g + ', ' + b + ', ' + alpha + ')';
  }

  function themeTokens() {
    var dark = isDarkMode();
    return {
      dark: dark,
      cardBg: readCssVar('--card-bg', dark ? '#1e1e1e' : '#ffffff'),
      heading: dark ? '#f1f5f9' : readCssVar('--heading-color', '#2a2a2a'),
      text: dark ? '#e2e8f0' : readCssVar('--text-color', '#34343c'),
      muted: dark ? '#cbd5e1' : '#525866',
      grid: dark ? 'rgba(255, 255, 255, 0.12)' : 'rgba(15, 23, 42, 0.08)',
      tooltipBg: dark ? 'rgba(15, 23, 42, 0.96)' : 'rgba(30, 41, 59, 0.94)',
      tooltipBorder: dark ? 'rgba(255, 255, 255, 0.16)' : 'rgba(255, 255, 255, 0.12)',
      palette: dark ? PALETTE_DARK : PALETTE_LIGHT
    };
  }

  function syncGlobalDefaults(tokens) {
    if (window.Chart && window.Chart.defaults) {
      window.Chart.defaults.color = tokens.text;
      window.Chart.defaults.borderColor = tokens.grid;
    }
  }

  function applyDatasetDefaults(config, tokens) {
    var datasets = (config.data && config.data.datasets) || [];
    var isBar = config.type === 'bar';
    var isLine = config.type === 'line';
    var isRadar = config.type === 'radar';
    var isScatter = config.type === 'scatter' || config.type === 'bubble';
    var isPolar = config.type === 'polarArea';
    var isPie = config.type === 'pie' || config.type === 'doughnut' || isPolar;

    datasets.forEach(function (ds, idx) {
      var color = tokens.palette[idx % tokens.palette.length];
      if (!ds.backgroundColor) {
        if (isPie) {
          var len = (config.data && config.data.labels && config.data.labels.length) || tokens.palette.length;
          ds.backgroundColor = Array.from({ length: len }, function (_, i) {
            var c = tokens.palette[i % tokens.palette.length];
            return isPolar ? hexToRgba(c, 0.72) : c;
          });
          ds._autoPieColors = len;
          ds._isPolar = isPolar;
        } else if (isScatter) {
          ds.backgroundColor = hexToRgba(color, config.type === 'bubble' ? 0.58 : 0.72);
          ds.borderColor = color;
          ds._autoScatterColor = idx;
          ds._scatterAlpha = config.type === 'bubble' ? 0.58 : 0.72;
        } else if (isRadar) {
          ds.backgroundColor = hexToRgba(color, 0.2);
          ds.borderColor = color;
          ds.pointBackgroundColor = color;
          ds._autoRadarColor = idx;
        } else if (isLine && ds.fill) {
          ds.backgroundColor = hexToRgba(color, 0.16);
          ds.borderColor = color;
          ds.pointBackgroundColor = color;
          ds._autoAreaLineColor = idx;
        } else {
          ds.backgroundColor = color;
          ds._autoColor = idx;
        }
      }

      if (isBar) {
        if (ds.borderRadius === undefined) ds.borderRadius = 6;
        if (ds.borderSkipped === undefined) ds.borderSkipped = false;
        if (ds.maxBarThickness === undefined) ds.maxBarThickness = 44;
      }

      if (isLine) {
        if (!ds.borderColor) {
          ds.borderColor = ds.backgroundColor || color;
          ds._autoBorder = idx;
        }
        if (ds.tension === undefined) ds.tension = 0.34;
        if (ds.borderWidth === undefined) ds.borderWidth = 2.5;
        if (ds.pointRadius === undefined) ds.pointRadius = 3.5;
        if (ds.pointHoverRadius === undefined) ds.pointHoverRadius = 5.5;
      }

      if (isRadar) {
        if (ds.borderWidth === undefined) ds.borderWidth = 2;
        if (ds.pointRadius === undefined) ds.pointRadius = 3.5;
        if (ds.pointHoverRadius === undefined) ds.pointHoverRadius = 5.5;
      }

      if (isScatter) {
        if (config.type === 'scatter') {
          if (ds.pointRadius === undefined) ds.pointRadius = 5;
          if (ds.pointHoverRadius === undefined) ds.pointHoverRadius = 7.5;
        }
        if (ds.borderWidth === undefined) ds.borderWidth = 1.5;
      }

      if (isPie) {
        if (ds.borderWidth === undefined) ds.borderWidth = 2;
        if (!ds.borderColor) {
          ds.borderColor = tokens.cardBg;
          ds._autoPieBorder = true;
        }
        if (ds.hoverOffset === undefined && !isPolar) ds.hoverOffset = 6;
      }
    });
  }

  function applyTheme(config, tokens) {
    applyDatasetDefaults(config, tokens);

    var isScatter = config.type === 'scatter' || config.type === 'bubble';
    var isRadar = config.type === 'radar';
    var isPolar = config.type === 'polarArea';
    var isPie = config.type === 'pie' || config.type === 'doughnut' || isPolar;
    var hasRadialScale = isRadar || isPolar;
    var nonCartesian = isPie || isRadar;

    config.options = config.options || {};
    config.options.responsive = true;
    config.options.maintainAspectRatio = false;

    if (config.type === 'doughnut' && config.options.cutout === undefined) {
      config.options.cutout = '64%';
    }

    config.options.interaction = Object.assign(
      isScatter || isPie
        ? { mode: 'nearest', intersect: true }
        : { mode: 'index', intersect: false },
      config.options.interaction || {}
    );

    config.options.plugins = config.options.plugins || {};
    config.options.plugins.legend = Object.assign(
      { position: 'bottom' },
      config.options.plugins.legend || {}
    );
    config.options.plugins.legend.labels = Object.assign(
      {
        color: tokens.text,
        usePointStyle: true,
        pointStyle: 'circle',
        boxWidth: 8,
        boxHeight: 8,
        padding: 16,
        font: { family: FONT_FAMILY, size: 12, weight: '500' }
      },
      config.options.plugins.legend.labels || {}
    );

    config.options.plugins.tooltip = Object.assign(
      {
        backgroundColor: tokens.tooltipBg,
        titleColor: '#f8fafc',
        bodyColor: '#e2e8f0',
        borderColor: tokens.tooltipBorder,
        borderWidth: 1,
        padding: 10,
        cornerRadius: 8,
        boxPadding: 5,
        usePointStyle: true,
        titleFont: { family: FONT_FAMILY, size: 12, weight: '600' },
        bodyFont: { family: FONT_FAMILY, size: 12 }
      },
      config.options.plugins.tooltip || {}
    );

    if (hasRadialScale) {
      config.options.scales = config.options.scales || {};
      var r = config.options.scales.r || {};
      r.grid = Object.assign({ color: tokens.grid }, r.grid || {});
      r.angleLines = Object.assign({ color: tokens.grid }, r.angleLines || {});
      r.pointLabels = Object.assign(
        {
          color: tokens.text,
          font: { family: FONT_FAMILY, size: 12, weight: '500' }
        },
        r.pointLabels || {}
      );
      r.ticks = Object.assign(
        {
          color: tokens.muted,
          backdropColor: 'transparent',
          font: { family: FONT_FAMILY, size: 11 }
        },
        r.ticks || {}
      );
      config.options.scales.r = r;
    }

    if (!nonCartesian) {
      var isHorizontal = config.options.indexAxis === 'y';
      config.options.scales = config.options.scales || { x: {}, y: {} };
      var axes = ['x', 'y'];
      Object.keys(config.options.scales).forEach(function (k) {
        if (axes.indexOf(k) === -1) axes.push(k);
      });
      axes.forEach(function (axis) {
        var scale = config.options.scales[axis] || {};
        var isCategoryAxis = isHorizontal ? axis === 'y' : axis === 'x';
        scale.border = Object.assign({ display: false }, scale.border || {});
        scale.ticks = Object.assign(
          {
            color: tokens.muted,
            padding: 8,
            font: { family: FONT_FAMILY, size: 12 }
          },
          scale.ticks || {}
        );
        scale.grid = Object.assign(
          {
            display: isScatter ? true : !isCategoryAxis,
            color: tokens.grid,
            tickLength: 0
          },
          scale.grid || {}
        );
        if (scale.title) {
          scale.title = Object.assign(
            {
              color: tokens.muted,
              font: { family: FONT_FAMILY, size: 12, weight: '500' }
            },
            scale.title
          );
        }
        config.options.scales[axis] = scale;
      });
    }
    return config;
  }

  function updateAllThemes() {
    var tokens = themeTokens();
    syncGlobalDefaults(tokens);
    instances.forEach(function (chart) {
      var plugins = chart.options.plugins || {};
      var legendLabels = plugins.legend && plugins.legend.labels;
      if (legendLabels) legendLabels.color = tokens.text;
      if (plugins.title) plugins.title.color = tokens.heading;
      if (plugins.subtitle) plugins.subtitle.color = tokens.muted;

      var tooltip = plugins.tooltip;
      if (tooltip) {
        tooltip.backgroundColor = tokens.tooltipBg;
        tooltip.borderColor = tokens.tooltipBorder;
      }

      if (chart.options.scales) {
        Object.keys(chart.options.scales).forEach(function (axis) {
          var scale = chart.options.scales[axis];
          if (scale.ticks) scale.ticks.color = tokens.muted;
          if (scale.grid) scale.grid.color = tokens.grid;
          if (scale.angleLines) scale.angleLines.color = tokens.grid;
          if (scale.pointLabels) scale.pointLabels.color = tokens.text;
          if (scale.title) scale.title.color = tokens.muted;
        });
      }

      (chart.data.datasets || []).forEach(function (ds) {
        if (typeof ds._autoColor === 'number') {
          ds.backgroundColor = tokens.palette[ds._autoColor % tokens.palette.length];
        }
        if (typeof ds._autoBorder === 'number') {
          ds.borderColor = tokens.palette[ds._autoBorder % tokens.palette.length];
        }
        if (typeof ds._autoAreaLineColor === 'number') {
          var lc = tokens.palette[ds._autoAreaLineColor % tokens.palette.length];
          ds.backgroundColor = hexToRgba(lc, 0.16);
          ds.borderColor = lc;
          ds.pointBackgroundColor = lc;
        }
        if (typeof ds._autoRadarColor === 'number') {
          var rc = tokens.palette[ds._autoRadarColor % tokens.palette.length];
          ds.backgroundColor = hexToRgba(rc, 0.2);
          ds.borderColor = rc;
          ds.pointBackgroundColor = rc;
        }
        if (typeof ds._autoScatterColor === 'number') {
          var sc = tokens.palette[ds._autoScatterColor % tokens.palette.length];
          ds.backgroundColor = hexToRgba(sc, ds._scatterAlpha || 0.72);
          ds.borderColor = sc;
        }
        if (typeof ds._autoPieColors === 'number') {
          ds.backgroundColor = Array.from({ length: ds._autoPieColors }, function (_, i) {
            var c = tokens.palette[i % tokens.palette.length];
            return ds._isPolar ? hexToRgba(c, 0.72) : c;
          });
        }
        if (ds._autoPieBorder) {
          ds.borderColor = tokens.cardBg;
        }
      });

      chart.update('none');
    });
  }

  function extractTitle(config) {
    var titleOpt = config.options && config.options.plugins && config.options.plugins.title;
    if (titleOpt && titleOpt.display !== false && titleOpt.text) {
      var text = Array.isArray(titleOpt.text) ? titleOpt.text.join(' ') : String(titleOpt.text);
      titleOpt.display = false;
      return text;
    }
    return null;
  }

  function renderCharts() {
    if (typeof window.Chart === 'undefined') {
      return;
    }

    var tokens = themeTokens();
    syncGlobalDefaults(tokens);
    var blocks = document.querySelectorAll('.chart-js');
    blocks.forEach(function (block, idx) {
      var codeEl =
        block.querySelector('td.rouge-code pre') ||
        block.querySelector('pre code') ||
        block.querySelector('code');
      if (!codeEl) return;

      var config;
      try {
        config = JSON.parse(codeEl.textContent);
      } catch (err) {
        return;
      }

      var titleText = extractTitle(config);
      var chartType = (config.type || 'chart').toUpperCase();
      var sourceId = 'chart-source-' + idx;

      var figure = document.createElement('figure');
      figure.className = 'chart-card';

      var header = document.createElement('div');
      header.className = 'chart-card-header';

      var titleEl = document.createElement('span');
      titleEl.className = 'chart-card-title';
      titleEl.textContent = titleText || chartType + ' Chart';

      var actions = document.createElement('div');
      actions.className = 'chart-card-actions';

      var badge = document.createElement('span');
      badge.className = 'chart-card-badge';
      badge.textContent = chartType;

      var toggleBtn = document.createElement('button');
      toggleBtn.type = 'button';
      toggleBtn.className = 'chart-card-toggle';
      toggleBtn.setAttribute('aria-expanded', 'false');
      toggleBtn.setAttribute('aria-controls', sourceId);
      toggleBtn.textContent = 'JSON 보기';

      actions.appendChild(badge);
      actions.appendChild(toggleBtn);
      header.appendChild(titleEl);
      header.appendChild(actions);
      figure.appendChild(header);

      var body = document.createElement('div');
      body.className = 'chart-card-body';
      if (config.type === 'radar' || config.type === 'polarArea') {
        body.className += ' chart-card-body-tall';
      }

      var canvas = document.createElement('canvas');
      canvas.setAttribute('aria-label', titleText || chartType + ' Chart');
      canvas.setAttribute('role', 'img');
      body.appendChild(canvas);
      figure.appendChild(body);

      var sourceWrap = document.createElement('div');
      sourceWrap.id = sourceId;
      sourceWrap.className = 'chart-card-source';
      sourceWrap.hidden = true;

      toggleBtn.addEventListener('click', function () {
        var nextHidden = !sourceWrap.hidden;
        sourceWrap.hidden = nextHidden;
        toggleBtn.setAttribute('aria-expanded', String(!nextHidden));
        toggleBtn.textContent = nextHidden ? 'JSON 보기' : 'JSON 닫기';
      });

      block.parentNode.insertBefore(figure, block);
      block.classList.remove('chart-js');
      block.classList.add('chart-source-block');
      sourceWrap.appendChild(block);
      figure.appendChild(sourceWrap);

      var chart = new window.Chart(canvas.getContext('2d'), applyTheme(config, tokens));
      instances.push(chart);
    });

    if (instances.length > 0) {
      var observer = new MutationObserver(updateAllThemes);
      observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-bs-theme', 'data-mode']
      });
      window.addEventListener('message', function (event) {
        if (event.data && event.data.id === 'theme-updated') {
          updateAllThemes();
        }
      });
      if (window.matchMedia) {
        window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', updateAllThemes);
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderCharts);
  } else {
    renderCharts();
  }
})();
