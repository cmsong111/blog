---
title: "Gemini 비전 및 오디오 멀티모달을 활용한 영수증 분석과 음성 회의록 요약"
description: Spring AI 2.0.1의 Media 추상화와 Google Gemini 네이티브 멀티모달을 결합하여, 별도의 OCR이나 STT 엔진 없이 영수증 이미지와 음성 회의 녹음 파일을 구조화된 DTO로 파싱하는 엔지니어링 파이프라인을 구축합니다.
date: 2026-04-16 12:00:00 +0900
tags: [spring-ai, gemini, multimodal, vision, audio, ocr, structured-output]
mermaid: true
image:
  path: /assets/images/2026-04-16/multimodal-receipt-structured-output-pass.png
  alt: Spring AI Gemini 멀티모달 비전 및 오디오 처리 테스트 통과 콘솔
---

> 비정형 시각 자료(영수증, 인보이스, 도면)나 음성 녹음(회의록, 고객 통화)을 데이터베이스에 적재 가능한 정형 데이터로 변환할 때, 과거에는 **Tesseract/Clova OCR**과 **Whisper/Google Cloud Speech-to-Text** 같은 전용 파이프라인을 앞단에 두고 그 결과를 다시 LLM에 전달하는 다단계 아키텍처를 취했습니다. 하지만 이러한 방식은 전처리 지연 시간과 중간 변환 오차가 누적되는 한계가 있습니다. Google Gemini는 텍스트뿐만 아니라 **이미지와 오디오 바이너리를 직접 이해하는 네이티브 멀티모달(Native Multimodal)** 아키텍처를 지원합니다. 본 글에서는 Spring AI 2.0.1의 **`Media` 추상화**와 **Structured Output(`entity()`)**을 결합하여 단일 요청으로 이미지와 음성을 파싱하는 실무 구현법을 살펴봅니다.

---

## 전용 OCR/STT 파이프라인 vs 네이티브 멀티모달 아키텍처 비교

전통적인 파이프라인과 Gemini 네이티브 멀티모달 파이프라인의 구조적 차이는 다음과 같습니다:

```mermaid
flowchart TD
    subgraph Traditional["기존 다단계 파이프라인"]
        T1["입력 파일 (영수증 / 회의 mp3)"] --> T2["전용 엔진 (OCR / STT)"]
        T2 --> T3["비정형 텍스트 추출"]
        T3 --> T4["LLM 텍스트 프롬프트 전달"]
        T4 --> T5["정형 JSON 변환"]
    end

    subgraph Native["Gemini 네이티브 멀티모달 파이프라인"]
        N1["입력 파일 (이미지 / 오디오)"] --> N2["Spring AI Media 바인딩"]
        N2 --> N3["Gemini 단일 호출 (generateContent)"]
        N3 --> N4["Structured Output (Receipt / MeetingMinutes DTO)"]
    end
```

- **중간 손실 제거**: 영수증의 레이아웃(품목명과 단가 사이의 행 위치), 음성의 뉘앙스나 화자 구분이 텍스트로 평탄화(Flatten)되지 않고 모델 내부 어텐션에 직접 반영됩니다.
- **인프라 간소화**: 별도의 OCR 컨테이너나 GPU 기반 STT 서빙 서버를 운영할 필요가 없으며, 단일 Gemini API 키 하나로 모든 미디어를 처리할 수 있습니다.

---

## 프로젝트 환경 및 의존성 구성

본 실습 코드는 [spring-ai-examples (multimodal)](https://github.com/cmsong111/spring-ai-examples/tree/master/multimodal) 모듈을 기반으로 합니다.

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
    implementation("tools.jackson.module:jackson-module-kotlin")

    testImplementation("org.springframework.boot:spring-boot-starter-test")
    testImplementation("org.jetbrains.kotlin:kotlin-test-junit5")
}
```

### application.yaml

Gemini의 인라인(Inline Base64) 데이터 페이로드는 단일 요청당 20MB 이하로 제한됩니다. 서블릿 멀티파트 업로드 한도를 15MB로 설정하여 대용량 파일 유입 시 서버 및 네트워크 부하를 사전에 차단합니다:

```yaml
server:
  port: 8086

