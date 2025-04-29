---
title: 스프링 부트에서 Ollama 모델 사용하기
description: 스프링 부트와 Spring AI를 활용하여 Ollama 모델을 통합하고 사용하는 방법을 알아봅니다.
date: 2025-04-29 12:00:00 +0000
categories: [spring-boot]
tags: [spring-boot, ai, ollama, spring-ai, kotlin]
image:
  path: https://docs.spring.io/spring-ai/reference/_images/spring-ai-integration-diagram-3.svg
---

스프링 부트에서 Spring AI를 활용해 Ollama 모델을 통합하는 방법을 소개합니다.

> 본 문서는 Spring AI 1.0.0-M7 버전을 기준으로 작성되었습니다.
{: .prompt-info }


## 프로젝트 설정

Spring AI와 Ollama 모델을 사용하려면 다음과 같이 프로젝트를 설정합니다.

### Gradle 의존성 추가

먼저, build.gradle.kts에 다음 의존성을 추가하여 Ollama 모델을 사용할 수 있도록 구성합니다.

```kotlin
extra["springAiVersion"] = "1.0.0-M7"

dependencies {
    implementation("org.springframework.ai:spring-ai-starter-model-ollama")
}

dependencyManagement {
    imports {
        mavenBom("org.springframework.ai:spring-ai-bom:${property("springAiVersion")}")
    }
}
```

## 간단한 Ollama 모델 사용 예제

Ollama 모델을 사용하여 AI 응답을 처리하는 간단한 REST 컨트롤러를 작성합니다.

### REST 컨트롤러 구현

아래는 Ollama 모델을 활용한 `AiController`의 예제입니다.

```kotlin
@RestController
class AiController(
    private val ollamaChatModel: OllamaChatModel
) {
    @PostMapping("/ollama")
    fun ollama(
        @RequestBody messageForm: MessageForm,
    ): ChatResponse {
        return ollamaChatModel.call(
            Prompt(
                listOf(
                    AssistantMessage(messageForm.assistantMessage),
                    UserMessage(
                        messageForm.userMessage,
                        emptyList()
                    )
                ),
                OllamaOptions.builder()
                    .model(OllamaModel.LLAMA3_2)
                    .build()
            ),
        )
    }

    data class MessageForm(
        val assistantMessage: String,
        val userMessage: String,
    )
}
```

### 테스트 요청 및 응답

아래는 API 호출 예시입니다.

사용자는 curl 명령어를 통해 Ollama 모델과 상호작용할 수 있습니다.

#### 요청 예제

```bash
curl -X POST http://localhost:8080/ollama \
-H "Content-Type: application/json" \
-d '{
  "assistantMessage": "You are a helpful assistant with expertise in geography?",
  "userMessage": "Can you tell me what the capital of France is?"
}'
```

#### 응답 예제

AI의 응답은 다음과 같이 JSON 형태로 반환됩니다.

```json
{
    "result": {
        "output": {
            "messageType": "ASSISTANT",
            "metadata": {
                "messageType": "ASSISTANT"
            },
            "toolCalls": [],
            "media": [],
            "text": "The capital of France is Paris."
        },
        "metadata": {
            "finishReason": "stop",
            "contentFilters": [],
            "empty": true
        }
    },
    "metadata": {
        "id": "",
        "model": "llama3.2",
        "rateLimit": {
            "requestsLimit": 0,
            "requestsRemaining": 0,
            "requestsReset": "PT0S",
            "tokensRemaining": 0,
            "tokensLimit": 0,
            "tokensReset": "PT0S"
        },
        "usage": {
            "promptTokens": 51,
            "completionTokens": 8,
            "totalTokens": 59
        },
        "promptMetadata": [],
        "empty": false
    },
    "results": [
        {
            "output": {
                "messageType": "ASSISTANT",
                "metadata": {
                    "messageType": "ASSISTANT"
                },
                "toolCalls": [],
                "media": [],
                "text": "The capital of France is Paris."
            },
            "metadata": {
                "finishReason": "stop",
                "contentFilters": [],
                "empty": true
            }
        }
    ]
}
```

## Multi-Model 지원 (이미지 삽입)

Ollama Vision 모델을 활용하여 이미지를 입력으로 받아 응답을 생성할 수도 있습니다.

예를 들어, 특정 이미지를 기반으로 설명을 요청할 수 있습니다.

