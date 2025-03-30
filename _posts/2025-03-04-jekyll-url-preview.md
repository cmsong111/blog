---
title: Jekyll URL 미리보기 만들기
description: Link preview를 사용하여 URL 미리보기 만들기 (템플릿 커스텀)
date: 2025-03-04 12:00:00 +0000
categories: [Blog, GitHub-Pages]
tags: [Chirpy, Jekyll, GitHub-Pages]
mermaid: true
image:
  path: https://camo.githubusercontent.com/7deb9e4905ab1e73cec83fa80f3a5d0c7f613e6b522a9fdc41d5c79fad37eda8/68747470733a2f2f6368697270792d696d672e6e65746c6966792e6170702f636f6d6d6f6e732f646576696365732d6d6f636b75702e706e67
---

## Notion-Like Bookmark

노션을 사용하다보면 아래와 같이 북마크 기능을 통해서 OpenGraph를 활용하여 URL 미리보기를 제공하는 기능이 있다.

하지만, Jekyll에서는 기본적으로 제공하지 않기 때문에, 직접 구현해야 한다.

마크다운에서 문법을 지원한다고 해도, [이것과 같이](/) 글자에 하이퍼링크를 거는게 전부이다.

따라서, 아래와 같이 [jekyll-linkpreview](https://github.com/ysk24ok/jekyll-linkpreview)를 활용하여 Jekyll에서 URL 미리보기를 구현해보았다.

{% linkpreview "https://github.com/ysk24ok/jekyll-linkpreview" %}

## jekyll-linkpreview


### jekyll-linkpreview 설치법

설치법은 디게 간단하다.

1. Gemfile에 `gem 'jekyll-linkpreview'` 추가
```ruby
group :jekyll_plugins do
  gem 'jekyll-linkpreview'
end 
```

2. `_config.yml`에 `jekyll-linkpreview` 추가
```yaml
plugins:
  - jekyll-linkpreview
```

3. bundle install 실행 
```bash
bundle install
```

4. css 파일 추가

리드미의 설명에 따라 [기본 CSS 파일](https://github.com/ysk24ok/jekyll-linkpreview/blob/master/assets/css/linkpreview.css)을 추가해야 한다.

필자은 CSS를 적당히 수정하여 사용했다. [CSS 링크](https://github.com/cmsong111/blog/blob/main/assets/css/linkpreview.css)에서 확인할 수 있다.


### jekyll-linkpreview 사용법

설치를 완료했다면, 사용법은 간단하다. 

다음과 같이 Liquid 문법에 따라 다음과 같이 작성하면 된다

```md
{% raw %}{% linkpreview "https://github.com/" %}{% endraw %}
```
그럼 아래와 같이 URL 미리보기 위젯이 나타나게 된다!

{% linkpreview "https://github.com/" %}

## Chirpy Toc(목차)와의 충돌

하지만, linkpreview를 사용하게 되면, 목차(toc)와 충돌이 발생한다.

jekyll-linkpreview의 렌더링된 HTML 소스 코드를 확인 해보면 해당 제목이 `<h2>` 태그로 감싸져 있는 것을 확인할 수 있다.

Chirpy 블로그의 경우, 목차(toc)는 `<h2>` ~ `<h3>` 태그를 기준으로 생성되기 때문에, 프리뷰의 제목이 목차로 생성되는 것이다.

![적용 전](/assets/images/2025-03-04/toc-error.png)

SEO 적으로도 좋지 않기 때문에, 해당 태그를 제거해야 한다.

### Custom Template을 통한 H2 태그 제거

[jekyll-linkpreview](https://github.com/ysk24ok/jekyll-linkpreview)의 경우, 커스텀 템플릿을 지원하기 때문에, 해당 기능을 활용하여 H2 태그를 제거할 수 있다.
따라서, `_includes` 폴더에 `linkpreview.html` 파일을 생성한다.

해당 파일의 경우 지킬 문법을 사용하기 때문에, Liquid 문법을 사용하여 작성해야 한다.

필자는 다음과 같이 설정했다

```html
{% raw %}<div class="jekyll-linkpreview-wrapper">
  <div class="jekyll-linkpreview-wrapper-inner">
    <div class="jekyll-linkpreview-content">
      <div class="jekyll-linkpreview-body">
        <div class="jekyll-linkpreview-title">
          <a href="{{ url }}" target="_blank">{{ title }}</a>
        </div>
        {% if description %}
          <div class="jekyll-linkpreview-description">{{ description }}</div>
        {% endif %}
        <div class="jekyll-linkpreview-footer">
          <a href="{{ url }}" target="_blank">{{ domain }}</a>
        </div>
      </div>
    </div>
  </div>
  {% if image %}
    <div class="jekyll-linkpreview-image" style="background-image: url('{{ image }}');"></div>
  {% endif %}
</div>{% endraw %}
```

위와 같이 작성하면, H2 태그가 제거된 것을 확인할 수 있다.

그럼 지금보는 목차와 같이 우측에 프리뷰에 대한 목차가 생성되지 않는다.

적용된 프로젝트의 풀 소스코들 확인하고 싶으면 아래 레포지토리를 확인해라

{% linkpreview "https://github.com/cmsong111/blog" %}