spring:
  application:
    name: multimodal
  servlet:
    multipart:
      # Gemini 인라인 데이터 요청 한도(20MB)를 고려해 업로드 용량을 15MB로 제한
      max-file-size: 15MB
      max-request-size: 15MB
  ai:
    google:
      genai:
        api-key: ${SPRING_AI_GOOGLE_GENAI_API_KEY:demo-key}
        chat:
          model: gemini-3.5-flash-lite
```

---

## Spring AI의 Media 추상화와 MIME 정규화

Spring AI는 프롬프트에 멀티미디어 바이너리를 첨부할 수 있도록 `org.springframework.ai.content.Media` 클래스를 제공합니다. 하지만 실무에서 브라우저나 모바일 클라이언트가 전송하는 `Content-Type` 헤더는 운영체제나 클라이언트 라이브러리에 따라 비표준 별칭으로 전달되는 경우가 많습니다:

- MP3 오디오: `audio/mpeg` ➔ Gemini API 규격: `audio/mp3`
- WAV 오디오: `audio/x-wav`, `audio/wave`, `audio/vnd.wave` ➔ 규격: `audio/wav`
- JPEG 이미지: `image/jpg` ➔ 규격: `image/jpeg`
- 임의 전송: `application/octet-stream`인 경우 파일 확장자 기반 추론 필요

이러한 규격 불일치는 Gemini API에서 `400 INVALID_ARGUMENT: Unsupported MIME type` 에러를 유발합니다. 이를 방지하기 위해 파일 검증 및 MIME 정규화 래퍼인 `MediaFile`을 작성합니다.

### support/MediaFile.kt

```kotlin
package io.github.cmsong111.multimodal.support

import org.springframework.ai.content.Media
import org.springframework.util.MimeType
import org.springframework.web.multipart.MultipartFile

class MediaFile(
    val name: String,
    val mimeType: MimeType,
    val bytes: ByteArray,
) {

    fun toMedia(): Media {
        return Media.builder()
            .mimeType(mimeType)
            .data(bytes)
            .name(name)
            .build()
    }

    companion object {
        val SUPPORTED_IMAGE_TYPES = setOf("image/png", "image/jpeg", "image/webp", "image/heic", "image/heif")
        val SUPPORTED_AUDIO_TYPES = setOf("audio/wav", "audio/mp3", "audio/aiff", "audio/aac", "audio/ogg", "audio/flac")

        private val ALIASES = mapOf(
            "image/jpg" to "image/jpeg",
            "audio/mpeg" to "audio/mp3",
            "audio/x-wav" to "audio/wav",
            "audio/wave" to "audio/wav",
            "audio/vnd.wave" to "audio/wav",
            "audio/x-aiff" to "audio/aiff",
            "audio/x-flac" to "audio/flac",
            "audio/x-aac" to "audio/aac",
        )

        private val EXTENSIONS = mapOf(
            "png" to "image/png", "jpg" to "image/jpeg", "jpeg" to "image/jpeg",
            "webp" to "image/webp", "heic" to "image/heic", "heif" to "image/heif",
            "wav" to "audio/wav", "mp3" to "audio/mp3", "aiff" to "audio/aiff",
            "aac" to "audio/aac", "ogg" to "audio/ogg", "flac" to "audio/flac",
        )

        fun image(file: MultipartFile): MediaFile = of(file, SUPPORTED_IMAGE_TYPES)
        fun audio(file: MultipartFile): MediaFile = of(file, SUPPORTED_AUDIO_TYPES)

        fun of(file: MultipartFile, supportedTypes: Set<String>): MediaFile {
            if (file.isEmpty) {
                throw UnsupportedMediaException("빈 파일은 처리할 수 없습니다.")
            }
            val name = file.originalFilename ?: "upload"
            val mimeType = resolveMimeType(file.contentType, name)
            if (mimeType == null || mimeType !in supportedTypes) {
                throw UnsupportedMediaException(
                    "지원하지 않는 파일 형식입니다: ${file.contentType ?: name} (지원 형식: ${supportedTypes.joinToString()})"
                )
            }
            return MediaFile(name, MimeType.valueOf(mimeType), file.bytes)
        }

        fun resolveMimeType(contentType: String?, fileName: String): String? {
            val declared = contentType?.substringBefore(';')?.trim()?.lowercase()
            if (!declared.isNullOrBlank() && declared != "application/octet-stream") {
                return ALIASES[declared] ?: declared
            }
            return EXTENSIONS[fileName.substringAfterLast('.', "").lowercase()]
        }
    }
}

