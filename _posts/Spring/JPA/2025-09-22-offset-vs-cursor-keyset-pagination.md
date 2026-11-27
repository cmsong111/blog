---
title: "Offset 페이징의 깊은 페이지 병목과 Keyset 커서 페이징 전환"
description: "PostgreSQL 500만 건에서 Offset 페이징과 (created_at, id) 복합 커서 Keyset 페이징의 응답 시간을 페이지 깊이별로 측정하고, 실행 계획과 count 쿼리 비용, OR 전개 조건이 인덱스를 못 타는 문제를 정리합니다."
date: 2025-09-22 10:00:00 +0900
tags: [jpa, postgresql, performance, database, spring-boot]
chart: true
---

> 동아리 커뮤니티 서비스의 게시글이 쌓이면서 뒤쪽 페이지와 무한 스크롤이 눈에 띄게 느려졌습니다. 500만 건 테이블에서 Offset, Slice, Keyset 커서 방식을 페이지 깊이별로 측정하고, 같은 Keyset이라도 조건을 어떻게 쓰느냐에 따라 성능이 수십 배 갈린 이유를 실행 계획으로 확인했습니다.

> 기준 환경: **Spring Boot 3.5.5, Hibernate ORM 6.6.26.Final, Kotlin 2.2.10, JDK 21, PostgreSQL 17.6**. 개인 PC(12코어, 32GB RAM, Windows + Docker Desktop/WSL2)에서 로컬로 재현했고, 각 시나리오는 워밍업 2회 후 5회 측정한 중앙값입니다. 페이지 크기는 20건입니다.
{: .prompt-info }

## 배경

동아리 서비스의 피드 API는 `PageRequest`와 `Page<Article>`을 그대로 쓰고 있었습니다. 첫 페이지는 빠른데 응답마다 전체 건수를 세고, 무한 스크롤로 깊이 내려갈수록 느려진다는 제보가 있었습니다. 원인을 숫자로 확인하려고 로컬에 게시글 500만 건을 만들었습니다. 두 행마다 같은 `created_at`을 갖게 해서 정렬 키 중복도 재현했습니다.

```sql
create table article (
  id bigint primary key,
  created_at timestamptz not null,
  title varchar(200) not null,
  body varchar(500) not null
);
create index idx_article_created_id on article (created_at desc, id desc);
```

인덱스 컬럼 순서를 정렬 순서와 똑같이 맞춘 이유는 [B-Tree 인덱스 구조와 복합 인덱스 컬럼 순서 설계 기준](/posts/btree-index-composite-column-order/)에 정리한 원칙을 따른 것입니다.

## 동작 원리

Offset은 "앞에서 N개를 건너뛰라"는 뜻이지만 데이터베이스는 건너뛸 행을 **실제로 읽고 버립니다**. 인덱스 순서대로 읽더라도 `OFFSET 1000000`이면 100만 20개의 인덱스 항목과 힙 튜플을 방문합니다. 실제 실행 계획에서도 그대로 보였습니다.

```text
-- OFFSET 1000000 LIMIT 20
Limit (actual time=103.681..103.684 rows=20 loops=1)
  Buffers: shared hit=24243 read=1
  ->  Index Scan using idx_article_created_id on article (actual time=0.018..82.294 rows=1000020 loops=1)
Execution Time: 103.718 ms
```

Keyset은 직전 페이지 마지막 행의 `(created_at, id)`를 커서로 받아 "그보다 작은 것부터 20개"를 읽습니다. PostgreSQL은 행 값 비교 `(a, b) < (x, y)`를 복합 인덱스의 **탐색 조건(Index Cond)** 으로 바로 씁니다. 그래서 위치와 무관하게 B-Tree에서 시작점을 찾고 20개만 읽습니다.

```text
-- (created_at, id) < ('2025-01-23 18:33:20+00', 4000001) LIMIT 20
Limit (actual time=0.010..0.012 rows=20 loops=1)
  Buffers: shared hit=3 read=1
  ->  Index Scan using idx_article_created_id on article (actual time=0.009..0.010 rows=20 loops=1)
        Index Cond: (ROW(created_at, id) < ROW('2025-01-23 18:33:20+00'::timestamp with time zone, 4000001))
Execution Time: 0.032 ms
```

문제는 같은 조건을 `created_at < ? or (created_at = ? and id < ?)`처럼 OR로 풀어 쓸 때였습니다. 이 경우 플래너는 정렬을 위해 인덱스를 처음부터 훑으면서 조건을 **필터(Filter)** 로 적용했습니다. 결과는 Offset과 다를 바 없었습니다.

