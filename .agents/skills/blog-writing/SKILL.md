---
name: blog-writing
description: >-
  남주의 커밋로그(namju.kim) 기술 블로그 포스트를 작성·수정·리팩토링할 때 사용하는 표준 스킬.
  작성자 페르소나, 톤앤매너, Front Matter·카테고리 규격, Mermaid 문법, 이미지 보안·크롭 규칙,
  상세 기술 글쓰기 체크리스트 및 QA 검증 절차를 포함합니다.
---

# 남주의 커밋로그 글쓰기 스킬 (`blog-writing`)

블로그 포스트를 새로 작성하거나 기존 포스트를 수정·보강할 때는 반드시 먼저 [`references/writing-tone.md`](./references/writing-tone.md)를 읽고 작성자(김남주)의 페르소나, 문체, 템플릿, 심화 집필 체크리스트를 100% 준수합니다.

## 1. 작성 워크플로우

1. **톤앤매너 장착**: [`references/writing-tone.md`](./references/writing-tone.md) 확인 (경어체 `~합니다/~습니다`, 담백한 엔지니어링 제목, 심화 체크리스트)
2. **경로 & Front Matter 생성**: `_posts/{대분류}/{중분류}/YYYY-MM-DD-kebab-case-title.md`
3. **시각 자료 & 다이어그램 구성**: Mermaid 다이어그램 + 필요 시 실제 실행 화면 스크린샷(`assets/images/YYYY-MM-DD/`)
4. **본문 작성**: 공식 문서 기반, `Why / Trade-off` + 내부 동작 원리(One Layer Deeper) + 복붙 가능한 최소 재현 코드 + 운영 함정
5. **QA 검증**: 로컬 빌드(`jekyll build`), `htmlproofer`, Mermaid 정적 문법 검사 수행 (커밋/푸시는 사용자 영역)

## 2. Front Matter 및 카테고리 규격

- `_plugins/category-folder-hook.rb`가 폴더 경로로 `categories`를 자동 주입하므로 **Front Matter에서 `categories`는 생략하고 `tags`만 작성**합니다.
- 표준 카테고리 폴더:
  - `AI > Concept`: `_posts/AI/Concept/`
  - `Blog > Jekyll`: `_posts/Blog/Jekyll/`
  - `Book`: `_posts/Book/`
  - `Dev`: `_posts/Dev/`
  - `Docker > Compose / Container / Image / Network`: `_posts/Docker/{중분류}/`
  - `Home Server > Containers`: `_posts/Home Server/Containers/`
  - `Java > Standard`: `_posts/Java/Standard/`
  - `Java > Swing`: `_posts/Java/Swing/`
  - `Spring > Feature`: `_posts/Spring/Feature/`
  - `Spring > Spring-AI`: `_posts/Spring/Spring-AI/`
  - `Spring > Wanted-Challenge`: `_posts/Spring/Wanted-Challenge/`
  - `Vite`: `_posts/Vite/`

```yaml
---
title: "기술 키워드와 적용 대상·목적이 명확한 담백한 제목"
description: "검색엔진 및 SNS 카드용 1~2문장 요약"
date: YYYY-MM-DD HH:MM:SS +0900
tags: [태그1, 태그2, 태그3]
mermaid: true # 본문에 mermaid 코드 블록이 있을 때만 true
image:
  path: /assets/images/YYYY-MM-DD/thumbnail.png # 로컬 저장 시 프로덕션 jsDelivr CDN 자동 적용
  alt: 대표 썸네일 설명
---
```

> **제목 금지어**: 의문형(`~할 때?`, `~죽는 이유`) 및 과장·어그로 표현(`완벽 해결`, `초고속`, `원클릭`, `~의 모든 것`, `치명적 위험`)을 사용하지 않습니다.

## 3. 이미지·외부 링크 규칙

- 외부 CDN 핫링크 대신 `assets/images/YYYY-MM-DD/`에 로컬 저장하여 프로덕션 jsDelivr CDN을 태웁니다.
- **코드 이미지 캡처 금지**: 모든 코드·설정·명령어는 마크다운 백틱 코드 블록으로 작성합니다.
- **타이트 크롭 & 보안 마스킹**: 불필요한 여백을 제거하고, API 키(`AIza...`, `sk-...`, 토큰 등)와 개인정보는 이미지에서 반드시 마스킹하며 코드에도 환경 변수(`${API_KEY}`) 형태로 표기합니다.
- 외부 참고 링크는 `{% linkpreview "URL" %}` 문법을 적극 활용합니다.

## 4. Mermaid 다이어그램 문법 수칙

1. **노드 라벨 특수문자 인용**: 괄호 `()`, 대괄호 `[]`, 중괄호 `{}`, 슬래시 `/`, 콜론 `:`, `&`, `,` 등이 포함되면 반드시 큰따옴표(`A["Docker Engine (/var/run/docker.sock)"]`)로 감쌉니다.
2. **화살표·엣지 라벨**: `flowchart`에서는 `-->`, `-.->`, `==>`만 사용하고, 특수문자·공백이 있는 엣지 라벨은 `-->|"HTTP/WS 프록시"|`처럼 큰따옴표로 감쌉니다.
3. **서브그래프**: 화살표 목적지로 서브그래프 ID 대신 내부 노드 ID를 지정하고, 서브그래프에 직접 `class`를 부여하지 않습니다.
4. **스타일링 HTML 태그 배제**: `<font>`, `<div>`, `<span>`을 사용하지 않습니다(줄바꿈은 `\n` 또는 `<br/>`만 허용).
5. **Front Matter 일치**: `mermaid` 블록이 있으면 `mermaid: true`, 없으면 생략합니다.

## 5. 품질 검증 (QA)

```bash
# 1. 사이트 빌드 검증 (Dev Container / Ruby 3.4 환경)
bundle exec jekyll build -d /tmp/_site

# 2. 내부 링크·이미지 깨짐 검사
bundle exec htmlproofer /tmp/_site \
  --disable-external \
  --ignore-urls "/^http:\/\/127.0.0.1/,/^http:\/\/0.0.0.0/,/^http:\/\/localhost/"

# 3. Mermaid 노드 따옴표 누락 전수 검사
python3 -c "
import glob, re
for f in glob.glob('_posts/**/*.md', recursive=True):
    content = open(f, encoding='utf-8').read()
    for block in re.findall(r'\`\`\`mermaid\n(.*?)\n\`\`\`', content, re.DOTALL):
        for line in block.split('\n'):
            line = line.strip()
            if re.search(r'[A-Za-z0-9_]+\[[^\"\n]*[\(\)\/:][^\"\n]*\]', line):
                print(f'[Mermaid Syntax Error] {f}: {line}')
"
```