class UnsupportedMediaException(message: String) : RuntimeException(message)
```

![MIME 정규화 및 미디어 파이프라인 디버그 로그](/assets/images/2026-04-16/multimodal-mime-normalization-debug.png)
_그림 1. 인바운드 MIME 타입 정규화(`audio/mpeg` ➔ `audio/mp3`) 및 미지원 포맷 415 차단 로그_

---

## 영수증 비전 분석과 Structured Output

영수증 사진에서 상호명, 결제 일시, 세부 품목 목록(수량, 단가, 소계), 최종 금액을 추출하여 코틀린 DTO로 바인딩합니다.

### dto/Receipt.kt

```kotlin
package io.github.cmsong111.multimodal.dto

import com.fasterxml.jackson.annotation.JsonPropertyDescription

data class Receipt(
    @field:JsonPropertyDescription("상호명")
    val storeName: String,

    @field:JsonPropertyDescription("결제 일시 (ISO-8601, 예: 2026-10-11T12:30:00). 영수증에 없으면 null")
    val purchasedAt: String?,

    @field:JsonPropertyDescription("구매 품목 목록")
    val items: List<ReceiptItem>,

    @field:JsonPropertyDescription("최종 결제 금액")
    val totalAmount: Long,

    @field:JsonPropertyDescription("통화 코드 (ISO-4217, 예: KRW, USD)")
    val currency: String,
)

data class ReceiptItem(
    @field:JsonPropertyDescription("품목명")
    val name: String,

    @field:JsonPropertyDescription("수량")
    val quantity: Int,

    @field:JsonPropertyDescription("단가")
    val unitPrice: Long,

    @field:JsonPropertyDescription("품목 합계 금액 (수량 x 단가)")
    val amount: Long,
)
```

### MultimodalService: analyzeReceipt 구현

`ChatClient`의 Fluent API에서 `.user { ... }` 람다를 열고, 텍스트 프롬프트와 `Media` 객체를 함께 체이닝한 뒤 `.entity(Receipt::class.java)`로 변환합니다:

```kotlin
fun analyzeReceipt(image: MediaFile): Receipt {
    return chatClient.prompt()
        .user { user ->
            user.text(
                """
                첨부한 영수증 이미지에서 상호명, 결제 일시, 품목(이름/수량/단가/금액), 최종 결제 금액, 통화를 추출하세요.
                금액은 통화 기호와 쉼표를 제외한 정수로 표기하세요.
                """.trimIndent()
            ).media(image.toMedia())
        }
        .call()
        .entity(Receipt::class.java)
        ?: throw IllegalStateException("영수증 분석 결과가 비어 있습니다.")
}
```

---

## 음성 회의 녹음 파일 직접 요약과 액션 아이템 추출

일반적으로 음성 파일로부터 회의록을 만들려면 **오디오 분할 ➔ 음성인식(STT) ➔ 텍스트 전사 ➔ 텍스트 요약 프롬프트 ➔ JSON 변환**의 5단계를 거쳐야 합니다. 반면 Gemini는 음성 파일 바이너리를 직접 프롬프트에 첨부하면 화자 간의 대화 흐름을 파악하여 회의록 DTO로 즉시 응답합니다.

### dto/MeetingMinutes.kt

```kotlin
package io.github.cmsong111.multimodal.dto

