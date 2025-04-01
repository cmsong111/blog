---
title: 프리온보딩 BE 챌린지 8월 사전 과제 - 게시글 조회수 기능
description: 동일IP에 대한 조회수 중복 증가 방지 
date: 2024-08-05 12:00:00 +0000
categories: [spring-boot, wanted-be-challenge]
tags: [원티드, 백엔드, 챌린지, spring-boot]
mermaid: true
image:
  path: https://static.wanted.co.kr/images/events/4818/6f9f8e47.jpg
---

## 조회수 기능 구현

## 중복 조회수 증가 방지

게시글 조회수 기능을 구현할 때에는 다양한 방법을 고려할 수 있습니다.

아래 포스팅은 다음 과정을 통해 구현하였습니다

1. IP에 기반하여 조회수를 증가시키는 방법
    - IP + User Agent를 활용하면 동일한 WIFI를 사용하더라도 다른기기로 접속 시 조회수를 증가시킬 수 있습니다.
2. Redis의 TTL을 활용하여 다음날은 조회수를 증가시키는 방법
    - RDS를 활용한다면, 스케줄러를 활용하여 매일 0시에 조회수를 초기화할 수 있습니다.

이번 포스팅에서는 IP + User Agent를 활용하여 조회수를 증가시키는 방법을 구현해보겠습니다.

### 조회수 엔티티

게시글 조회수를 저장할 엔티티를 생성합니다.

`@RedisHash` 어노테이션을 활용하여 Redis에 저장할 수 있도록 설정합니다.

개발의 편의(?)를 위해 create 정적메소드와, createKey 정적 메소드를 생성합니다.

```kotlin
{% raw %}import org.springframework.data.annotation.Id
import org.springframework.data.redis.core.RedisHash
import java.io.Serializable
import java.time.Instant

@RedisHash(value = "article_views", timeToLive = 60 * 60 * 24)
data class ArticleView(
    @Id
    val id: String,
    val articleId: Long,
    val ip: String,
    val userAgent: String,
    val createdAt: Instant,
) : Serializable {
    companion object {
        fun create(
            articleId: Long, ip: String, userAgent: String,
        ): ArticleView {
            return ArticleView(
                id = createKey(articleId, ip, userAgent),
                articleId = articleId,
                ip = ip,
                userAgent = userAgent,
                createdAt = Instant.now(),
            )
        }

        fun createKey(
            articleId: Long, ip: String, userAgent: String,
        ): String {
            return "article_views:$articleId:$ip:$userAgent"
        }
    }
}{% endraw %}
```

### 조회수 레포지토리

`KeyValueRepository`를 상속받아 Redis에 저장할 수 있는 레포지토리를 생성합니다.

내부의 `ListCrudRepository`가 자동으로(?) finAll(), save()같은 메소드를 제공해줍니다.


```kotlin
{% raw %}import org.project.portfolio.article.entity.ArticleView
import org.springframework.data.keyvalue.repository.KeyValueRepository
import org.springframework.data.redis.repository.configuration.EnableRedisRepositories

@EnableRedisRepositories
interface ArticleRedisRepository : KeyValueRepository<ArticleView, String>{% endraw %}
```

### Post Service

```kotlin
{% raw %}import org.project.portfolio.article.entity.ArticleView

@Service
class ArticleService(
    private val articleRepository: ArticleJpaRepository,
    private val articleRedisRepository: ArticleRedisRepository,
) {
    @Transactional
    fun increaseArticleViewCount(
        articleId: Long, ip: String, userAgent: String,
    ): Long {
        // 게시글 조회
        val article: Article = articleRepository.findByIdOrNull(articleId)
            ?: throw BusinessException(ErrorCode.ARTICLE_NOT_FOUND)

        // 중복 조회수 증가 방지
        if (articleRedisRepository.findByIdOrNull(ArticleView.createKey(articleId, ip, userAgent)) == null) {
            articleRedisRepository.save(ArticleView.create(articleId, ip, userAgent))
            article.apply { viewCount++ }
        }

        return article.viewCount
    }
}{% endraw %}
```
### Post Controller

보통(?) `Controller`에서 하나의 서비스를 호출하다보니 깜박했을수도 있지만, 2개 이상의 메소드를 호출할 수 있습니다.

따라서 게시글 정보를 가져올 떄 조회수를 증가시키는 메소드를 같이 호출합니다.

```kotlin
@RestController
@RequestMapping("/api/v1/articles")
@Tag(name = "Article", description = "The article API")
class ArticleController(
    private val articleService: ArticleService,
) {
    @GetMapping("/{id}")
    @Operation(summary = "게시글 상세 조회 API")
    fun getArticle(
        @PathVariable @Parameter(description = "게시글 ID") id: Long,
        request: HttpServletRequest,
    ): ResponseEntity<ArticleResponse> {
        articleService.increaseArticleViewCount(
            articleId = id,
            ip = request.remoteAddr,
            userAgent = request.getHeader("User-Agent") ?: "Unknown User-Agent",
        )
        return ResponseEntity.ok(
            articleService.getArticle(id),
        )
    }
}
```

> 스프링 앞에 ELB나 Nginx가 있다면, 아래 포스티을 참고해서 실제 IP를 가져오는 방법을 확인하세요.
{: .prompt-info }

{% linkpreview "https://codingwithyou.tistory.com/130" %}

## 적용 결과

### Redis에 저장된 데이터

Redis에 저장된 데이터를 확인해보면, `article_views`라는 키로 저장되어 있습니다.

`article_views:게시글ID:IP:UserAgent` 형식으로 저장되어 있습니다.

> 키 값이 조금 길다 싶으면 MD5 해시(앞 10글자만) 로 저장하는 방법도 있습니다.
{: .prompt-info }


![Redis 캡쳐](/assets/images/2024-08-05/screenshot-01.png)

TTL도 86400초(24시간)로 잘 설정되어 있습니다.

![Redis 캡쳐](/assets/images/2024-08-05/screenshot-02.png)

## 정리

게시글 조회수 중복 증가 방지 기능을 구현해보았습니다.

Redis를 활용하여 TTL을 설정하고, IP + User Agent를 활용하여 중복 조회수를 방지할 수 있었습니다.

이 외에도 다양한 방법으로 구현할 수 있으니, 본인에게 맞는 방법을 찾아보세요.

{% linkpreview "https://github.com/cmsong111/Wanted-PreOnBoarding-Backend-Challenge" %}
