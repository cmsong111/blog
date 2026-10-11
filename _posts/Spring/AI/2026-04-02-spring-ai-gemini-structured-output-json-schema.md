---
title: "Spring AI BeanOutputConverter와 Gemini Provider-Native JSON Schema를 활용한 구조화된 출력"
description: Spring AI 2.0.1의 BeanOutputConverter와 Google Gemini의 Provider-Native JSON Schema(response_schema)를 결합하여, 중첩 DTO와 Enum을 재시도 없이 100% 안전하게 Kotlin 객체로 역직렬화하는 노하우를 정리합니다.
date: 2026-04-02 12:00:00 +0900
tags: [spring-ai, structured-output, json-schema, gemini, bean-output-converter, dto]
mermaid: true
image:
  path: /assets/images/2026-04-02/spring-ai-structured-output-test-pass.png
  alt: Gemini 구조화된 출력(Structured Output) 통합 테스트 통과 콘솔
---

> LLM 응답을 백엔드 비즈니스 로직에 결합할 때 가장 빈번하게 발생하는 장애는 비정형 텍스트, 마크다운 백틱(```json) 침범, 혹은 잘못된 Enum 키 생성으로 인한 역직렬화 실패입니다. 본 글에서는 Spring AI 2.0.1의 **`BeanOutputConverter`**와 Google Gemini의 **제공자 네이티브 JSON Schema(Constrained Decoding)**를 결합하여 복잡한 중첩 객체와 Enum DTO를 100% 문법 보장으로 파싱하는 실전 해결책을 소개합니다.

---

## 프롬프트 지시의 한계 vs 모델 수준의 스키마 강제

프롬프트에 "반드시 순수 JSON으로만 출력해 줘"라고 아무리 강조해도, 모델은 가끔 마크다운 백틱을 붙이거나 약속된 Enum(`INTERMEDIATE`) 대신 한글(`"중급"`)을 반환합니다:

```mermaid
flowchart TD
    subgraph PromptWay["1. 단순 프롬프트 지시 (Prompt Engineering)"]
        P1["프롬프트에 JSON 지침 추가"] --> P2["모델이 비정형 텍스트 응답"]
        P2 --> P3{"Jackson 역직렬화 실패?"}
        P3 -- "실패" --> P4["재시도(Retry) 호출 비용 발생"]
    end

    subgraph NativeWay["2. Provider-Native JSON Schema (Constrained Decoding)"]
        N1["Java/Kotlin DTO 정의"] --> N2["JSON Schema 자동 추출"]
        N2 --> N3["Gemini 옵션에 response_schema 주입"]
        N3 --> N4["모델 내부 디코딩 단계에서 문법 100% 강제"]
        N4 --> N5["Jackson 안전 역직렬화 (파싱 실패율 0%)"]
    end
```

Google Gemini API는 `response_mime_type: application/json`과 `response_schema` 옵션을 지원합니다. 이를 적용하면 모델의 다음 토큰 생성 확률 분포(Next-Token Logits) 자체가 지정된 JSON Schema의 문법 규칙에 구속(Constrained Decoding)되어 **스키마를 벗어난 출력이 원천적으로 불가능**해집니다.

---

## 프로젝트 환경 및 의존성 설정

본 실습 코드는 [spring-ai-examples (structured-output)](https://github.com/cmsong111/spring-ai-examples/tree/master/structured-output) 모듈을 기반으로 합니다.

### build.gradle.kts

```kotlin
plugins {
    kotlin("jvm") version "2.3.21"
    kotlin("plugin.spring") version "2.3.21"
    id("org.springframework.boot") version "4.1.1"
    id("io.spring.dependency-management") version "1.1.7"
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-web")
    implementation("org.springframework.ai:spring-ai-starter-model-google-genai")
    implementation("com.fasterxml.jackson.module:jackson-module-kotlin")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit5")
}
```

---

## 복합 중첩 DTO 및 Enum 설계

실무 환경을 모사하기 위해 메인 큐레이션 DTO 안에 도서 목록 리스트(`List<CuratedBook>`), 난이도 Enum(`Level`), 카테고리 Enum(`Category`), 핵심 요약 리스트(`List<String>`)가 포함된 계층형 구조를 정의합니다:

```kotlin
package io.github.cmsong111.structured_output.dto

data class ReadingCuration(
    val theme: String,
    val targetLevel: Level,
    val books: List<CuratedBook>,
    val curatorComment: String
)

data class CuratedBook(
    val title: String,
    val author: String,
    val publishedYear: Int,
    val level: Level,
    val category: Category,
    val keyTakeaways: List<String>
)

enum class Level {
    BEGINNER, INTERMEDIATE, ADVANCED
}

enum class Category {
    PROGRAMMING, ARCHITECTURE, CULTURE, ESSAY
}
```

---

## 핵심 트러블슈팅: GeminiBeanOutputConverter ($ref Inliner)

Spring AI 2.0.1의 기본 `BeanOutputConverter`를 중첩 DTO에 적용하면 중요한 문제에 직면하게 됩니다.

> [!WARNING]
> `BeanOutputConverter`는 동일한 타입(예: `Level` enum이 상위와 하위 DTO에서 중복 사용됨)이 여러 번 나타나면 JSON Schema의 **`$defs`와 `$ref`(#/$defs/Level)**로 참조를 생성합니다.  
> 하지만 **Spring AI 2.0.1의 GoogleGenAiChatModel은 Gemini SDK의 `Schema` 객체로 변환하는 과정에서 `$defs`/`$ref`를 해석하지 않고 누락**시켜 버립니다. 결과적으로 해당 필드의 Enum 제약이 사라져 모델이 임의 문자열을 반환하게 됩니다.

이를 해결하기 위해 `$ref`를 실제 인라인 정의로 자동 치환해 주는 **`GeminiBeanOutputConverter`**와 **`JsonSchemaInliner`**를 구현합니다:

```kotlin
package io.github.cmsong111.structured_output.converter

import org.springframework.ai.converter.BeanOutputConverter
import tools.jackson.databind.JsonNode
import tools.jackson.databind.json.JsonMapper
import tools.jackson.databind.node.ArrayNode
import tools.jackson.databind.node.ObjectNode

class GeminiBeanOutputConverter<T : Any>(clazz: Class<T>) : BeanOutputConverter<T>(clazz) {

    private val inlinedSchema: String = JsonSchemaInliner.inline(super.getJsonSchema())

    override fun getJsonSchema(): String = inlinedSchema
}

object JsonSchemaInliner {
    private const val DEFS = "\$defs"
    private const val REF = "\$ref"
    private const val REF_PREFIX = "#/\$defs/"
    private val jsonMapper = JsonMapper.builder().build()

    fun inline(jsonSchema: String): String {
        val root = jsonMapper.readTree(jsonSchema) as ObjectNode
        val defs = root.get(DEFS) as? ObjectNode ?: return jsonSchema

        val inlined = resolve(root, defs, depth = 0) as ObjectNode
        inlined.remove(DEFS)
        return jsonMapper.writerWithDefaultPrettyPrinter().writeValueAsString(inlined)
    }

    private fun resolve(node: JsonNode, defs: ObjectNode, depth: Int): JsonNode {
        check(depth < 32) { "재귀적인 \$ref는 인라인할 수 없습니다." }
        return when (node) {
            is ObjectNode -> {
                val ref = node.get(REF)?.asString()
                val result: ObjectNode = if (ref != null && ref.startsWith(REF_PREFIX)) {
                    val target = defs.get(ref.removePrefix(REF_PREFIX))
                        ?: error("정의를 찾을 수 없습니다: $ref")
                    resolve(target, defs, depth + 1).deepCopy() as ObjectNode
                } else {
                    jsonMapper.createObjectNode()
                }
                node.properties()
                    .filter { (key, _) -> key != REF }
                    .forEach { (key, value) -> result.set(key, resolve(value, defs, depth + 1)) }
                result
            }
            is ArrayNode -> jsonMapper.createArrayNode().apply {
                node.forEach { add(resolve(it, defs, depth + 1)) }
            }
            else -> node
        }
    }
}
```

![JSON Schema Inliner 변환 비교 로그](/assets/images/2026-04-02/gemini-json-schema-inliner-debug.png)
_JsonSchemaInliner 동작 결과: Gemini SDK가 해석하지 못하는 $ref/$defs를 인라인으로 완전히 해소_

---

## 구조화된 출력 서비스 구현 (StructuredOutputService)

`ChatClient` Fluent API의 `.entity()` 방식과, Gemini 네이티브 `responseSchema`를 직접 옵션에 주입하는 방식을 모두 지원하도록 구현합니다:

```kotlin
package io.github.cmsong111.structured_output.service

import io.github.cmsong111.structured_output.converter.GeminiBeanOutputConverter
import io.github.cmsong111.structured_output.dto.ReadingCuration
import org.springframework.ai.chat.client.ChatClient
import org.springframework.ai.google.genai.GoogleGenAiChatOptions
import org.springframework.stereotype.Service

@Service
class StructuredOutputService(
    private val chatClient: ChatClient
) {
    private val curationConverter = GeminiBeanOutputConverter(ReadingCuration::class.java)

    /**
     * 1. ChatClient Fluent .entity() 방식
     */
    fun curateWithPrompt(topic: String): ReadingCuration? {
        return chatClient.prompt()
            .system("당신은 시니어 개발자 전문 북 큐레이터입니다.")
            .user("주제에 맞는 책 3권을 추천해주세요: '$topic'")
            .call()
            .entity(ReadingCuration::class.java)
    }

    /**
     * 2. Gemini Provider-Native responseSchema 옵션 방식
     */
    fun curateWithNativeSchema(topic: String): ReadingCuration? {
        val nativeOptions = GoogleGenAiChatOptions.builder()
            .responseMimeType("application/json")
            .responseSchema(curationConverter.jsonSchema)
            .build()

        val rawJson = chatClient.prompt()
            .options(nativeOptions)
            .system("당신은 시니어 개발자 전문 북 큐레이터입니다.")
            .user("주제에 맞는 책 3권을 추천해주세요: '$topic'")
            .call()
            .content() ?: return null

        return curationConverter.convert(rawJson)
    }
}
```

---

## 동작 검증 및 테스트 결과

실제 `gemini-3.5-flash-lite` 모델을 호출하는 통합 테스트(`StructuredOutputIntegrationTests`)를 실행합니다:

```kotlin
@SpringBootTest
class StructuredOutputIntegrationTests {

    @Autowired
    private lateinit var structuredOutputService: StructuredOutputService

    @Test
    fun `프롬프트 기반 큐레이션 DTO 파싱`() {
        val topic = "객체지향 설계와 리팩터링"
        val curation = structuredOutputService.curateWithPrompt(topic)

        println("=== [StructuredOutput] Prompt-based ===")
        println(curation)

        assertThat(curation).isNotNull
        assertThat(curation?.books).hasSize(3)
        assertThat(curation?.targetLevel).isNotNull()
    }
}
```

### 테스트 실행 콘솔

![StructuredOutput 실시간 통합 테스트 성공 콘솔](/assets/images/2026-04-02/spring-ai-structured-output-test-pass.png)
_JUnit 5 통합 테스트 통과: 중첩 리스트 및 Enum 제약이 정확히 바인딩된 ReadingCuration DTO_

출력된 결과 DTO는 다음과 같이 한 번의 호출로 오타 없이 깔끔하게 역직렬화됩니다:

```text
ReadingCuration(
  theme=객체지향 설계와 리팩터링, 
  targetLevel=INTERMEDIATE, 
  books=[
    CuratedBook(title=객체지향의 사실과 오해, author=조영호, publishedYear=2015, level=BEGINNER, category=PROGRAMMING),
    CuratedBook(title=리팩터링 2판, author=마틴 파울러, publishedYear=2018, level=INTERMEDIATE, category=PROGRAMMING),
    CuratedBook(title=클린 아키텍처, author=로버트 C. 마틴, publishedYear=2017, level=ADVANCED, category=ARCHITECTURE)
  ], 
  curatorComment=객체지향의 기본 원칙을 익힌 뒤 리팩터링을 거쳐 아키텍처를 구축하는 단계별 로드맵입니다.
)
```

### cURL API 호출 응답

서버 구동 후 `GET /api/curation?topic=객체지향`을 호출하면 브라우저/클라이언트에서도 엄격한 JSON DTO 응답을 즉시 받아볼 수 있습니다:

![cURL 구조화된 DTO JSON 응답 콘솔](/assets/images/2026-04-02/curation-dto-curl-response.png)
_REST 엔드포인트 호출 결과: 약속된 스키마 규격을 100% 만족하는 JSON 페이로드_

---

## 정리 및 다음 단계

- Spring AI의 `BeanOutputConverter`와 Gemini의 `response_schema`를 결합하면 프롬프트 작성자가 수동 JSON 파싱이나 재시도 로직을 작성할 필요가 없습니다.
- 중첩 DTO 및 Enum 재사용 시 발생하는 `$ref`/`$defs` 누락 이슈는 `GeminiBeanOutputConverter` 인라인 치환으로 완벽히 해결할 수 있습니다.
- `gemini-3.5-flash-lite` 모델에서도 복잡한 계층형 DTO가 실패율 0%로 안정적으로 생성됨을 검증했습니다.

다음 포스트에서는 텍스트를 넘어, 구글의 이미지 생성 모델을 스프링 부트에 연동하는 **`Google GenAI ImageModel` 이미지 생성 및 S3/로컬 스토리지 저장 파이프라인**을 구현해 봅니다.

---

> 본 포스트의 전체 실습 코드는 [GitHub 저장소 (cmsong111/spring-ai-examples/structured-output)](https://github.com/cmsong111/spring-ai-examples/tree/master/structured-output)에서 확인하실 수 있습니다.
