---
title: "Redis 캐시 스탬피드·관통·눈사태를 재현하고 DB 조회 수로 비교한 방어 전략"
description: "핫 키 만료 순간의 캐시 스탬피드, 없는 키 조회로 생기는 관통, 동시 만료로 생기는 눈사태를 로컬에서 재현하고 뮤텍스, PER, Null 캐싱, Bloom 필터, TTL Jitter 적용 전후의 DB 조회 수를 측정했습니다."
date: 2026-02-09 10:00:00 +0900
tags: [redis, caching, spring-boot, kotlin, performance]
chart: true
---

> 캐시를 붙였는데도 DB가 순간적으로 몰리는 장애는 대부분 "캐시가 비는 순간"에 일어납니다. 스탬피드, 관통, 눈사태를 각각 재현해 DB 조회 수를 세고, 방어 기법별로 몇 건까지 줄어드는지 측정했습니다.

> 본 글은 **Spring Boot 4.0.2, Kotlin 2.2.21, Java 21, Spring Data Redis 4.0.2(Lettuce 6.8.2), Redis 8.4.0, PostgreSQL 17.6, HikariCP 7.0.2(풀 10)** 환경을 기준으로 작성했습니다. 측정은 개인 PC(12코어, 32GB RAM, Windows + Docker Desktop/WSL2)에서 진행했고, 각 시나리오는 3회 반복했습니다.
{: .prompt-info }

## 배경

회사 서비스의 메인 화면에는 집계 쿼리로 만든 "인기 목록"이 있고, 이 결과를 Redis에 캐싱해 둡니다. 평소에는 캐시 적중률이 높아 문제가 없었는데, 트래픽이 몰리는 시간에 캐시 TTL이 끝나는 순간마다 DB 커넥션 풀 대기 경고가 짧게 튀었습니다. 원인을 정리해 보니 캐시가 비는 패턴은 세 가지였습니다.

| 현상 | 캐시가 비는 이유 | 대표 방어 |
| :--- | :--- | :--- |
| 스탬피드(Stampede) | 핫 키 1개 만료 순간 동시 미스 | 뮤텍스, PER |
| 관통(Penetration) | DB에도 없는 키라 캐시에 안 남음 | Null 캐싱, Bloom 필터 |
| 눈사태(Avalanche) | 많은 키가 같은 시각에 만료 | TTL Jitter |

재현용 DB 조회는 `pg_sleep(0.1)`을 붙여 재계산 비용을 100ms로 고정했고, 조회 메서드 안의 `AtomicInteger`로 실제 DB 조회 횟수를 셌습니다.

## 스탬피드와 뮤텍스, PER

먼저 핫 키가 막 만료된 순간 200개 요청이 동시에 도착하는 상황입니다.

| 전략 | DB 조회 (3회) | p50 | p99 |
| :--- | :--- | ---: | ---: |
| 순진한 cache-aside | 200 / 200 / 200 | 1,079ms | 2,039ms |
| Redis 뮤텍스 | 1 / 1 / 1 | 125ms | 138ms |

순진한 방식은 200개 요청이 모두 DB로 갔고, 커넥션 풀이 10개라 100ms 쿼리가 20번에 나눠 처리되면서 p99가 2초를 넘었습니다. 뮤텍스는 `SET NX PX`로 락을 잡은 1개 요청만 DB에 가고 나머지 199개는 20ms 간격으로 캐시를 다시 읽었습니다. 토큰을 비교한 뒤 지우는 해제 스크립트는 [분산 락 비교 글](/posts/redis-distributed-lock-transaction-boundary/)에서 쓴 것과 같습니다.

뮤텍스는 DB를 지키지만 대기자는 여전히 재계산 시간만큼 기다립니다. 그래서 32개 스레드가 12초 동안 계속 조회하고 TTL이 2초인 지속 부하에서 PER(Probabilistic Early Recomputation)과 비교했습니다.

