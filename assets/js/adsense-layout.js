/**
 * 남주의 커밋로그(namju.kim) 수동 Google AdSense 배치 스크립트
 * - Chirpy 레이아웃/헤더를 덮어쓰지 않고 DOM에 정확한 위치로 수동 광고 단위를 주입합니다.
 * - 넓은 화면(>= 1200px)에서는 우측 사이드바 목차(#toc-wrapper) 바로 아래에 세로형 광고를 배치합니다.
 * - 포스트 본문(.content)에서는 <h2> 섹션 경계에 자동으로 인아티클 광고를 1~2개 삽입합니다.
 * - 포스트 하단(.post-tail-wrapper 직전)에 수평형 광고를 1개 배치합니다.
 */
(function () {
  'use strict';

  var AD_CLIENT = 'ca-pub-9883771255224638';
  var SLOTS = {
    sidebarVertical: '5274823967',
    inArticle: '4516149753',
    postBottom: '9442007524'
  };

  function createAdContainer(className, slotId, options) {
    var wrapper = document.createElement('aside');
    wrapper.className = 'ad-slot-wrapper ' + className;
    wrapper.setAttribute('aria-label', document.documentElement.lang === 'en' ? 'Advertisement' : '광고');

    var label = document.createElement('span');
    label.className = 'ad-slot-label';
    label.textContent = 'AD';
    wrapper.appendChild(label);

    var ins = document.createElement('ins');
    ins.className = 'adsbygoogle';
    ins.style.display = options.display || 'block';
    if (options.width) {
      ins.style.width = options.width;
    }
    if (options.height) {
      ins.style.height = options.height;
    }
    if (options.textAlign) {
      ins.style.textAlign = options.textAlign;
    }
    ins.setAttribute('data-ad-client', AD_CLIENT);
    ins.setAttribute('data-ad-slot', slotId);
    if (options.layout) {
      ins.setAttribute('data-ad-layout', options.layout);
    }
    if (options.format) {
      ins.setAttribute('data-ad-format', options.format);
    }
    if (options.fullWidthResponsive !== undefined) {
      ins.setAttribute(
        'data-full-width-responsive',
        String(options.fullWidthResponsive)
      );
    }

    wrapper.appendChild(ins);
    return wrapper;
  }

  function pushAd() {
    try {
      (window.adsbygoogle = window.adsbygoogle || []).push({});
    } catch (e) {
      // AdSense 스크립트 차단(AdBlock 등) 환경에서는 조용히 무시
    }
  }

  function mountSidebarAd(target, isSticky) {
    var panelWrapper = document.getElementById('panel-wrapper');
    if (!panelWrapper || panelWrapper.querySelector('.ad-slot-sidebar')) {
      return;
    }

    var adEl = createAdContainer(
      isSticky ? 'ad-slot-sidebar ad-slot-sidebar-sticky' : 'ad-slot-sidebar',
      SLOTS.sidebarVertical,
      {
        format: 'vertical',
        fullWidthResponsive: false
      }
    );

    target.appendChild(adEl);
    pushAd();
  }

  function injectSidebarAd() {
    // Bootstrap xl 브레이크포인트(>= 1200px)에서만 우측 #panel-wrapper가 표시됨
    if (!window.matchMedia('(min-width: 1200px)').matches) {
      return;
    }

    var panelWrapper = document.getElementById('panel-wrapper');
    if (!panelWrapper || panelWrapper.querySelector('.ad-slot-sidebar')) {
      return;
    }

    var tocWrapper = document.getElementById('toc-wrapper');
    if (!tocWrapper) {
      // 홈/목록/카테고리 등 목차가 없는 페이지: 우측 패널 하단에 sticky 고정
      mountSidebarAd(panelWrapper, true);
      return;
    }

    var tocReady = function () {
      var tocNav = tocWrapper.querySelector('#toc');
      return (
        !tocWrapper.classList.contains('invisible') &&
        tocNav &&
        tocNav.children.length > 0
      );
    };

    if (tocReady()) {
      mountSidebarAd(tocWrapper, false);
      return;
    }

    // Tocbot이 #toc-wrapper를 초기화할 때까지 감시 (최대 1.5초 폴백)
    var settled = false;
    var observer = new MutationObserver(function () {
      if (!settled && tocReady()) {
        settled = true;
        observer.disconnect();
        mountSidebarAd(tocWrapper, false);
      }
    });
    observer.observe(tocWrapper, {
      attributes: true,
      attributeFilter: ['class'],
      childList: true,
      subtree: true
    });

    window.setTimeout(function () {
      if (!settled) {
        settled = true;
        observer.disconnect();
        mountSidebarAd(tocReady() ? tocWrapper : panelWrapper, !tocReady());
      }
    }, 1500);
  }

  function injectPostAds() {
    var content = document.querySelector('article .content');
    var tailWrapper = document.querySelector('.post-tail-wrapper');

    // 포스트 상세 페이지가 아니면 중단
    if (!content || !tailWrapper) {
      return;
    }

    var isDesktop = window.matchMedia('(min-width: 768px)').matches;

    // 1. 본문 중간 광고: h2 섹션 경계에 자동 삽입
    //    - 데스크톱(>= 768px): 인아티클 광고 (in-article / fluid)
    //    - 모바일(< 768px): 좌우로 길고 상하로 짧은 공식 슬림 배너(320x100) 고정
    var headings = Array.prototype.slice.call(
      content.querySelectorAll(':scope > h2')
    );
    var insertIndices = [];

    if (headings.length >= 4) {
      insertIndices.push(Math.floor(headings.length * 0.45));
    }
    if (headings.length >= 8) {
      var secondIdx = Math.floor(headings.length * 0.78);
      if (secondIdx > insertIndices[0] + 1) {
        insertIndices.push(secondIdx);
      }
    }

    insertIndices.forEach(function (idx) {
      var targetH2 = headings[idx];
      if (!targetH2 || !targetH2.parentNode) {
        return;
      }
      var inArticleAd = isDesktop
        ? createAdContainer('ad-slot-in-article', SLOTS.inArticle, {
            layout: 'in-article',
            format: 'fluid',
            textAlign: 'center'
          })
        : createAdContainer(
            'ad-slot-in-article ad-slot-in-article-mobile',
            SLOTS.postBottom,
            {
              display: 'inline-block',
              width: '320px',
              height: '100px'
            }
          );
      targetH2.parentNode.insertBefore(inArticleAd, targetH2);
      pushAd();
    });

    // 2. 포스트 본문 하단(카테고리/태그·댓글 직전) 수평형 광고
    //    - 데스크톱(>= 768px): 본문 폭 내 수평형 (full-width-responsive 비활성화)
    //    - 모바일(< 768px): 애드센스 공식 슬림 가로 배너(320x100) 고정
    if (!document.querySelector('.ad-slot-post-bottom')) {
      var bottomOptions = isDesktop
        ? {
            format: 'horizontal',
            fullWidthResponsive: false
          }
        : {
            display: 'inline-block',
            width: '320px',
            height: '100px'
          };

      var bottomAd = createAdContainer(
        isDesktop
          ? 'ad-slot-post-bottom'
          : 'ad-slot-post-bottom ad-slot-post-bottom-mobile',
        SLOTS.postBottom,
        bottomOptions
      );
      tailWrapper.parentNode.insertBefore(bottomAd, tailWrapper);
      pushAd();
    }
  }

  function init() {
    // Chirpy의 Tocbot이 #toc-wrapper를 초기화한 직후에 사이드바 위치를 정확히 판별
    window.requestAnimationFrame(function () {
      injectSidebarAd();
      injectPostAds();
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
