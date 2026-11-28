/**
 * 남주의 커밋로그(namju.kim) 웹 접근성 보강 스크립트
 * - Chirpy 기본 레이아웃(_layouts/default.html)을 덮어쓰지 않고
 *   키보드/스크린 리더 사용자를 위한 "본문으로 바로가기" 스킵 링크를 주입합니다.
 */
(function () {
  'use strict';

  function injectSkipLink() {
    if (!document.body || document.querySelector('.skip-to-content')) {
      return;
    }

    var mainEl = document.querySelector('main');
    if (!mainEl) {
      return;
    }

    if (!mainEl.id) {
      mainEl.id = 'main-content';
    }
    if (!mainEl.hasAttribute('tabindex')) {
      mainEl.setAttribute('tabindex', '-1');
    }

    var skipLink = document.createElement('a');
    skipLink.className = 'skip-to-content';
    skipLink.href = '#' + mainEl.id;
    skipLink.textContent = document.documentElement.lang === 'en' ? 'Skip to main content' : '본문으로 바로가기';

    document.body.insertBefore(skipLink, document.body.firstChild);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectSkipLink);
  } else {
    injectSkipLink();
  }
})();
