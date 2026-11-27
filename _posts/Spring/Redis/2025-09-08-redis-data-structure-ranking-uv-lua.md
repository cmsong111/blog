---
title: "Redis Sorted Set·HyperLogLog·Lua로 랭킹과 UV 집계 구현하기"
description: "동아리 서비스의 주간 랭킹과 방문자 UV 집계를 Redis Sorted Set·HyperLogLog·Lua 스크립트로 구현하고, Set 대비 메모리, HLL 오차율, 동시 증가 시 유실 건수를 직접 측정한 결과를 정리합니다."
date: 2025-09-08 10:00:00 +0900
tags: [redis, spring-boot, kotlin, concurrency, performance]
chart: true
---

> 동아리 알고리즘 스터디 사이트에 주간 랭킹과 일별 방문자 수(UV)를 붙이면서 Redis 자료구조 세 가지를 골라 썼습니다. 100만 명 기준 Set과 HyperLogLog의 메모리 차이, HLL의 실제 오차, 동시 증가에서 GET+SET이 잃어버리는 업데이트 수를 로컬에서 재현해 측정했습니다.

> 본 글은 **Spring Boot 3.5.5, Kotlin 2.2.10, Java 21, Spring Data Redis 3.5.3(Lettuce 6.6.0), Redis 8.2.1(Docker)** 환경을 기준으로 작성했습니다. 측정은 개인 PC(12코어, 32GB RAM, Windows + Docker Desktop/WSL2)에서 애플리케이션과 Redis를 같은 머신에 두고 진행했습니다.
{: .prompt-info }

## 배경

동아리 스터디 사이트에는 문제를 풀 때마다 점수가 쌓이고, 메인 화면에 주간 상위 10명과 오늘 방문자 수가 표시됩니다. 처음에는 둘 다 PostgreSQL에서 `ORDER BY score DESC LIMIT 10`과 `COUNT(DISTINCT user_id)`로 계산했습니다. 그런데 메인 화면은 모든 방문자가 열기 때문에 집계 쿼리가 요청마다 돌았고, 방문 로그 테이블도 빠르게 커졌습니다.

예전에 [Redis SETNX로 조회수 중복을 막았던 경험](/posts/Wanted-be-challenge-view-count-redis/)이 있어서 이번에도 Redis를 떠올렸습니다. 다만 이번에는 "어떤 자료구조를 고르느냐"가 핵심이었습니다. 랭킹은 Sorted Set, UV는 HyperLogLog, 여러 명령을 한 번에 묶어야 하는 갱신은 Lua 스크립트로 정리했습니다.

## 자료구조별 내부 동작

**Sorted Set**은 멤버 수가 적을 때 `listpack`이라는 연속 메모리 배열로 저장되고, 기본값 128개(`zset-max-listpack-entries`)를 넘으면 `skiplist` + 해시 테이블 조합으로 바뀝니다. 실제로 `OBJECT ENCODING`을 찍어 보니 멤버 100명일 때는 `listpack`, 1만 명부터는 `skiplist`였습니다. 스킵 리스트 덕분에 점수 갱신(`ZINCRBY`)과 순위 조회(`ZREVRANK`)가 O(log N)이고, 상위 K명 조회는 O(log N + K)입니다.

**HyperLogLog(HLL)**는 원소를 저장하지 않습니다. 원소를 64비트로 해시한 뒤 앞 14비트로 16,384개 레지스터 중 하나를 고르고, 나머지 비트에서 처음 1이 나오기까지의 0 개수 최댓값만 기록합니다. 그래서 원소가 몇 개든 dense 표현은 레지스터 16,384개 × 6비트 = 12KB로 고정되고, 공식 표준 오차는 0.81%입니다. 원소가 적을 때는 run-length 기반 sparse 표현을 쓰다가 일정 크기를 넘으면 dense로 전환됩니다.

**Lua 스크립트**는 Redis의 단일 스레드 명령 실행 루프에서 스크립트 전체가 하나의 명령처럼 실행됩니다. 실행 도중 다른 클라이언트 명령이 끼어들 수 없으므로 "읽고 계산하고 쓰기"를 원자적으로 묶을 수 있습니다.

## 측정 결과

같은 문자열 멤버를 Set과 HLL에 넣고 `MEMORY USAGE key SAMPLES 0`으로 키 하나의 실제 메모리를 비교했습니다.

