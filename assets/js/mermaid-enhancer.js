/**
 * 남주의 커밋로그(namju.kim) Chirpy 네이티브 Mermaid 카드 & 테마 인핸서
 * - Front Matter에 `mermaid: true`가 선언된 글에서만 로드됩니다.
 * - Chirpy 기본 Mermaid(구형 보라색 default/dark 테마)를 `.chart-card`와 통일된
 *   Chirpy 카드 프레임 + 커스텀 라이트/다크 팔레트 + 클릭 확대/줌 모달 + 코드 보기 토글로 업그레이드합니다.
 * - Chirpy v7.6 다크/라이트 모드(`data-bs-theme` / `theme-updated`) 전환 시 실시간 재렌더링합니다.
 */
(function () {
  'use strict';

  var FONT_FAMILY =
    "'Pretendard Variable', Pretendard, -apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif";

  var DIAGRAM_LABELS = [
    { re: /^(flowchart|graph)\b/i, badge: 'FLOWCHART', label: '흐름도 다이어그램' },
    { re: /^sequenceDiagram\b/i, badge: 'SEQUENCE', label: '시퀀스 다이어그램' },
    { re: /^stateDiagram(?:-v2)?\b/i, badge: 'STATE', label: '상태 전이 다이어그램' },
    { re: /^classDiagram\b/i, badge: 'CLASS', label: '클래스 다이어그램' },
    { re: /^erDiagram\b/i, badge: 'ER DIAGRAM', label: 'ER 다이어그램' },
    { re: /^xychart-beta\b/i, badge: 'XY CHART', label: '수치 비교 차트' },
    { re: /^timeline\b/i, badge: 'TIMELINE', label: '타임라인' },
    { re: /^gantt\b/i, badge: 'GANTT', label: '일정 다이어그램' },
    { re: /^pie\b/i, badge: 'PIE', label: '비율 차트' },
    { re: /^mindmap\b/i, badge: 'MINDMAP', label: '마인드맵' },
    { re: /^architecture(?:-beta)?\b/i, badge: 'ARCHITECTURE', label: '아키텍처 다이어그램' }
  ];

  var items = [];
  var renderSeq = 0;
  var lastDark = null;
  var lightboxState = null;

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

  function buildMermaidConfig(dark) {
    var lightVars = {
      darkMode: false,
      background: 'transparent',
      fontFamily: FONT_FAMILY,
      fontSize: '14px',
      primaryColor: '#eff6ff',
      primaryTextColor: '#1e293b',
      primaryBorderColor: '#3b82f6',
      secondaryColor: '#f8fafc',
      secondaryTextColor: '#334155',
      secondaryBorderColor: '#cbd5e1',
      tertiaryColor: '#f0fdf4',
      tertiaryTextColor: '#1e293b',
      tertiaryBorderColor: '#86efac',
      lineColor: '#64748b',
      textColor: '#334155',
      mainBkg: '#eff6ff',
      nodeBorder: '#3b82f6',
      nodeTextColor: '#1e293b',
      clusterBkg: '#f8fafc',
      clusterBorder: '#cbd5e1',
      titleColor: '#1e293b',
      edgeLabelBackground: '#ffffff',
      actorBkg: '#eff6ff',
      actorBorder: '#3b82f6',
      actorTextColor: '#1e293b',
      actorLineColor: '#94a3b8',
      signalColor: '#475569',
      signalTextColor: '#1e293b',
      labelBoxBkgColor: '#f8fafc',
      labelBoxBorderColor: '#cbd5e1',
      labelTextColor: '#1e293b',
      loopTextColor: '#334155',
      noteBkgColor: '#fefce8',
      noteBorderColor: '#eab308',
      noteTextColor: '#422006',
      activationBkgColor: '#dbeafe',
      activationBorderColor: '#2563eb',
      attributeBackgroundColorOdd: '#ffffff',
      attributeBackgroundColorEven: '#f8fafc',
      xyChart: {
        backgroundColor: 'transparent',
        titleColor: '#1e293b',
        xAxisLabelColor: '#475569',
        yAxisLabelColor: '#475569',
        xAxisTitleColor: '#475569',
        yAxisTitleColor: '#475569',
        xAxisLineColor: '#cbd5e1',
        yAxisLineColor: '#cbd5e1',
        xAxisTickColor: '#cbd5e1',
        yAxisTickColor: '#cbd5e1',
        plotColorPalette: '#2563eb, #10b981, #f59e0b, #8b5cf6, #ef4444, #06b6d4'
      }
    };

    var darkVars = {
      darkMode: true,
      background: 'transparent',
      fontFamily: FONT_FAMILY,
      fontSize: '14px',
      primaryColor: '#1e293b',
      primaryTextColor: '#f1f5f9',
      primaryBorderColor: '#60a5fa',
      secondaryColor: '#27272a',
      secondaryTextColor: '#e2e8f0',
      secondaryBorderColor: '#52525b',
      tertiaryColor: '#132a22',
      tertiaryTextColor: '#e2e8f0',
      tertiaryBorderColor: '#34d399',
      lineColor: '#94a3b8',
      textColor: '#e2e8f0',
      mainBkg: '#1e293b',
      nodeBorder: '#60a5fa',
      nodeTextColor: '#f1f5f9',
      clusterBkg: '#18181b',
      clusterBorder: '#3f3f46',
      titleColor: '#f1f5f9',
      edgeLabelBackground: '#1e1e1e',
      actorBkg: '#1e293b',
      actorBorder: '#60a5fa',
      actorTextColor: '#f1f5f9',
      actorLineColor: '#64748b',
      signalColor: '#cbd5e1',
      signalTextColor: '#f1f5f9',
      labelBoxBkgColor: '#27272a',
      labelBoxBorderColor: '#52525b',
      labelTextColor: '#f1f5f9',
      loopTextColor: '#e2e8f0',
      noteBkgColor: '#2c2512',
      noteBorderColor: '#fbbf24',
      noteTextColor: '#fef3c7',
      activationBkgColor: '#1e3a5f',
      activationBorderColor: '#60a5fa',
      attributeBackgroundColorOdd: '#1e1e1e',
      attributeBackgroundColorEven: '#26262a',
      xyChart: {
        backgroundColor: 'transparent',
        titleColor: '#f1f5f9',
        xAxisLabelColor: '#cbd5e1',
        yAxisLabelColor: '#cbd5e1',
        xAxisTitleColor: '#cbd5e1',
        yAxisTitleColor: '#cbd5e1',
        xAxisLineColor: '#475569',
        yAxisLineColor: '#475569',
        xAxisTickColor: '#475569',
        yAxisTickColor: '#475569',
        plotColorPalette: '#60a5fa, #34d399, #fbbf24, #a78bfa, #f87171, #22d3ee'
      }
    };

    var edgeBg = dark ? '#1e1e1e' : '#ffffff';
    var edgeBorder = dark ? 'rgba(255,255,255,0.12)' : 'rgba(15,23,42,0.1)';
    var textCol = dark ? '#f1f5f9' : '#1e293b';

    return {
      startOnLoad: false,
      theme: 'base',
      securityLevel: 'loose',
      fontFamily: FONT_FAMILY,
      themeVariables: dark ? darkVars : lightVars,
      flowchart: {
        curve: 'basis',
        padding: 16,
        nodeSpacing: 44,
        rankSpacing: 52,
        htmlLabels: true,
        useMaxWidth: true
      },
      sequence: {
        diagramMarginX: 24,
        diagramMarginY: 16,
        actorMargin: 48,
        boxMargin: 10,
        messageMargin: 36,
        mirrorActors: false,
        useMaxWidth: true
      },
      er: {
        useMaxWidth: true
      },
      state: {
        useMaxWidth: true
      },
      themeCSS:
        '.node rect, .node polygon { rx: 8px; ry: 8px; stroke-width: 1.5px; } ' +
        '.cluster rect { rx: 10px; ry: 10px; stroke-width: 1.25px; stroke-dasharray: 4 3; } ' +
        '.edgeLabel rect { rx: 6px; ry: 6px; fill: ' + edgeBg + '; stroke: ' + edgeBorder + '; stroke-width: 1px; opacity: 0.96; } ' +
        '.edgeLabel .labelBkg, .labelBkg { background-color: ' + edgeBg + ' !important; color: ' + textCol + ' !important; border: 1px solid ' + edgeBorder + '; border-radius: 6px; padding: 1px 6px; } ' +
        '.edgeLabel, .edgeLabel p, .edgeLabel span { font-size: 12px; font-weight: 500; color: ' + textCol + '; } ' +
        '.nodeLabel, .nodeLabel p { font-weight: 500; line-height: 1.4; } ' +
        '.actor { rx: 8px; ry: 8px; stroke-width: 1.5px; } ' +
        '.messageText { font-weight: 500; font-size: 13px; } ' +
        '.labelText, .loopText { font-weight: 600; } ' +
        '.flowchart-link { stroke-width: 1.6px; } ' +
        'text.titleText, .title { fill: ' + textCol + '; font-weight: 600; }'
    };
  }

  function parseMeta(source) {
    var trimmed = source.trim();
    var title = null;
    var body = trimmed;

    var fmMatch = trimmed.match(/^---\s*\n([\s\S]*?)\n---\s*\n([\s\S]*)$/);
    if (fmMatch) {
      var titleLine = fmMatch[1].match(/^\s*title\s*:\s*['"]?(.+?)['"]?\s*$/m);
      if (titleLine) title = titleLine[1].trim();
      body = fmMatch[2].trim();
    }

    if (!title) {
      var xyTitle = body.match(/^\s*title\s+"([^"]+)"/m) || body.match(/^\s*title\s+(.+)$/m);
      if (xyTitle && /^xychart-beta\b/i.test(body)) {
        title = xyTitle[1].trim();
      }
    }

    var firstLine = body.split(/\r?\n/)[0].trim();
    var badge = 'MERMAID';
    var defaultLabel = '다이어그램';
    for (var i = 0; i < DIAGRAM_LABELS.length; i++) {
      if (DIAGRAM_LABELS[i].re.test(firstLine)) {
        badge = DIAGRAM_LABELS[i].badge;
        defaultLabel = DIAGRAM_LABELS[i].label;
        break;
      }
    }

    return {
      title: title || defaultLabel,
      badge: badge
    };
  }

  function ensureLightbox() {
    if (lightboxState) return lightboxState;

    var overlay = document.createElement('div');
    overlay.className = 'mermaid-lightbox';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');
    overlay.setAttribute('aria-label', '다이어그램 확대 보기');
    overlay.hidden = true;

    overlay.innerHTML =
      '<div class="mermaid-lightbox-dialog">' +
      '  <div class="mermaid-lightbox-header">' +
      '    <span class="mermaid-lightbox-title"></span>' +
      '    <div class="mermaid-lightbox-controls">' +
      '      <button type="button" class="mermaid-card-btn" data-action="zoom-out" aria-label="축소">−</button>' +
      '      <span class="mermaid-lightbox-zoom">100%</span>' +
      '      <button type="button" class="mermaid-card-btn" data-action="zoom-in" aria-label="확대">+</button>' +
      '      <button type="button" class="mermaid-card-btn" data-action="reset">초기화</button>' +
      '      <button type="button" class="mermaid-card-btn mermaid-lightbox-close" data-action="close" aria-label="닫기">닫기</button>' +
      '    </div>' +
      '  </div>' +
      '  <div class="mermaid-lightbox-viewport">' +
      '    <div class="mermaid-lightbox-canvas"></div>' +
      '  </div>' +
      '</div>';

    document.body.appendChild(overlay);

    var state = {
      overlay: overlay,
      titleEl: overlay.querySelector('.mermaid-lightbox-title'),
      zoomEl: overlay.querySelector('.mermaid-lightbox-zoom'),
      viewport: overlay.querySelector('.mermaid-lightbox-viewport'),
      canvas: overlay.querySelector('.mermaid-lightbox-canvas'),
      scale: 1,
      tx: 0,
      ty: 0,
      dragging: false,
      startX: 0,
      startY: 0
    };

    function applyTransform() {
      state.canvas.style.transform =
        'translate(' + state.tx + 'px, ' + state.ty + 'px) scale(' + state.scale + ')';
      state.zoomEl.textContent = Math.round(state.scale * 100) + '%';
    }

    function setScale(next) {
      state.scale = Math.max(0.4, Math.min(4, next));
      applyTransform();
    }

    function resetView() {
      state.scale = 1;
      state.tx = 0;
      state.ty = 0;
      applyTransform();
    }

    function close() {
      overlay.hidden = true;
      document.body.style.overflow = '';
    }

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) {
        close();
        return;
      }
      var btn = e.target.closest('[data-action]');
      if (!btn) return;
      var action = btn.getAttribute('data-action');
      if (action === 'close') close();
      else if (action === 'zoom-in') setScale(state.scale + 0.25);
      else if (action === 'zoom-out') setScale(state.scale - 0.25);
      else if (action === 'reset') resetView();
    });

    state.viewport.addEventListener(
      'wheel',
      function (e) {
        e.preventDefault();
        var delta = e.deltaY < 0 ? 0.15 : -0.15;
        setScale(state.scale + delta);
      },
      { passive: false }
    );

    state.viewport.addEventListener('mousedown', function (e) {
      if (e.button !== 0) return;
      state.dragging = true;
      state.startX = e.clientX - state.tx;
      state.startY = e.clientY - state.ty;
      state.viewport.classList.add('is-dragging');
    });

    window.addEventListener('mousemove', function (e) {
      if (!state.dragging) return;
      state.tx = e.clientX - state.startX;
      state.ty = e.clientY - state.startY;
      applyTransform();
    });

    window.addEventListener('mouseup', function () {
      if (!state.dragging) return;
      state.dragging = false;
      state.viewport.classList.remove('is-dragging');
    });

    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && !overlay.hidden) {
        close();
      }
    });

    state.open = function (title, svgEl) {
      state.titleEl.textContent = title;
      state.canvas.innerHTML = '';
      if (svgEl) {
        var cloned = svgEl.cloneNode(true);
        cloned.removeAttribute('style');
        var vb = cloned.viewBox && cloned.viewBox.baseVal;
        var rect = svgEl.getBoundingClientRect();
        var natW = (vb && vb.width > 0 ? vb.width : rect.width) || 640;
        var natH = (vb && vb.height > 0 ? vb.height : rect.height) || 400;
        var maxW = Math.min(window.innerWidth * 0.84, 1120);
        var maxH = Math.min(window.innerHeight * 0.72, 720);
        var fitScale = Math.min(maxW / natW, maxH / natH, 1.8);
        var targetW = Math.max(280, Math.round(natW * fitScale));
        cloned.setAttribute('width', String(targetW));
        cloned.removeAttribute('height');
        cloned.style.width = targetW + 'px';
        cloned.style.height = 'auto';
        cloned.style.maxWidth = 'none';
        state.canvas.appendChild(cloned);
      }
      resetView();
      overlay.hidden = false;
      document.body.style.overflow = 'hidden';
    };

    lightboxState = state;
    return state;
  }

  function renderOne(item, seq) {
    var id = 'mmd-svg-' + item.idx + '-' + seq;
    try {
      var res = window.mermaid.render(id, item.source);
      Promise.resolve(res)
        .then(function (out) {
          var svg = typeof out === 'string' ? out : out && out.svg;
          if (!svg) return;
          item.stage.innerHTML = svg;
          if (out && typeof out.bindFunctions === 'function') {
            out.bindFunctions(item.stage);
          }
          var svgEl = item.stage.querySelector('svg');
          if (svgEl) {
            svgEl.style.height = 'auto';
          }
        })
        .catch(function () {
          item.stage.innerHTML = '<pre class="mermaid-fallback"></pre>';
          item.stage.firstChild.textContent = item.source;
        });
    } catch (err) {
      item.stage.innerHTML = '<pre class="mermaid-fallback"></pre>';
      item.stage.firstChild.textContent = item.source;
    }
  }

  function renderAll(force) {
    if (typeof window.mermaid === 'undefined' || typeof window.mermaid.initialize !== 'function') {
      return;
    }
    var dark = isDarkMode();
    if (!force && lastDark === dark) return;
    lastDark = dark;
    renderSeq += 1;

    window.mermaid.initialize(buildMermaidConfig(dark));
    var currentSeq = renderSeq;
    items.forEach(function (item) {
      renderOne(item, currentSeq);
    });
  }

  function buildCard(source, idx) {
    var meta = parseMeta(source);
    var sourceId = 'mermaid-source-' + idx;

    var figure = document.createElement('figure');
    figure.className = 'mermaid-card';

    var header = document.createElement('div');
    header.className = 'mermaid-card-header';

    var titleEl = document.createElement('span');
    titleEl.className = 'mermaid-card-title';
    titleEl.textContent = meta.title;

    var actions = document.createElement('div');
    actions.className = 'mermaid-card-actions';

    var badge = document.createElement('span');
    badge.className = 'mermaid-card-badge';
    badge.textContent = meta.badge;

    var zoomBtn = document.createElement('button');
    zoomBtn.type = 'button';
    zoomBtn.className = 'mermaid-card-btn';
    zoomBtn.textContent = '확대';
    zoomBtn.title = '다이어그램 확대 보기 (더블클릭 가능)';

    var toggleBtn = document.createElement('button');
    toggleBtn.type = 'button';
    toggleBtn.className = 'mermaid-card-btn';
    toggleBtn.setAttribute('aria-expanded', 'false');
    toggleBtn.setAttribute('aria-controls', sourceId);
    toggleBtn.textContent = '코드 보기';

    actions.appendChild(badge);
    actions.appendChild(zoomBtn);
    actions.appendChild(toggleBtn);
    header.appendChild(titleEl);
    header.appendChild(actions);
    figure.appendChild(header);

    var body = document.createElement('div');
    body.className = 'mermaid-card-body';

    var stage = document.createElement('div');
    stage.className = 'mermaid-stage';
    body.appendChild(stage);
    figure.appendChild(body);

    var sourceWrap = document.createElement('div');
    sourceWrap.id = sourceId;
    sourceWrap.className = 'mermaid-card-source';
    sourceWrap.hidden = true;

    var sourceBar = document.createElement('div');
    sourceBar.className = 'mermaid-source-bar';
    var sourceLabel = document.createElement('span');
    sourceLabel.textContent = 'MERMAID';
    var copyBtn = document.createElement('button');
    copyBtn.type = 'button';
    copyBtn.className = 'mermaid-card-btn';
    copyBtn.textContent = '복사';
    copyBtn.addEventListener('click', function () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(source).then(function () {
          copyBtn.textContent = '복사됨';
          setTimeout(function () {
            copyBtn.textContent = '복사';
          }, 1500);
        });
      }
    });
    sourceBar.appendChild(sourceLabel);
    sourceBar.appendChild(copyBtn);

    var pre = document.createElement('pre');
    var code = document.createElement('code');
    code.textContent = source;
    pre.appendChild(code);
    sourceWrap.appendChild(sourceBar);
    sourceWrap.appendChild(pre);
    figure.appendChild(sourceWrap);

    function openZoom() {
      var svgEl = stage.querySelector('svg');
      if (!svgEl) return;
      ensureLightbox().open(meta.title, svgEl);
    }

    zoomBtn.addEventListener('click', openZoom);
    stage.addEventListener('dblclick', openZoom);

    toggleBtn.addEventListener('click', function () {
      var nextHidden = !sourceWrap.hidden;
      sourceWrap.hidden = nextHidden;
      toggleBtn.setAttribute('aria-expanded', String(!nextHidden));
      toggleBtn.textContent = nextHidden ? '코드 보기' : '코드 닫기';
    });

    return {
      idx: idx,
      source: source,
      figure: figure,
      stage: stage
    };
  }

  function enhanceMermaidBlocks() {
    if (typeof window.mermaid === 'undefined') return;

    // Prevent Chirpy's default startOnLoad from rendering with ugly default theme
    window.mermaid.initialize(buildMermaidConfig(isDarkMode()));

    var targets = [];

    // Case 1: Chirpy post.min.js already converted <pre><code class="language-mermaid"> into <pre class="mermaid">
    var chirpyPres = Array.prototype.slice.call(document.querySelectorAll('pre.mermaid'));
    chirpyPres.forEach(function (mPre) {
      var prev = mPre.previousElementSibling;
      var src = mPre.textContent;
      var hiddenPre = null;
      if (prev && prev.classList.contains('d-none')) {
        var codeEl = prev.querySelector('code.language-mermaid');
        if (codeEl) {
          src = codeEl.textContent;
          hiddenPre = prev;
        }
      }
      targets.push({ replaceEl: mPre, removeEl: hiddenPre, source: src.trim() });
    });

    // Case 2: Fallback if raw <pre><code class="language-mermaid"> remains untouched
    var rawCodes = Array.prototype.slice.call(
      document.querySelectorAll('pre:not(.d-none) > code.language-mermaid')
    );
    rawCodes.forEach(function (codeEl) {
      targets.push({
        replaceEl: codeEl.parentElement,
        removeEl: null,
        source: codeEl.textContent.trim()
      });
    });

    if (targets.length === 0) return;

    targets.forEach(function (t, idx) {
      var item = buildCard(t.source, idx);
      t.replaceEl.parentNode.replaceChild(item.figure, t.replaceEl);
      if (t.removeEl && t.removeEl.parentNode) {
        t.removeEl.parentNode.removeChild(t.removeEl);
      }
      items.push(item);
    });

    renderAll(true);

    var observer = new MutationObserver(function () {
      renderAll(false);
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['data-bs-theme', 'data-mode']
    });

    window.addEventListener('message', function (event) {
      if (event.data && event.data.id === 'theme-updated') {
        renderAll(false);
      }
    });

    if (window.matchMedia) {
      window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', function () {
        renderAll(false);
      });
    }
  }

  if (typeof window.mermaid !== 'undefined' && typeof window.mermaid.initialize === 'function') {
    window.mermaid.initialize({ startOnLoad: false });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', enhanceMermaidBlocks);
  } else {
    enhanceMermaidBlocks();
  }
})();