import com.fasterxml.jackson.annotation.JsonPropertyDescription

data class MeetingMinutes(
    @field:JsonPropertyDescription("회의 주제를 나타내는 한 줄 제목")
    val title: String,

    @field:JsonPropertyDescription("회의 내용 요약 (3문장 이내)")
    val summary: String,

    @field:JsonPropertyDescription("발언자 또는 언급된 참석자 이름 목록")
    val participants: List<String>,

    @field:JsonPropertyDescription("결정 사항 목록")
    val decisions: List<String>,

    @field:JsonPropertyDescription("후속 조치 목록")
    val actionItems: List<ActionItem>,
)

data class ActionItem(
    @field:JsonPropertyDescription("담당자 이름. 알 수 없으면 null")
    val owner: String?,

    @field:JsonPropertyDescription("해야 할 일")
    val task: String,

    @field:JsonPropertyDescription("기한 (언급된 표현 그대로, 예: 수요일까지). 없으면 null")
    val dueDate: String?,
)
```

### MultimodalService: summarizeMeeting 구현

```kotlin
fun summarizeMeeting(audio: MediaFile): MeetingMinutes {
    return chatClient.prompt()
        .user { user ->
            user.text(
                """
                첨부한 회의 녹음을 듣고 회의록을 작성하세요.
                요약, 참석자, 결정 사항, 담당자와 기한이 있는 액션 아이템을 한국어로 정리하세요.
                """.trimIndent()
            ).media(audio.toMedia())
        }
        .call()
        .entity(MeetingMinutes::class.java)
        ?: throw IllegalStateException("회의록 생성 결과가 비어 있습니다.")
}
```

---

## HTTP 엔드포인트 및 컨트롤러 구성

Spring MVC의 `@RequestPart`를 통해 멀티파트 파일을 수신하고, 지원되지 않는 미디어 포맷은 `UnsupportedMediaException` 핸들러를 통해 `415 Unsupported Media Type`으로 응답합니다:

```kotlin
package io.github.cmsong111.multimodal.controller

import io.github.cmsong111.multimodal.dto.MeetingMinutes
import io.github.cmsong111.multimodal.dto.Receipt
import io.github.cmsong111.multimodal.service.MultimodalService
import io.github.cmsong111.multimodal.support.MediaFile
import io.github.cmsong111.multimodal.support.UnsupportedMediaException
import org.springframework.http.HttpStatus
import org.springframework.http.MediaType
import org.springframework.http.ResponseEntity
import org.springframework.web.bind.annotation.*
import org.springframework.web.multipart.MultipartFile