| 전략 | DB 조회 (3회) | 50ms 넘은 요청 (3회) | 최대 지연 |
| :--- | :--- | :--- | ---: |
| 순진한 cache-aside | 160 / 160 / 160 | 160 / 160 / 160 | 약 410ms |
| Redis 뮤텍스 | 5 / 5 / 5 | 160 / 160 / 160 | 약 130ms |
| PER (β = 1) | 18 / 18 / 21 | 18 / 18 / 21 | 약 105ms |

```json
{
  "type": "bar",
  "data": {
    "labels": ["동시 200건 버스트", "12초 지속 부하"],
    "datasets": [
      { "label": "순진한 cache-aside", "data": [200, 160], "backgroundColor": "#f7768e" },
      { "label": "Redis 뮤텍스", "data": [1, 5], "backgroundColor": "#7aa2f7" },
      { "label": "PER", "data": [null, 18], "backgroundColor": "#9ece6a" }
    ]
  },
  "options": {
    "plugins": { "title": { "display": true, "text": "스탬피드 상황의 DB 조회 수 (3회 중앙값)" } }
  }
}
```
{: .chart-js }

순진한 방식은 만료 5번 × 스레드 32개 = 160번 DB에 갔습니다. 뮤텍스는 만료당 1번(5번)으로 DB 조회가 가장 적지만, 만료 때마다 32개 스레드가 모두 기다려 느린 요청 수는 순진한 방식과 같았습니다. PER은 DB 조회가 18~21번으로 뮤텍스보다 많지만, 느린 요청은 재계산을 맡은 요청 자신뿐이었습니다.

PER의 내부 원리는 XFetch 알고리즘입니다. 캐시에 값과 함께 재계산 소요 시간 δ와 논리 만료 시각을 저장하고, 읽을 때마다 `now - δ × β × ln(rand) ≥ expiry`이면 만료 전이라도 그 요청 혼자 미리 재계산합니다. `ln(rand)`는 음수라서 만료가 가까울수록, 재계산이 비쌀수록 조기 재계산 확률이 커집니다. 실제 Redis TTL은 논리 만료보다 넉넉하게 둬서 재계산하는 동안에도 기존 값을 계속 내줍니다.

## 관통과 눈사태

**관통**은 존재하지 않는 ID 100개를 각 10번씩, 16개 스레드로 조회해 재현했습니다. Null 캐싱 없이 1,000번 모두 DB로 갔고, 없는 결과를 `__NULL__` 표식으로 30초 캐싱하자 112 / 115 / 119번으로 줄었습니다. 100번이 아니라 110번대인 이유는 같은 ID에 대한 첫 미스가 동시에 몰렸기 때문입니다. 관통 안에도 작은 스탬피드가 있는 셈입니다.

ID를 무작위로 바꿔 가며 찌르는 요청은 Null 캐싱으로 막을 수 없어 Bloom 필터를 함께 봤습니다. Redis 8부터는 Bloom 필터가 기본 포함되어 모듈 설치 없이 `BF.RESERVE`를 쓸 수 있습니다. 존재하는 ID 10만 개를 넣고 없는 ID 10만 개로 조회했습니다.

| 목표 오탐률 | 메모리 | 실제 오탐 | 존재하는 ID 판정 |
| :--- | ---: | ---: | ---: |
| 1% | 137,976 B | 522건 (0.52%) | 100,000 / 100,000 |
| 0.1% | 197,888 B | 55건 (0.055%) | 100,000 / 100,000 |

Bloom 필터는 "없다"고 하면 확실히 없고, "있다"는 오탐일 수 있습니다. 실제로 존재하는 ID를 놓친 경우는 0건이었습니다.

**눈사태**는 1,000개 키를 한 번에 적재하고 TTL 5초를 똑같이 준 뒤, 16개 스레드가 12초 동안 무작위 키를 읽게 했습니다. 250ms 구간별 DB 조회 수의 최댓값은 고정 TTL에서 425 / 470 / 492건, TTL에 ±20% Jitter를 주자 153 / 135 / 141건이었습니다. 총 DB 조회 수는 두 경우 모두 약 1,020건으로 같고, 몰리는 시점만 흩어집니다.