| 고유 멤버 수 | Set 메모리 | HLL 메모리 | HLL 오차 |
| :--- | ---: | ---: | ---: |
| 1,000 | 47,464 B | 2,576 B (sparse) | -0.20% |
| 10,000 | 530,344 B | 14,352 B (dense) | -0.29% |
| 100,000 | 5,047,848 B | 14,352 B | +0.70% |
| 1,000,000 | 48,387,880 B | 14,352 B | -2.11% |

```json
{
  "type": "bar",
  "data": {
    "labels": ["1천", "1만", "10만", "100만"],
    "datasets": [
      { "label": "Set (KB)", "data": [46.4, 517.9, 4929.5, 47253.8], "backgroundColor": "#f7768e" },
      { "label": "HyperLogLog (KB)", "data": [2.5, 14.0, 14.0, 14.0], "backgroundColor": "#7aa2f7" }
    ]
  },
  "options": {
    "scales": { "y": { "type": "logarithmic", "title": { "display": true, "text": "KB (로그 스케일)" } } },
    "plugins": { "title": { "display": true, "text": "고유 멤버 수별 Set vs HyperLogLog 메모리" } }
  }
}
```
{: .chart-js }

100만 명 기준으로 Set은 약 46MB, HLL은 14KB로 약 3,370배 차이가 났습니다. 오차는 표의 -2.11%가 눈에 띄어서 100만 명 실험을 서로 다른 멤버로 10번 더 돌렸습니다. 평균 절대 오차는 0.44%, 최대 1.08%였습니다. 즉 대부분은 표준 오차 근처지만, 가끔 2%대까지 튀는 시행도 실제로 나옵니다. 일별 HLL 7개를 `PFMERGE`로 합친 주간 UV는 실제 165,112명에 대해 165,566명(+0.28%)으로 집계됐습니다.

랭킹 조회 지연은 멤버 수에 거의 영향을 받지 않았습니다. 상위 10명 조회(`ZREVRANGE 0 9 WITHSCORES`)의 p50은 멤버 100명일 때 567µs, 100만 명일 때 561µs였습니다. 이 수치는 대부분 클라이언트와 Docker 사이 왕복 시간이고, 스킵 리스트 탐색 자체는 측정 오차 안에 묻혔습니다. 대신 100만 명 Sorted Set은 약 82MB(86,227,216 B)를 차지해 메모리가 더 먼저 한계가 됩니다.

마지막으로 64개 스레드가 같은 카운터를 1만 번 증가시켰습니다.

| 방식 | 최종 값 (3회) | 유실 | 소요 시간 중앙값 |
| :--- | :--- | :--- | ---: |
| `GET` 후 `SET` | 300 / 302 / 301 | 약 97% | 420ms |
| `INCR` | 10,000 × 3 | 0 | 168ms |
| Lua 스크립트 | 10,000 × 3 | 0 | 213ms |

Lettuce는 기본적으로 커넥션 하나를 여러 스레드가 공유하므로 64개 스레드의 `GET`이 거의 동시에 같은 값을 읽고, 각자 +1한 값을 덮어씁니다. 그래서 1만 번 중 300번 남짓만 살아남았습니다.

## 코드

```kotlin
// build.gradle.kts
plugins {
    kotlin("jvm") version "2.2.10"
    kotlin("plugin.spring") version "2.2.10"
    id("org.springframework.boot") version "3.5.5"
    id("io.spring.dependency-management") version "1.1.7"
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
}
```

```yaml
# src/main/resources/application.yml
spring:
  data:
    redis:
      host: localhost
      port: 6379
```