@RestController
@RequestMapping("/api/multimodal")
class MultimodalController(
    private val multimodalService: MultimodalService
) {

    @PostMapping("/describe", consumes = [MediaType.MULTIPART_FORM_DATA_VALUE])
    fun describe(
        @RequestPart file: MultipartFile,
        @RequestParam(defaultValue = "이 이미지를 자세히 설명해줘.") question: String,
    ): Map<String, String> {
        return mapOf("result" to multimodalService.describeImage(MediaFile.image(file), question))
    }

    @PostMapping("/receipt", consumes = [MediaType.MULTIPART_FORM_DATA_VALUE])
    fun receipt(@RequestPart file: MultipartFile): Receipt {
        return multimodalService.analyzeReceipt(MediaFile.image(file))
    }

    @PostMapping("/meeting", consumes = [MediaType.MULTIPART_FORM_DATA_VALUE])
    fun meeting(@RequestPart file: MultipartFile): MeetingMinutes {
        return multimodalService.summarizeMeeting(MediaFile.audio(file))
    }

    @ExceptionHandler(UnsupportedMediaException::class)
    fun handleUnsupportedMedia(e: UnsupportedMediaException): ResponseEntity<Map<String, String?>> {
        return ResponseEntity.status(HttpStatus.UNSUPPORTED_MEDIA_TYPE).body(mapOf("error" to e.message))
    }
}
```

---

## 대용량 미디어 처리와 비용·속도 최적화 가이드

멀티모달 바이너리를 인라인으로 직접 전달할 때 다음 사항을 반드시 고려해야 합니다:

1. **페이로드 한도 (Inline 20MB)**:
   - Spring AI의 `Media`는 내부적으로 Base64 인코딩되어 Gemini API의 `inlineData`로 직렬화됩니다.
   - Base64 변환 시 데이터 크기가 약 33% 증가하므로, 원본 파일이 15MB를 초과하면 Gemini API의 20MB 제한에 걸려 요청이 거부됩니다.
   - 20MB를 초과하는 수십 분 분량의 오디오나 고해상도 비디오는 Google AI File API(추후 연재 예정)를 사용하여 파일 URI를 참조하는 방식을 사용해야 합니다.
2. **이미지 토큰 최적화**:
   - Gemini 모델은 이미지의 해상도에 비례하여 토큰을 계산합니다. 스마트폰으로 촬영한 원본 사진(4000x3000, 8MB)은 긴 변 기준 1200~1600px로 리사이징(Thumbnailing)하여 전송해도 영수증 OCR 인식률에 차이가 없으며, 토큰 소모량과 네트워크 업로드 시간을 70% 이상 단축할 수 있습니다.
3. **오디오 포맷 최적화**:
   - 음성 인식에는 고음질 48kHz 스테레오가 불필요합니다. 16kHz 모노 MP3 또는 Opus 포맷으로 변환하면 1시간 분량의 음성도 10MB 이내로 압축되어 인라인 전송이 가능해집니다.

---

## 실행 및 검증

### 단위 테스트 및 통합 테스트

`FakeChatModel`을 이용한 Mock 단위 테스트와, Java2D로 직접 렌더링한 영수증 PNG 및 한국어 회의 녹음 WAV 샘플을 사용한 통합 테스트를 실행합니다:

```bash
./gradlew :multimodal:test
```

![멀티모달 영수증 및 오디오 요약 테스트 통과 화면](/assets/images/2026-04-16/multimodal-receipt-structured-output-pass.png)
_그림 2. 영수증 이미지 비전 분석 및 회의 녹음 오디오 요약 통합 테스트 통과 콘솔_

### curl을 통한 회의록 요약 확인

```bash
curl -s -X POST -F "file=@multimodal/src/test/resources/samples/meeting.wav" \
  http://localhost:8086/api/multimodal/meeting | jq .
```

![회의 녹음 오디오 요약 API curl 호출 결과](/assets/images/2026-04-16/multimodal-audio-meeting-minutes-curl.png)
_그림 3. 음성 파일 업로드 시 Gemini가 직접 요약, 참석자, 액션 아이템을 추출하여 반환한 JSON_

---

## 정리

- Spring AI 2.0.1의 **`Media` 추상화**를 사용하면 파일 바이너리를 간단히 `UserMessage`에 첨부할 수 있습니다.
- Google Gemini의 **네이티브 멀티모달**을 활용하면 별도의 OCR 및 STT 인프라 없이도 단일 API 호출로 시각/음성 데이터를 분석할 수 있습니다.
- 브라우저나 OS마다 다른 MIME 타입은 `MediaFile`을 통해 Gemini 정규 규격(`image/jpeg`, `audio/mp3`, `audio/wav`)으로 사전에 변환하여 `400 INVALID_ARGUMENT` 오류를 방지해야 합니다.
- 다음 글에서는 악의적이거나 민감한 사용자 입력으로부터 AI 서비스를 안전하게 보호하는 **Google Gemini SafetySettings 설정과 유해성 차단 가드레일 구현**을 다룹니다.