```text
Limit (actual time=58.256..58.259 rows=20 loops=1)
  ->  Index Scan using idx_article_created_id on article (actual time=58.254..58.256 rows=20 loops=1)
        Filter: ((created_at < '2025-01-23 18:33:20+00'::timestamp with time zone) OR (...))
        Rows Removed by Filter: 1000000
Execution Time: 58.333 ms
```

Spring Data JPA의 `Window`/`KeysetScrollPosition` API도 확인해 보니 SQL 로그에 `where a1_0.created_at<? or a1_0.created_at=? and a1_0.id<?`가 찍혔습니다. 편리하지만 PostgreSQL에서는 OR 전개 쪽 성능을 그대로 물려받습니다. 실행 계획 읽는 순서는 [PostgreSQL EXPLAIN ANALYZE로 실행 계획 읽는 방법](/posts/postgresql-explain-analyze-execution-plan/)에 정리해 두었습니다.

## 측정 결과

| 페이지 깊이(건너뛴 행) | Offset Page(+count) | Offset Slice | Keyset 행 값 비교 | Window API(OR) |
| ---: | ---: | ---: | ---: | ---: |
| 0 | 85.80ms | 2.55ms | 2.42ms | 2.29ms |
| 1만 | 87.57ms | 2.27ms | 1.88ms | 2.97ms |
| 10만 | 91.73ms | 6.94ms | 1.94ms | 7.66ms |
| 100만 | 146.42ms | 66.78ms | 2.22ms | 62.15ms |
| 250만 | 237.16ms | 140.96ms | 1.97ms | 154.61ms |
| 약 500만(마지막) | 440.18ms | 276.48ms | 1.88ms | 2.30ms |

```json
{
  "type": "line",
  "data": {
    "labels": ["0", "1천", "1만", "10만", "50만", "100만", "250만", "약 500만"],
    "datasets": [
      { "label": "Offset Page(+count)", "data": [85.80, 87.67, 87.57, 91.73, 117.77, 146.42, 237.16, 440.18], "borderColor": "#f7768e" },
      { "label": "Offset Slice", "data": [2.55, 1.88, 2.27, 6.94, 29.87, 66.78, 140.96, 276.48], "borderColor": "#e0af68" },
      { "label": "Window API(OR 전개)", "data": [2.29, 2.33, 2.97, 7.66, 30.03, 62.15, 154.61, 2.30], "borderColor": "#bb9af7" },
      { "label": "Keyset 행 값 비교", "data": [2.42, 2.04, 1.88, 1.94, 1.94, 2.22, 1.97, 1.88], "borderColor": "#9ece6a" }
    ]
  },
  "options": {
    "plugins": { "title": { "display": true, "text": "페이지 깊이별 20건 조회 중앙값 (ms, 로그 스케일, 500만 건)" } },
    "scales": { "y": { "type": "logarithmic", "title": { "display": true, "text": "ms" } } }
  }
}
```
{: .chart-js }

세 가지가 보였습니다. 첫째, `Page`는 깊이와 무관하게 매번 `select count(a1_0.id)`를 실행해 첫 페이지부터 약 85ms를 썼습니다. count 쿼리는 병렬 Index Only Scan으로 500만 행을 세는데, 같은 PC에서 단독 측정 시 82~295ms로 변동폭도 컸습니다. 둘째, count를 뺀 `Slice`도 깊이에 비례해 느려졌습니다. 셋째, 행 값 비교 Keyset만 끝까지 2ms 안팎으로 평평했습니다. OR 전개는 마지막 페이지에서만 플래너가 `BitmapOr` 계획으로 바꿔 빨라졌을 뿐, 중간 구간은 Offset과 같은 곡선을 그렸습니다.

## 적용 코드

```kotlin
// build.gradle.kts
plugins {
    id("org.springframework.boot") version "3.5.5"
    id("io.spring.dependency-management") version "1.1.7"
    kotlin("jvm") version "2.2.10"
    kotlin("plugin.spring") version "2.2.10"
    kotlin("plugin.jpa") version "2.2.10"
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    runtimeOnly("org.postgresql:postgresql")
}
```