![image](https://picsum.photos/id/11/1600/900)

### 코드 예제

```kotlin
@Service
class AiService2(
    private val ollamaChatModel: OllamaChatModel,
) {
    fun generate(
        assistantMessage: String,
        userMessage: String,
        medias: List<Media>,
    ): String {
        val response: ChatResponse = ollamaChatModel.call(
            Prompt(
                listOf(
                    AssistantMessage(assistantMessage),
                    UserMessage(
                        userMessage,
                        medias
                    )
                ),
                OllamaOptions.builder()
                    .model(OllamaModel.LLAMA3_2_VISION_11b)
                    .build()

            ),
        )

        return response.result.output.text!!
    }


    init {
        val response = generate(
            assistantMessage = "you are a helpful assistant",
            userMessage = "Explain the following image",
            medias = listOf(
                Media(
                    MimeType.valueOf("image/jpg"),
                    ClassPathResource("11-1600x900.jpg"),
                ),
            )
        )
        println("response: $response")
    }
}

```
### 생성 결과 

> The image depicts a serene and picturesque landscape, likely situated in a rural or wilderness area. The dominant feature of the scene is a winding stream that flows through the center of the image, its gentle curves creating a sense of movement and life. The stream's banks are lined with lush greenery, including trees and bushes, which add depth and texture to the image.
> 
> In the foreground, a field of tall grasses and wildflowers stretches out towards the viewer, punctuated by a few scattered pink flowers that add a pop of color to the otherwise muted palette. A small tree stands sentinel on the left side of the stream, its branches stretching up towards the sky like nature's own cathedral.
> 
> Beyond the stream, the landscape opens up into a vast expanse of rolling hills and mountains, their peaks shrouded in mist or cloud cover. The overall effect is one of tranquility and peace, as if the very essence of the natural world has been distilled into this single, breathtaking image.

<details>
<summary>번역문</summary>
<div markdown="1">

> 이미지는 시골이나 야생 지역에 위치한 것으로 보이는 고요하고 그림 같은 풍경을 묘사하고 있습니다. 이 장면의 주요 특징은 이미지의 중앙을 흐르는 구불구불한 개울이며, 완만한 곡선이 움직임과 생동감을 자아냅니다. 개울의 둑에는 나무와 덤불을 포함한 무성한 녹지가 줄지어 있어 이미지에 깊이와 질감을 더합니다.
>
> 전경에는 키가 큰 풀과 야생화가 펼쳐진 들판이 관람객을 향해 펼쳐져 있으며, 분홍색 꽃 몇 송이가 흩어져 있어 어두운 팔레트에 색을 더합니다. 개울 왼쪽에는 작은 나무가 보초를 서고 있으며, 가지가 마치 자연의 성당처럼 하늘을 향해 뻗어 있습니다.
>
> 개울 너머로 펼쳐진 풍경은 안개나 구름으로 뒤덮인 구불구불한 언덕과 산으로 펼쳐집니다. 전체적인 효과는 마치 자연 세계의 본질이 이 하나의 숨막히는 이미지로 증류된 것처럼 평온함과 평화로움을 선사합니다.

</div>
</details>


## 구조화된 응답 처리

Spring AI는 JSON 스키마를 기반으로 구조화된 응답을 받을 수 있도록 지원합니다.

이를 위해 `BeanOutputConverter`와 함께 `@JsonProperty` 애노테이션을 활용하여 응답 객체를 정의합니다.

```kotlin
@Service
class AiService(
    private val ollamaChatModel: OllamaChatModel,
) {
    fun generate(
        assistantMessage: String,
        userMessage: String,
        medias: List<Media> = emptyList(),
        outputConverter: BeanOutputConverter<Person> = BeanOutputConverter(Person::class.java),
    ): Person {
        val response: ChatResponse = ollamaChatModel.call(
            Prompt(
                listOf(
                    AssistantMessage(assistantMessage),
                    UserMessage(
                        userMessage,
                        medias
                    )
                ),
                OllamaOptions.builder()
                    .model(OllamaModel.LLAMA3_2)
                    .format(outputConverter.jsonSchemaMap)
                    .build()

            ),
        )

        return outputConverter.convert(response.result.output.text)
            ?: throw IllegalArgumentException("Failed to convert response to Person")
    }

    data class Person(
        @field:JsonProperty(required = true, value = "name")
        val name: String,
        @field:JsonProperty(required = true, value = "age")
        val age: Int,
        @field:JsonProperty(required = true, value = "height")
        val height: Double,
        @field:JsonProperty(required = true, value = "weight")
        val weight: Double,
        @field:JsonProperty(required = true, value = "hobbies")
        val hobbies: List<String>,
        @field:JsonProperty(required = true, value = "address")
        val address: String,
        @field:JsonProperty(required = true, value = "phone")
        val phone: String,
        @field:JsonProperty(required = true, value = "email")
        val email: String,
    )

    init {
        val response = generate(
            assistantMessage = "you are a helpful assistant",
            userMessage = "Can you create Dummy data for me?",
        )
        println("response: $response")
    }
}


```

```bash
response: Person(name=John Doe, age=30, height=72.0, weight=190.5, hobbies=[Reading, Hiking], address=123 Main St, phone=+1-555-1234, email=john.doe@example.com)
```