```json
{
  "type": "line",
  "data": {
    "labels": ["3.0s", "3.25s", "3.5s", "3.75s", "4.0s", "4.25s", "4.5s", "4.75s", "5.0s", "5.25s", "5.5s", "5.75s", "6.0s", "6.25s"],
    "datasets": [
      { "label": "고정 TTL 5s", "data": [0, 0, 0, 0, 0, 142, 369, 425, 87, 0, 0, 0, 0, 0], "borderColor": "#f7768e" },
      { "label": "TTL 5s ±20% Jitter", "data": [0, 0, 26, 70, 136, 153, 110, 121, 132, 138, 92, 46, 1, 0], "borderColor": "#7aa2f7" }
    ]
  },
  "options": {
    "plugins": { "title": { "display": true, "text": "250ms 구간별 DB 조회 수 (1회차)" } }
  }
}
```
{: .chart-js }

고정 TTL인데도 만료가 4.25~5.0초에 걸쳐 나타난 것은 1,000개 키를 순차로 적재하는 데 걸린 시간만큼 만료도 퍼졌기 때문입니다.

## 적용 코드

```kotlin
// build.gradle.kts
plugins {
    kotlin("jvm") version "2.2.21"
    kotlin("plugin.spring") version "2.2.21"
    id("org.springframework.boot") version "4.0.2"
    id("io.spring.dependency-management") version "1.1.7"
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-redis")
    implementation("org.springframework.boot:spring-boot-starter-jdbc")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    runtimeOnly("org.postgresql:postgresql")
}
```

```yaml
# src/main/resources/application.yml
spring:
  data:
    redis:
      host: localhost
      port: 6379
  datasource:
    url: jdbc:postgresql://localhost:5432/app
    username: app
    password: ${DB_PASSWORD}
    hikari:
      maximum-pool-size: 10
```

```kotlin
// src/main/kotlin/com/example/cache/StampedeCache.kt
package com.example.cache

import org.springframework.data.redis.core.StringRedisTemplate
import org.springframework.data.redis.core.script.RedisScript
import org.springframework.stereotype.Component
import java.time.Duration
import java.util.UUID
import java.util.concurrent.ThreadLocalRandom
import kotlin.math.ln

fun interface Loader { fun load(id: Long): String? }

@Component
class StampedeCache(private val redis: StringRedisTemplate) {

    private val unlockScript = RedisScript.of(
        "if redis.call('GET', KEYS[1]) == ARGV[1] then return redis.call('DEL', KEYS[1]) end return 0",
        Long::class.java,
    )

    // 뮤텍스: 미스가 나면 한 요청만 DB로, 나머지는 짧게 기다렸다가 캐시 재조회
    fun mutex(id: Long, ttl: Duration, loader: Loader): String? {
        val key = "item:$id"
        redis.opsForValue().get(key)?.let { return it }
        val lockKey = "lock:$key"
        val token = UUID.randomUUID().toString()
        repeat(100) {
            if (redis.opsForValue().setIfAbsent(lockKey, token, Duration.ofSeconds(3)) == true) {
                try {
                    redis.opsForValue().get(key)?.let { return it } // double-check
                    val v = loader.load(id) ?: return null
                    redis.opsForValue().set(key, v, ttl)
                    return v
                } finally {
                    redis.execute(unlockScript, listOf(lockKey), token)
                }
            }
            Thread.sleep(20)
            redis.opsForValue().get(key)?.let { return it }
        }
        return loader.load(id) // 대기 한도 초과 시 최후 수단
    }

    // PER(XFetch): "값|재계산 소요ms|논리 만료 epoch ms"
    fun per(id: Long, ttl: Duration, loader: Loader, beta: Double = 1.0): String? {
        val key = "item:per:$id"
        redis.opsForValue().get(key)?.let { raw ->
            val (value, delta, expiry) = raw.split('|').let { Triple(it[0], it[1].toLong(), it[2].toLong()) }
            val rnd = ThreadLocalRandom.current().nextDouble().coerceAtLeast(1e-12)
            if (System.currentTimeMillis() - delta * beta * ln(rnd) < expiry) return value
        }
        val start = System.currentTimeMillis()
        val v = loader.load(id) ?: return null
        val delta = System.currentTimeMillis() - start
        val expiry = System.currentTimeMillis() + ttl.toMillis()
        redis.opsForValue().set(key, "$v|$delta|$expiry", ttl.plusSeconds(10)) // 실제 TTL은 여유 있게
        return v
    }

    // Null 캐싱: 없는 ID도 짧게 캐싱
    fun withNullCaching(id: Long, ttl: Duration, loader: Loader, nullTtl: Duration = Duration.ofSeconds(30)): String? {
        val key = "item:$id"
        when (val cached = redis.opsForValue().get(key)) {
            NULL_MARK -> return null
            null -> Unit
            else -> return cached
        }
        val v = loader.load(id)
        redis.opsForValue().set(key, v ?: NULL_MARK, if (v == null) nullTtl else jittered(ttl))
        return v
    }

    companion object {
        const val NULL_MARK = "__NULL__"

        // TTL Jitter: 기준 TTL의 ±ratio 범위에서 무작위
        fun jittered(base: Duration, ratio: Double = 0.2): Duration {
            val spread = (base.toMillis() * ratio).toLong()
            return base.plusMillis(ThreadLocalRandom.current().nextLong(-spread, spread + 1))
        }
    }
}
```