```kotlin
// src/main/kotlin/com/example/club/stat/StatRedisRepository.kt
package com.example.club.stat

import org.springframework.data.redis.core.StringRedisTemplate
import org.springframework.data.redis.core.ZSetOperations
import org.springframework.data.redis.core.script.RedisScript
import org.springframework.stereotype.Repository
import java.time.LocalDate

@Repository
class StatRedisRepository(private val redis: StringRedisTemplate) {

    private val incrScript = RedisScript.of(
        """
        local v = tonumber(redis.call('GET', KEYS[1]) or '0') + 1
        redis.call('SET', KEYS[1], v)
        return v
        """.trimIndent(), Long::class.java
    )

    private val memoryScript = RedisScript.of(
        "return redis.call('MEMORY', 'USAGE', KEYS[1], 'SAMPLES', '0')", Long::class.java
    )

    // 랭킹: 점수 누적과 상위 10명
    fun addScore(week: String, userId: Long, delta: Double): Double? =
        redis.opsForZSet().incrementScore("rank:$week", "user:$userId", delta)

    fun top10(week: String): Set<ZSetOperations.TypedTuple<String>> =
        redis.opsForZSet().reverseRangeWithScores("rank:$week", 0, 9) ?: emptySet()

    fun myRank(week: String, userId: Long): Long? =
        redis.opsForZSet().reverseRank("rank:$week", "user:$userId")?.plus(1)

    // UV: 일별 HLL과 주간 병합
    fun visit(date: LocalDate, userId: Long) {
        redis.opsForHyperLogLog().add("uv:$date", userId.toString())
    }

    fun weeklyUv(days: List<LocalDate>): Long =
        redis.opsForHyperLogLog().union("uv:week:${days.first()}", *days.map { "uv:$it" }.toTypedArray())

    // 읽고-계산하고-쓰기를 원자적으로
    fun incrementByScript(key: String): Long = redis.execute(incrScript, listOf(key))!!

    fun memoryUsage(key: String): Long = redis.execute(memoryScript, listOf(key))!!
}
```

`MEMORY USAGE`를 Lua로 감싼 데는 이유가 있습니다. `RedisConnection.execute()`로 임의 명령을 보내면 Lettuce 6.6.0은 결과를 바이트 배열로 받으려다 정수 응답에서 `UnsupportedOperationException: ByteArrayOutput does not support set(long)`을 던졌습니다. `RedisScript`에 반환 타입 `Long`을 지정하면 정수 응답을 그대로 받을 수 있습니다.

## 선택 기준과 쓰지 말아야 할 때

| 요구사항 | 고를 자료구조 | 이유 |
| :--- | :--- | :--- |
| 상위 K명, 내 순위 | Sorted Set | O(log N) 갱신·순위 조회 |
| 고유 방문자 수(근사 허용) | HyperLogLog | 키당 최대 12KB, 병합 가능 |
| 고유 방문자 목록·정확한 수 | Set 또는 DB | 멤버 조회와 정확한 카운트 필요 |
| 단순 카운터 | `INCR` / `INCRBY` | 단일 명령으로 원자적 |
| 조건부 갱신, 여러 키 동시 갱신 | Lua 스크립트 | 스크립트 전체가 원자적 실행 |

**언제 쓰지 말아야 하는가**도 분명합니다. HLL은 정산, 쿠폰 지급 대상자 수처럼 1명 차이도 문제가 되는 숫자에 쓰면 안 됩니다. 측정에서도 2%대 오차가 실제로 나왔습니다. "누가" 방문했는지 알아야 한다면 HLL로는 불가능합니다. Lua 스크립트는 실행되는 동안 Redis 전체를 막으므로 수만 개 키를 도는 반복문이나 `KEYS` 호출을 넣으면 안 됩니다. 단순 증가라면 Lua보다 `INCR`이 더 짧고 빠릅니다.

## 운영 함정 및 정리

> Sorted Set은 점수가 같으면 멤버 문자열의 사전 순으로 정렬됩니다. `alice`, `bob`, `charlie`를 모두 100점으로 넣고 `ZREVRANGE`를 호출하면 `[charlie, bob, alice]`가 나왔습니다. "먼저 달성한 사람이 위"를 원해 `점수 × 10^10 + (상수 - 타임스탬프)` 같은 복합 점수를 쓰면 점수가 `double`이라 2^53(9,007,199,254,740,992)을 넘는 순간 정밀도가 깨집니다. 실제로 10,000,008,242,999,999는 10,000,008,243,000,000으로 저장됐습니다.
{: .prompt-warning }

- [ ] 카운터를 `GET` 후 `SET`으로 갱신하는 코드가 남아 있지 않은가?
- [ ] HLL 결과를 화면 표시용 근사치로만 쓰고, 정확한 집계는 원본 로그에서 하는가?
- [ ] 주간·일별 랭킹 키에 `EXPIRE`를 걸어 오래된 Sorted Set이 메모리를 점유하지 않는가?
- [ ] 동점자 정렬 규칙과 복합 점수의 정밀도 한계를 확인했는가?
- [ ] Lua 스크립트가 짧은 시간 안에 끝나는 고정 개수의 키만 다루는가?
