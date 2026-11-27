---
title: "EditorConfig와 ktlint로 Kotlin 프로젝트 코드 스타일 자동화하기"
description: "Kotlin 프로젝트에서 EditorConfig와 ktlint Gradle 플러그인, GitHub Actions CI를 연동해 코드 스타일 검사와 포맷팅을 자동화하는 실무 설정을 정리합니다."
date: 2024-11-04 12:00:00 +0900
tags: [kotlin, gradle, ci-cd, dx]
---

> 코드 리뷰의 스타일 논쟁을 줄이기 위해 `.editorconfig`와 `ktlint`로 Kotlin 코드 스타일을 자동화하고 GitHub Actions CI까지 연동하는 실무 설정을 정리합니다.

> Kotlin 1.9+, Gradle(Kotlin DSL), IntelliJ IDEA, `org.jlleitschuh.gradle.ktlint` 12.1.x(ktlint 1.x) 기준입니다.
{: .prompt-info }

팀 프로젝트 PR 리뷰에서 들여쓰기, 와일드카드 import, 파일 끝 개행 누락 같은 스타일 지적에 시간이 많이 쓰입니다. 문서로만 규칙을 정하면 매번 지키기 어려우므로 에디터와 CI가 기계적으로 강제하도록 구성하는 편이 낫습니다.

## EditorConfig와 ktlint의 역할 분담

`.editorconfig`는 IDE가 코드를 작성하거나 재정렬(`Reformat Code`)할 때 따르는 기준 파일입니다. 반면 `ktlint`는 Kotlin 공식 컨벤션에 따라 코드를 정적 검사하고 자동 포맷팅하는 린터입니다.

에디터 설정만 두면 정렬을 생략한 커밋을 막을 수 없고, `ktlint`만 쓰면 IDE 자동 정렬 결과와 충돌할 수 있습니다. ktlint는 `.editorconfig`를 설정 소스로 직접 읽으므로 두 도구를 함께 두면 **단일 설정 파일(SSOT)**로 IDE와 빌드의 규칙을 일치시킬 수 있습니다.

| 구분 | `.editorconfig` | `ktlint` (`ktlint-gradle`) |
| :--- | :--- | :--- |
| **역할** | IDE 포맷팅 기준 정의 | 정적 검사 및 일괄 포맷팅 |
| **동작 시점** | 코드 작성·IDE 정렬 시 | Gradle 실행·CI 빌드 시 |
| **강제력** | 없음 | 높음 (위반 시 빌드 실패) |
| **커버 범위** | 인코딩, 줄바꿈, 들여쓰기, import | Kotlin 컨벤션 규칙 전반 |

## .editorconfig 설정과 IntelliJ 자동 연동

프로젝트 루트에 `.editorconfig`를 두면 IntelliJ IDEA가 별도 플러그인 없이 자동 인식해 로컬 IDE 설정보다 우선 적용합니다. 최상단에 `root = true`를 선언해 상위 폴더 설정이 섞이지 않도록 막아 둡니다.

실제 Spring Boot + Kotlin 백엔드 프로젝트에서 사용 중인 `.editorconfig` 설정입니다.

```ini
# /.editorconfig
root = true

[*]
charset = utf-8
end_of_line = lf
indent_style = space
indent_size = 4
insert_final_newline = true

[*.{kt,kts}]
ij_kotlin_code_style_defaults = KOTLIN_OFFICIAL
ktlint_code_style = intellij_idea
ktlint_function_signature_body_expression_wrapping = multiline
ktlint_standard_function-expression-body = disabled

ktlint_standard_indent = disabled
ktlint_standard_string-template-indent = disabled

# 와일드카드 import 전면 비활성화
ij_kotlin_name_count_to_use_star_import = 2147483647
ij_kotlin_name_count_to_use_star_import_for_members = 2147483647
ij_kotlin_packages_to_use_import_on_demand = unset
```

- **`charset`, `end_of_line`, `insert_final_newline`**: OS별 줄바꿈(CRLF/LF) 차이와 파일 끝 개행 누락으로 생기는 불필요한 Git diff를 방지합니다.
- **`ktlint_code_style = intellij_idea`**: `ktlint_official` 스타일은 일부 줄바꿈 규칙에서 IntelliJ 정렬(`Cmd + Option + L`)과 어긋날 수 있습니다. `intellij_idea`로 맞춰 두면 IDE 정렬 직후 `ktlintCheck`를 그대로 통과합니다.
- **와일드카드 import 차단**: `ij_kotlin_name_count_to_use_star_import`를 `2147483647`로 두고 `ij_kotlin_packages_to_use_import_on_demand = unset`을 지정하면 `.*` 자동 축약을 막아 코드 리뷰 가독성과 ktlint 검사를 동시에 챙길 수 있습니다.