## 선택 기준과 쓰지 말아야 할 때

| 상황 | 추천 |
| :--- | :--- |
| 재계산이 비싸고 DB 보호가 최우선 | 뮤텍스 (대기 지연은 감수) |
| 재계산 비용이 일정하고 지연 꼬리를 줄이고 싶음 | PER |
| 없는 ID가 반복 조회됨 | Null 캐싱 (짧은 TTL) |
| 무작위 ID 스캔, 크롤링 | Bloom 필터 + Null 캐싱 |
| 배치로 한꺼번에 적재한 키 | TTL Jitter |

**언제 쓰지 말아야 하는가**도 있습니다. 트래픽이 낮아 만료 순간 동시 미스가 거의 없다면 뮤텍스나 PER은 코드 복잡도만 늘립니다. PER은 재계산 비용이 들쭉날쭉하면 δ가 흔들려 조기 재계산이 너무 많거나 적어집니다. Null 캐싱은 "방금 생성된 데이터"가 Null 표식 TTL 동안 안 보일 수 있으므로, 생성 시점에 해당 키를 지우는 처리가 필요합니다. Bloom 필터는 삭제를 지원하지 않아 데이터가 자주 지워지는 도메인에서는 오탐이 계속 쌓입니다.

## 운영 함정 및 정리

> 뮤텍스의 락 TTL(여기서는 3초)이 재계산 시간보다 짧으면, 재계산 도중 락이 풀려 두 번째 요청이 또 DB로 갑니다. 반대로 너무 길면 락을 잡은 인스턴스가 죽었을 때 대기자들이 그만큼 기다립니다. 재계산 p99보다 넉넉하게 잡고, 대기 한도를 넘으면 DB 직접 조회로 빠지는 경로가 다시 스탬피드가 되지 않도록 한도 초과 횟수를 [커스텀 메트릭](/posts/otel-custom-business-metrics/)으로 남겨 두는 편이 좋습니다.
{: .prompt-warning }

- [ ] 핫 키의 재계산 비용과 동시 요청 수를 알고 있는가?
- [ ] 핫 키에는 뮤텍스나 PER 중 하나를 적용했는가?
- [ ] 없는 키 조회에 Null 캐싱 TTL을 짧게 두고, 생성 시 무효화하는가?
- [ ] 배치·워밍업으로 한꺼번에 적재하는 키에 TTL Jitter를 넣었는가?
- [ ] 캐시 미스율과 DB 조회 수를 대시보드에서 만료 시점과 함께 볼 수 있는가?