```kotlin
// src/main/kotlin/lab/ArticleRepository.kt
package lab

import org.springframework.data.domain.Limit
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.data.jpa.repository.Query
import java.time.Instant

interface ArticleRepository : JpaRepository<Article, Long> {

    // HQL 튜플 비교 → SQL (created_at, id) < (?, ?) 로 그대로 번역됩니다
    @Query(
        """
        select a from Article a
        where (a.createdAt, a.id) < (:createdAt, :id)
        order by a.createdAt desc, a.id desc
        """,
    )
    fun findNextPage(createdAt: Instant, id: Long, limit: Limit): List<Article>
}
```

```kotlin
// src/main/kotlin/lab/ArticleFeedService.kt
package lab

import org.springframework.data.domain.Limit
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.time.Instant
import java.util.Base64

data class ArticleCursor(val createdAt: Instant, val id: Long) {
    fun encode(): String =
        Base64.getUrlEncoder().withoutPadding()
            .encodeToString("$createdAt|$id".toByteArray()) // 마이크로초까지 보존

    companion object {
        fun decode(raw: String): ArticleCursor {
            val (ts, id) = String(Base64.getUrlDecoder().decode(raw)).split("|")
            return ArticleCursor(Instant.parse(ts), id.toLong())
        }
    }
}

data class FeedPage(val items: List<Long>, val nextCursor: String?)

@Service
@Transactional(readOnly = true)
class ArticleFeedService(private val repo: ArticleRepository) {

    fun feed(cursor: String?, size: Int = 20): FeedPage {
        val c = cursor?.let(ArticleCursor::decode)
            ?: ArticleCursor(Instant.parse("9999-12-31T00:00:00Z"), Long.MAX_VALUE)
        // size + 1 건을 읽어 다음 페이지 존재 여부를 판단 (count 쿼리 없음)
        val rows = repo.findNextPage(c.createdAt, c.id, Limit.of(size + 1))
        val page = rows.take(size)
        val next = if (rows.size > size) page.last().let { ArticleCursor(it.createdAt, it.id).encode() } else null
        return FeedPage(page.map { it.id }, next)
    }
}
```

## 선택 기준

| 상황 | 권장 방식 | 이유 |
| :--- | :--- | :--- |
| 관리자 화면, 총 페이지 번호 필요, 수만 건 이하 | Offset + `Page` | 구현 단순, 깊이 1만까지 Slice 기준 2ms대 |
| 번호 없는 "더 보기", 총 건수 불필요 | Offset + `Slice` | count 제거만으로 첫 페이지 85ms → 2ms대 |
| 무한 스크롤, 깊은 탐색, 실시간 삽입 많음 | Keyset 행 값 비교 | 깊이와 무관하게 일정, 중복·누락 없음 |
| MySQL 등 행 값 비교 인덱스 활용이 불확실한 DB | Keyset + 실행 계획 검증 | OR 전개가 필터로 떨어지는지 반드시 확인 |

**Keyset을 쓰지 말아야 하는 경우**도 있습니다. "37페이지로 바로 이동" 같은 임의 접근이 요구사항이면 커서로는 만들 수 없습니다. 정렬 기준을 사용자가 자유롭게 바꾸는 화면도 정렬 조합마다 복합 인덱스와 커서 형식이 필요해 비용이 커집니다. 데이터가 수만 건 이하이고 사용자가 앞쪽 몇 페이지만 본다면, 이번 측정처럼 Offset Slice도 Keyset과 차이가 없으므로 Offset을 유지하는 편이 낫습니다.

> 주의: 커서에 `created_at`을 밀리초로 잘라 담으면 PostgreSQL `timestamptz`의 마이크로초와 어긋나 같은 행을 다시 보여 주거나 건너뛸 수 있습니다. 커서에는 원래 정밀도를 그대로 담고, 정렬 키가 유일하지 않다면 반드시 PK를 마지막 타이브레이커로 넣어야 합니다. 또 `desc` 정렬에서 `null`이 허용된 컬럼은 행 값 비교 결과가 `null`이 되어 행이 사라지므로 커서 컬럼은 `not null`로 두는 것이 안전합니다.
{: .prompt-warning }

## 정리

- [ ] 목록 API가 `Page`를 반환해 불필요한 count 쿼리를 매번 실행하고 있지 않은가?
- [ ] 커서 정렬 키가 유일하도록 `(정렬 컬럼, id)` 복합 커서를 쓰는가?
- [ ] 커서 조건이 `Index Cond`로 잡히는지 `EXPLAIN ANALYZE`로 확인했는가?
- [ ] `Window` API나 OR 전개 조건이 `Filter`와 `Rows Removed by Filter`로 떨어지지 않는가?
- [ ] 정렬 순서와 같은 방향·순서의 복합 인덱스가 있는가?
