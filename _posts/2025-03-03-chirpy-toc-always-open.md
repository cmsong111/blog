---
title: Chirpy 목차(toc) 항상 열기
description: Chirpy 목차(table of contents) 항상 열기
date: 2025-03-03 12:00:00 +0000
categories: [Blog, GitHub-Pages]
tags: [Chirpy, Jekyll, GitHub-Pages]
mermaid: true
image:
  path: https://camo.githubusercontent.com/7deb9e4905ab1e73cec83fa80f3a5d0c7f613e6b522a9fdc41d5c79fad37eda8/68747470733a2f2f6368697270792d696d672e6e65746c6966792e6170702f636f6d6d6f6e732f646576696365732d6d6f636b75702e706e67
---

Chirpy 블로그를 사용하면서, 목차(toc)가 항상 열려있으면 좋겠다는 생각이 들었다.

목차(toc)는 글을 읽는 도중에, 다른 섹션으로 이동할 수 있는 편리한 기능이지만, 기본적으로는 클릭해야 열리는 형태로 되어있다.

따라서, 매번 클릭해야 하는 불편함이 있다.

## 적용 결과

| 적용 전| 적용 후|
|:---:|:---:|
|![적용 전](/assets/images/2025-03-02/before.png) |![적용 후](/assets/images/2025-03-02/after.png) |

## 적용 과정

### SCSS 코드

구글링을 통해 `assets/css/jekyll-theme-chirpy.scss`파일에 아래 코드를 적용하면, 목차(toc)가 항상 열린 상태로 보인다고 한다.

```scss
.is-collapsed {
  max-height: none !important;
}
```

{% linkpreview "https://github.com/cotes2020/jekyll-theme-chirpy/discussions/1706" %}

나는 해당 파일이 존재하지 않아 `assets/css/jekyll-theme-chirpy.scss`파일을 생성하고 위 코드를 추가했다.

하지만, 바로 적용되지 않고, 웹에서 빌드된 CSS 파일을 확인해보니, 해당 코드가 없다는 점을 확인했다.

따라서, `assets/css/style.scss` 파일을 수정하여, `assets/css/style.css`파일을 변경했더니, 모든 CSS 속성이 사라지는 대참사가 발생했다.

대게 이런 경우에는 편하게 원본파일을 구해서 수정하는게 제일 빠르게? 쉽게? 문제를 해결할 수 있다.


### 원본 SCSS 파일 수정
원본 SCSS 파일은 jekyll-theme-chirpy 깃허브에서 바로 확인할 수 있었다

[원본 jekyll-theme-chirpy.scss](https://github.com/cotes2020/jekyll-theme-chirpy/blob/master/assets/css/jekyll-theme-chirpy.scss) 깃허브 링크

해당 코드를 복사하여 `assets/css/jekyll-theme-chirpy.scss`파일을 수정했다

```scss
{% raw %}---
---

@use 'main
{%- if jekyll.environment == 'production' -%}
  .bundle
{%- endif -%}
';

/* append your custom style below */

.is-collapsed {
  max-height: none !important;
}{% endraw %}
``` 

> Vscode에서 저장할 때 자동 정렬이 되면, 페이지 CSS 전체가 무너질 수 있으니 주의하자

그 결과 [적용 결과](#적용-결과)와 같이 목차(toc)가 항상 열린 상태로 보이게 되었다.