## Gradle ktlint 플러그인 설정과 태스크 활용

`build.gradle.kts`에 `org.jlleitschuh.gradle.ktlint` 플러그인을 추가하면 팀원 모두가 별도 CLI 설치 없이 동일한 버전의 ktlint를 실행할 수 있습니다.

```kotlin
// /build.gradle.kts
plugins {
    kotlin("jvm") version "1.9.25"
    id("org.jlleitschuh.gradle.ktlint") version "12.1.1"
}

ktlint {
    verbose.set(true)
    outputToConsole.set(true)
    filter {
        exclude("**/generated/**")
    }
}
```

일상적으로 사용하는 Gradle 태스크는 두 가지입니다.

```bash
# 스타일 위반 여부만 검사 (수정하지 않음)
./gradlew ktlintCheck

# 자동 수정 가능한 스타일 위반을 일괄 포맷팅
./gradlew ktlintFormat
```

이 플러그인은 Gradle 기본 `check` 태스크에 `ktlintCheck`를 자동으로 의존 연결합니다. 따라서 `./gradlew check`나 `./gradlew build`를 실행할 때 테스트와 함께 스타일 검증이 자동으로 수행됩니다. 로컬에서는 `ktlintFormat`으로 먼저 정리한 뒤, 수동 수정이 필요한 위반이 남았는지 `ktlintCheck`로 확인하는 흐름이 깔끔합니다.

## GitHub Actions CI 게이트 연동

로컬에서 포맷팅을 깜빡해도 PR 단계에서 차단되도록 CI 워크플로우에 `./gradlew ktlintCheck`를 추가합니다. 테스트보다 먼저 실행하면 스타일 위반 시 빠르게 실패(Fail-Fast)해 CI 자원을 아낄 수 있습니다.

```yaml
# /.github/workflows/ci-cd.yaml
name: CI Pipeline

on:
  push:
    branches: ['**']
  pull_request:
    branches: [main]

jobs:
  test:
    name: Lint & Test
    runs-on: ubuntu-24.04

    steps:
      - uses: actions/checkout@v4

      - name: Set up JDK 21
        uses: actions/setup-java@v4
        with:
          java-version: '21'
          distribution: 'temurin'

      - name: Setup Gradle
        uses: gradle/actions/setup-gradle@v4

      - name: Check Lint
        run: ./gradlew ktlintCheck

      - name: Run Tests
        run: ./gradlew test
```

위반 사항이 있으면 CI 로그에 파일 위치와 규칙 ID가 그대로 출력됩니다.

```text
> Task :ktlintMainSourceSetCheck FAILED
/src/main/kotlin/org/project/domain/OrderService.kt:3:1: Wildcard import (standard:no-wildcard-imports)
/src/main/kotlin/org/project/domain/OrderService.kt:18:25: Missing spacing around "=" (standard:spacing-around-operators)
```

## 실무 도입 및 운영 시 주의사항

- **기존 코드베이스 도입 시 포맷팅 커밋 분리**: 기능 PR에 `ktlintFormat` 결과를 섞으면 리뷰가 어려워지고 `git blame` 이력이 오염됩니다. 포맷팅 전용 커밋을 따로 병합하고 루트에 `.git-blame-ignore-revs` 파일을 두어 해당 커밋 해시를 등록해 두면 원래 작성자 이력을 유지할 수 있습니다.
- **`disabled_rules` 대신 개별 규칙 비활성화**: ktlint 1.0부터 기존 `disabled_rules` 프로퍼티는 제거되었습니다. 현재는 `ktlint_standard_<rule-id> = disabled` 형식으로 필요한 규칙만 선별해 끄고 주석으로 합의 이유를 남겨 두어야 합니다.
- **Git Pre-commit Hook 트레이드오프**: `./gradlew addKtlintCheckGitPreCommitHook`으로 커밋 전 자동 검사를 걸 수 있지만, 매 커밋마다 Gradle 실행 대기 시간이 생깁니다.

> Pre-commit Hook은 로컬 커밋 흐름을 끊을 수 있으므로 선택 옵션으로 두고, 최종 강제는 GitHub Actions의 `ktlintCheck`에 맡기는 편이 실무에서 더 쾌적합니다.
{: .prompt-tip }

## 참고 자료

{% linkpreview "https://editorconfig.org/" %}

{% linkpreview "https://pinterest.github.io/ktlint/latest/" %}

{% linkpreview "https://github.com/JLLeitschuh/ktlint-gradle" %}
