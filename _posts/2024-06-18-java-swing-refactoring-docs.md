---
title: Dokka를 활용한 코드 문서화 (with 배포)
description: Dokka를 활용한 코드 문서화 (with 배포)
date: 2024-06-18 12:00:00 +0000
categories: [Refactoring Project, Java-Swing]
tags: [Java, Swing, Refactoring, Dokka]
mermaid: true
image:
  path: https://velog.velcdn.com/images/cmsong111/post/24a8b41a-49a7-4813-87f2-fe4b172fa200/image.png
---

# Dokka를 활용한 코드 문서화 (with 배포)

프로젝트를 진행하다 보면 팀원 간의 코드 공유나 코드를 이해하기 위해 문서화가 필요할 때가 있습니다. 주석을 통해 문서화하는 것도 좋지만, 문서화 도구를 사용하면 더욱 효율적으로 작업할 수 있습니다. 일반적으로 Java에서는 Javadoc을, Kotlin에서는 KDoc을 사용합니다. 이번에는 Kotlin에서 사용할 수 있는 Dokka를 살펴보겠습니다.

## Dokka란?

Dokka는 Kotlin을 위한 문서화 도구로, Kotlin 코드를 HTML, Markdown, Javadoc 등 다양한 형식으로 변환할 수 있습니다. Gradle 플러그인 형태로 제공되며, 쉽게 프로젝트에 적용할 수 있습니다.

## Dokka 설치

Dokka를 사용하기 위해서는 Gradle 플러그인을 설치해야 합니다. `build.gradle` 파일에 아래와 같이 추가합니다.

```gradle
plugins {
    id "org.jetbrains.dokka" version "1.9.10"
}
```

현재(2024년 6월 15일 기준) Dokka와 Jackson의 버전 간 충돌 문제가 있습니다. 따라서 Jackson의 버전을 2.15.3으로 고정해야 합니다. (dependency 근처에 추가해 주세요.)

```gradle
configurations.matching { it.name.startsWith("dokka") }.configureEach {
    resolutionStrategy.eachDependency {
        if (requested.group.startsWith("com.fasterxml.jackson")) {
            useVersion("2.15.3")
        }
    }
}
```

## Dokka 사용

Dokka를 사용하려면 다음 명령어를 입력하면 됩니다.

```shell
./gradlew dokkaHtml
```

이 명령어를 입력하면 `build/dokka/html` 디렉토리에 문서화된 HTML 파일이 생성됩니다. Markdown 파일로 변환하고 싶다면 다음과 같이 입력합니다.

```shell
./gradlew dokkaMarkdown
```

## 생성 결과

![생성 결과](https://velog.velcdn.com/images/cmsong111/post/1b7aef35-d7af-4bb1-b53b-e5cf2df327ad/image.png)

개발자 모드로 접속하면 왼쪽 사이드에 목차가 표시됩니다. 그러나 파일 기반으로 접속하기 때문에 정상적으로 작동하지 않습니다. 웹 서버를 통해 확인하면 정상적으로 작동합니다.

_아래에서 쉽게 GitHub Pages에 배포하는 방법을 소개하겠습니다._

## 설명(주석) 작성하기

Dokka를 사용하기 위해서는 주석을 작성해야 합니다. 주석은 JavaDoc과 유사하게 작성하면 됩니다.

```kotlin
/**
 * 이 클래스는 사람을 나타내는 클래스입니다.
 * @property name 사람의 이름
 * @property age 사람의 나이
 */
class Person(
    val name: String,
    val age: Int
) {
    /**
     * 이 함수는 사람의 이름을 출력합니다.
     */
    fun printName() {
        println(name)
    }
}
```

패키지에 대한 설명은 `docs.md` 파일에 작성합니다.

```markdown
# 패키지명

패키지에 대한 설명을 작성합니다.
```

#### 예시

```markdown
# Module TODO Swing Application

해당 문서는 Swing을 이용한 Java, Kotlin 어플리케이션 개발 방법에 대한 문서입니다.

# Package org.example

Main 클래스가 존재하는 패키지입니다.

# Package org.example.common

공통적으로 사용되는 클래스들이 존재하는 패키지입니다. Font, Color, Dimension 등의 상수값과 공통적으로 사용되는 메소드를 정의합니다.
```

## Dokka 배포 (GitHub Pages)

Dokka로 문서화된 결과를 GitHub Pages에 배포하려면 다음과 같이 진행합니다. (Gradle 기준으로 작성하였습니다.)

### 1. GitHub 액션 설정

`.github/workflows/dokka.yml` 파일을 생성하고 다음과 같이 작성합니다.

```yml
name: Docs CI
# refactor 브랜치에 push 이벤트가 발생하면 실행
on:
  push:
    branches: ["refactor"]

jobs:
  docs:
    runs-on: ubuntu-latest

    steps:
        # Java 17 환경 설정
      - uses: actions/checkout@v4
      - name: Set up JDK 17
        uses: actions/setup-java@v4
        with:
          java-version: "17"
          distribution: "temurin"

      - name: permissions
        run: chmod +x gradlew

        # Dokka HTML 문서 생성
      - name: Build Documentation
        run: ./gradlew dokkaHtml

        # GitHub Pages에 배포 (docs 브랜치)
      - name: Deploy Documentation to GitHub Pages
        uses: JamesIves/github-pages-deploy-action@v4
        with:
          BRANCH: docs
          FOLDER: build/dokka/html
```

### 2. GitHub Pages 설정

1. GitHub 저장소의 Settings -> Pages로 이동합니다.
2. Source를 docs 브랜치로 설정합니다. GitHub 액션에서 자동으로 라이브러리를 생성합니다.
3. /(root)로 설정합니다.
4. Save를 클릭합니다.

![](https://velog.velcdn.com/images/cmsong111/post/41111765-51a3-4bed-9164-b2e6e4fb26f0/image.png)

### 3. 확인

GitHub Action 탭에서 배포 과정을 확인할 수 있습니다.
![](https://velog.velcdn.com/images/cmsong111/post/cbf18b65-3608-48b9-b883-28416b62e09f/image.png)

배포가 완료되면 docs 브랜치에 문서가 push된 것을 확인할 수 있습니다. 또한, docs에 배포된 링크를 통해 문서를 확인할 수 있습니다.

#### GitHub Pages 배포 결과

이번에 리팩토링 중인 프로젝트에서 Dokka를 사용하여 문서화한 결과입니다.

[https://cmsong111.github.io/Restaurant-information-system/](https://cmsong111.github.io/Restaurant-information-system/)

![](https://velog.velcdn.com/images/cmsong111/post/aa3bc70a-7163-48a7-8e36-3bb35a0ddf43/image.png)

위에서 사이드바에 나타나지 않던 목차가 정상적으로 표시되는 것을 확인할 수 있습니다.

### 팁

GitHub README를 작성할 때, 아래와 같이 배포된 링크를 추가하면 좋습니다.

[![Dokka](https://img.shields.io/badge/Kdoc-7F52FF.svg?style=for-the-badge&logo=kotlin&logoColor=white)](https://cmsong111.github.io/Restaurant-information-system/)

```markdown
[![Dokka](https://img.shields.io/badge/Kdoc-7F52FF.svg?style=for-the-badge&logo=kotlin&logoColor=white)](https://cmsong111.github.io/Restaurant-information-system/)
```
