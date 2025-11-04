---
title: 스프링 AI MCP Server 사용해보기
description: Spring AI의 Model Control Plane(MCP)을 STDIO 형식으로 구성해 간단한 예제 서버를 만들어보는 방법을 정리합니다.
date: 2025-11-03 12:00:00 +0900
categories: [spring-ai]
tags: [spring-boot, spring-ai, mcp, ai]
---

> Spring AI의 MCP(Model Control Plane)를 STDIO 방식으로 구성해 간단한 도구(툴)들을 노출하는 예제를 만들어봤습니다. 이 글에서는 주요 코드와 설정 파일, 빌드 및 실행 방법, 결과 확인 스크린샷을 짧게 정리합니다.

## 준비 사항
- JDK, Gradle 설정이 된 Spring Boot 프로젝트
- Spring AI 의 MCP 관련 의존성 및 어노테이션 사용 가능
- dev 환경에서 STDIO 방식으로 MCP 서버 실행 가능

## 핵심 아이디어
Spring Bean으로 ToolCallbackProvider를 등록하고, @Tool 어노테이션으로 툴 메서드를 정의하면 MCP를 통해 LLM이 해당 툴을 호출할 수 있습니다. 이 예제는 게시글(Article) CRUD를 툴로 노출합니다.

## 설정 및 주요 코드

### MCP용 ToolCallbackProvider 등록 (Kotlin)
```kotlin
@Configuration
class MCPConfig(
  private val articleService: ArticleService
) {
  @Bean
  fun myTools(): ToolCallbackProvider {
    return MethodToolCallbackProvider.builder().toolObjects(articleService).build()
  }
}
```

### ArticleService: @Tool로 노출되는 메서드들
```kotlin
import org.springframework.ai.tool.annotation.Tool
import org.springframework.stereotype.Component

@Component
class ArticleService(
  private val articleRepository: ArticleRepository
) {

  @Tool(description = "새로운 아티클(게시글)을 생성합니다.")
  fun createArticle(articleCreateForm: ArticleCreateForm): Article {
    return articleRepository.save(
      Article.create(
        title = articleCreateForm.title,
        content = articleCreateForm.content,
        author = articleCreateForm.author,
      )
    )
  }

  @Tool(description = "아이디로 아티클을 조회합니다. 존재하지 않으면 null을 반환합니다.")
  fun getArticle(id: Long): Article? {
    return articleRepository.findById(id).orElse(null)
  }

  @Tool(description = "모든 아티클을 목록으로 반환합니다.")
  fun listArticles(): List<Article> {
    return articleRepository.findAll()
  }

  @Tool(description = "아티클을 수정합니다. id로 기존 아티클을 찾아 title/content를 갱신합니다.")
  fun updateArticle(form: ArticleUpdateForm): Article {
    val article = articleRepository.findById(form.id)
      .orElseThrow { IllegalArgumentException("Article with id=${form.id} not found") }

    article.update(
      title = form.title,
      content = form.content,
    )

    return articleRepository.save(article)
  }

  @Tool(description = "아티클을 삭제합니다. 성공하면 true를 반환합니다.")
  fun deleteArticle(id: Long): Boolean {
    if (!articleRepository.existsById(id)) return false
    articleRepository.deleteById(id)
    return true
  }
}
```

### 요청 바디 모델 예시 (Kotlin / Jackson)

이유는 모르겠으나, `val title: String = ""` 처럼 기본값을 주지 않으면 MCP에서 JSON 역직렬화 시 오류가 발생합니다.

```kotlin
import com.fasterxml.jackson.annotation.JsonIgnoreProperties
import com.fasterxml.jackson.annotation.JsonProperty
import com.fasterxml.jackson.annotation.JsonPropertyDescription

@JsonIgnoreProperties(ignoreUnknown = true)
data class ArticleCreateForm(

  @field:JsonProperty("title", required = true)
  @field:JsonPropertyDescription("새 아티클의 제목입니다. (예: 'Spring AI 사용법')")
  val title: String = "",

  @field:JsonProperty("content", required = true)
  @field:JsonPropertyDescription("아티클의 본문 내용입니다. Markdown 형식을 지원할 수 있습니다.")
  val content: String = "",

  @field:JsonProperty("author", required = true)
  @field:JsonPropertyDescription("아티클 작성자의 이름 또는 닉네임입니다. (예: 'Gemini')")
  val author: String = "",
)
```

## 빌드 및 MCP 서버(STDIO) 설정

### application.yml 설정

main에서 web-application-type을 none으로 설정하고, spring.ai.mcp.server 항목에 STDIO 설정을 추가합니다.
추가적으로, 스프링에서 로그가 출력되지 않도록 banner-mode를 off로 설정합니다. (클로드 실행시 불필요한 출력 방지)

```yaml
spring:
  application:
    name: article-server

  main:
    web-application-type: none
    banner-mode: off

  ai:
    mcp:
      server:
        name: article-server
        version: 0.0.1-SNAPSHOT
        stdio: true

```

프로젝트 빌드:
```bash
./gradlew bootJar
```

MCP 서버 설정 파일 (JSON, 예: mcp-config.json)
```json
{
  "mcpServers": {
    "article-server": {
      "type": "stdio",
      "command": "java",
      "args": [
        "-jar",
        "./spring-mcp-example-0.0.1-SNAPSHOT.jar"
      ]
    }
  }
}
```

위 설정은 MCP 컨트롤러가 자식 프로세스로 해당 JAR를 STDIO로 실행하여 JSON 입출력을 통해 통신하도록 합니다.

## 동작 확인 (스크린샷)
사용 가능한 MCP 도구들 확인  
![MCP 연결 확인](/assets/images/2025-11-03/screenshot_0.png)

게시글 생성 및 수정 요청  
![게시글 생성/수정](/assets/images/2025-11-03/screenshot_1.png)

게시글 조회 및 삭제 요청  
![게시글 조회/삭제](/assets/images/2025-11-03/screenshot_2.png)

게시글 삭제 확인  
![게시글 삭제 확인](/assets/images/2025-11-03/screenshot_3.png)

## 참고 링크
실습에 사용한 공식 문서와 예제 저장소:
- 공식 문서: 
  {% linkpreview "https://docs.spring.io/spring-ai/reference/api/mcp/mcp-overview.html" %}
- GitHub 예제 코드: 
  {% linkpreview "https://github.com/cmsong111/spring-ai-mcp-example" %}
