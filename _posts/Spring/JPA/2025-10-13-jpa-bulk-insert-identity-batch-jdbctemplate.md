---
title: "JPA 대량 Insert에서 IDENTITY 전략과 JDBC 배치 처리 비교"
description: "10만 건 Insert를 JPA IDENTITY, SEQUENCE pooled 옵티마이저, JdbcTemplate batchUpdate, 드라이버 배치 재작성 옵션 조합으로 측정하고 실제 배치 여부를 통계로 검증합니다."
date: 2025-10-13 10:00:00 +0900
tags: [jpa, jdbc, performance, postgresql, spring-boot]
chart: true
---

> 동아리 서비스의 활동 로그를 한 번에 10만 건 옮겨 담는 배치가 100초 넘게 걸렸습니다. `hibernate.jdbc.batch_size`를 켰는데도 빨라지지 않은 이유를 추적하고, ID 생성 전략과 드라이버 옵션 조합별로 시간과 실제 실행된 SQL 수를 측정했습니다.

> 기준 환경: **Spring Boot 3.5.6, Hibernate ORM 6.6.29.Final, Kotlin 2.2.20, JDK 21, PostgreSQL 17.6(pgjdbc 42.7.7), MySQL 8.4.6(Connector/J 9.4.0)**. 개인 PC(12코어, 32GB RAM, Windows + Docker Desktop/WSL2)에서 로컬로 재현했습니다. 행당 컬럼 4개(본문 100자), 1,000건 단위 flush/clear, 워밍업 1회 후 3회 측정한 중앙값입니다.
{: .prompt-info }

## 문제 상황

동아리 출석·활동 이벤트를 새 테이블로 이관하는 코드는 평범한 `saveAll`이었습니다. 설정에는 배치도 켜 두었습니다.

```yaml
# src/main/resources/application.yml
spring:
  jpa:
    properties:
      hibernate:
        jdbc.batch_size: 1000
        order_inserts: true
        generate_statistics: true
```

그런데 10만 건에 중앙값 104,123ms가 걸렸습니다. 세션 통계 로그를 켜 보니 배치는 한 번도 실행되지 않았습니다.

```text
51730123 nanoseconds spent preparing 100000 JDBC statements;
102535297069 nanoseconds spent executing 100000 JDBC statements;
0 nanoseconds spent executing 0 JDBC batches;
```

## 원인 분석

엔티티의 ID가 `GenerationType.IDENTITY`였기 때문입니다. IDENTITY는 INSERT를 실행해야 DB가 ID를 정해 줍니다. 그런데 `persist()` 직후 영속성 컨텍스트는 그 엔티티를 ID로 관리해야 하므로, Hibernate는 INSERT를 쓰기 지연 큐에 모으지 못하고 **`persist()` 시점에 바로 한 건씩 실행**합니다. `batch_size` 설정은 아예 적용될 기회가 없습니다. 이 PC의 Docker 환경에서는 왕복 한 번이 약 1ms였고, 그 1ms가 10만 번 쌓인 것이 104초의 정체였습니다.

SEQUENCE 전략은 INSERT 전에 `nextval`로 ID를 받아 두므로 INSERT를 모아 보낼 수 있습니다. 다만 `allocationSize = 1`이면 ID 하나마다 `nextval` 왕복이 생깁니다. `allocationSize = 1000`과 `increment by 1000` 시퀀스를 맞추면 pooled 옵티마이저가 시퀀스 값 하나로 ID 1,000개 구간을 메모리에서 나눠 줍니다.

마지막 단계는 드라이버입니다. JDBC 배치는 "한 번에 전송"일 뿐 서버에서는 여전히 INSERT 문 1,000개가 따로 실행됩니다. pgjdbc의 `reWriteBatchedInserts=true`는 이를 다중 행 `VALUES (...), (...)` 문으로 바꿉니다. `pg_stat_statements`로 보니 1,000건 배치가 128행짜리 7개, 64행·32행·8행짜리 각 1개로 쪼개져 있었습니다. 드라이버가 2의 거듭제곱 크기 문장을 미리 준비해 재사용하는 방식입니다.

## 해결 방법

```kotlin
// build.gradle.kts
plugins {
    id("org.springframework.boot") version "3.5.6"
    id("io.spring.dependency-management") version "1.1.7"
    kotlin("jvm") version "2.2.20"
    kotlin("plugin.spring") version "2.2.20"
    kotlin("plugin.jpa") version "2.2.20"
}

dependencies {
    implementation("org.springframework.boot:spring-boot-starter-data-jpa")
    implementation("org.jetbrains.kotlin:kotlin-reflect")
    runtimeOnly("org.postgresql:postgresql")
    runtimeOnly("com.mysql:mysql-connector-j")
}
```

```yaml
# src/main/resources/application.yml
spring:
  datasource:
    url: jdbc:postgresql://localhost:5432/lab?reWriteBatchedInserts=true
    # MySQL: jdbc:mysql://localhost:3306/lab?rewriteBatchedStatements=true
```

```kotlin
// src/main/kotlin/lab/Entities.kt
package lab

import jakarta.persistence.*
import java.time.Instant

@Entity
@Table(name = "event_pooled")
class PooledEvent(
    val userId: Long,
    val type: String,
    val payload: String,
    val createdAt: Instant,
) {
    @Id
    @GeneratedValue(strategy = GenerationType.SEQUENCE, generator = "event_pooled_gen")
    // DB 시퀀스도 반드시 increment by 1000 으로 생성합니다
    @SequenceGenerator(name = "event_pooled_gen", sequenceName = "event_pooled_id_seq", allocationSize = 1000)
    var id: Long? = null
}
```

```kotlin
// src/main/kotlin/lab/BulkWriter.kt
package lab

import jakarta.persistence.EntityManager
import org.springframework.data.jpa.repository.JpaRepository
import org.springframework.jdbc.core.JdbcTemplate
import org.springframework.stereotype.Service
import org.springframework.transaction.annotation.Transactional
import java.sql.Timestamp
import java.time.Instant

@Service
class BulkWriter(private val em: EntityManager, private val jdbc: JdbcTemplate) {
    private val createdAt = Instant.parse("2025-10-01T00:00:00Z")
    private val payload = "p".repeat(100)

    // 1,000건 단위로 flush/clear 해서 영속성 컨텍스트가 무한히 커지지 않게 합니다
    @Transactional
    fun <T : Any> jpaSaveAll(repo: JpaRepository<T, Long>, n: Int, factory: (Long, String, String, Instant) -> T) {
        (0 until n).chunked(1000).forEach { chunk ->
            repo.saveAll(chunk.map { factory((it % 1000).toLong(), "CLICK", payload, createdAt) })
            em.flush()
            em.clear()
        }
    }

    @Transactional
    fun jdbcBatch(table: String, n: Int) {
        jdbc.batchUpdate(
            "insert into $table (user_id, type, payload, created_at) values (?, ?, ?, ?)",
            (0 until n).toList(), 1000,
        ) { ps, i ->
            ps.setLong(1, (i % 1000).toLong())
            ps.setString(2, "CLICK")
            ps.setString(3, payload)
            ps.setTimestamp(4, Timestamp.from(createdAt))
        }
    }
}
```

## 결과 확인

PostgreSQL에서 10만 건을 넣은 결과입니다. "서버 INSERT 실행 수"는 `pg_stat_statements.calls`, 배치 수는 Hibernate 세션 통계 값입니다.

| 방식 | 중앙값 | 서버 INSERT 실행 수 | `nextval` 호출 | JDBC 배치 |
| :--- | ---: | ---: | ---: | ---: |
| JPA IDENTITY | 104,123ms | 100,000 | - | 0 |
| JPA SEQUENCE `allocationSize=1` | 53,928ms | 100,000 | 100,000 | 100 |
| JPA SEQUENCE pooled 1000 | 851ms | 100,000 | 100 | 100 |
| JPA SEQUENCE pooled 1000 + 재작성 | 610ms | 1,000 | 100 | 100 |
| JdbcTemplate `batchUpdate` | 776ms | 100,000 | - | - |
| JdbcTemplate `batchUpdate` + 재작성 | 320ms | 1,000 | - | - |

MySQL에서도 같은 측정을 했습니다. MySQL에는 시퀀스가 없어 JPA는 IDENTITY만 비교했고, 실행된 INSERT 수는 `Com_insert` 상태 변수 증가분으로 확인했습니다.

| 방식 (MySQL) | 재작성 끔 | 재작성 켬 | 재작성 켬 `Com_insert` |
| :--- | ---: | ---: | ---: |
| JPA IDENTITY | 60,564ms | 60,313ms | 100,000 |
| JdbcTemplate `batchUpdate` | 55,424ms | 938ms | 100 |

Connector/J는 `rewriteBatchedStatements`를 켜지 않으면 `batchUpdate`도 서버에 한 건씩 보냈습니다. 배치 API를 썼는데도 IDENTITY와 거의 같은 시간이 걸린 이유입니다. 켜면 1,000건이 다중 행 INSERT 1개로 합쳐져 `Com_insert`가 100으로 줄었습니다. 반대로 JPA IDENTITY는 애초에 배치를 만들지 않으므로 드라이버 옵션이 아무 효과도 없었습니다.

```json
{
  "type": "bar",
  "data": {
    "labels": ["JPA IDENTITY", "JPA SEQ alloc 1", "JPA SEQ pooled", "JdbcTemplate"],
    "datasets": [
      { "label": "PostgreSQL 재작성 끔", "data": [104123, 53928, 851, 776], "backgroundColor": "#f7768e" },
      { "label": "PostgreSQL 재작성 켬", "data": [null, null, 610, 320], "backgroundColor": "#9ece6a" },
      { "label": "MySQL 재작성 끔", "data": [60564, null, null, 55424], "backgroundColor": "#e0af68" },
      { "label": "MySQL 재작성 켬", "data": [60313, null, null, 938], "backgroundColor": "#7aa2f7" }
    ]
  },
  "options": {
    "plugins": { "title": { "display": true, "text": "10만 건 Insert 중앙값 (ms, 로그 스케일)" } },
    "scales": { "y": { "type": "logarithmic", "title": { "display": true, "text": "ms" } } }
  }
}
```
{: .chart-js }

IDENTITY에서 pooled SEQUENCE로 바꾸는 것만으로 122배 빨라졌고, 드라이버 재작성까지 더하면 서버가 실행하는 INSERT 문이 100분의 1로 줄었습니다. 엔티티 설계 시 `all-open`·`no-arg` 설정은 [Kotlin JPA 엔티티 설계와 all-open, no-arg 플러그인 설정](/posts/kotlin-jpa-entity-design-allopen-noarg/)에 정리한 기준을 그대로 따랐습니다.

## 선택 기준과 정리

| 상황 | 권장 방식 |
| :--- | :--- |
| 화면에서 한 건씩 저장 | IDENTITY도 충분 (차이가 체감되지 않음) |
| 엔티티 이벤트·연관관계가 필요한 수천~수만 건 | SEQUENCE pooled + `batch_size` + 재작성 옵션 |
| 수십만 건 이상 단순 적재, 엔티티 로직 불필요 | JdbcTemplate `batchUpdate` + 재작성 옵션 |
| 수백만 건 초기 적재 | PostgreSQL `COPY`, MySQL `LOAD DATA` 검토 |

**JPA로 대량 Insert를 하지 말아야 하는 경우**도 있습니다. 엔티티 생명주기 콜백이나 연관관계 cascade가 필요 없고 그냥 행을 쌓기만 하면 된다면, 영속성 컨텍스트를 거치는 비용만 남습니다. 반대로 IDENTITY를 이미 운영 중인 테이블을 SEQUENCE로 바꾸는 작업은 기존 ID와 충돌하지 않도록 시퀀스 시작값을 맞춰야 하므로, 배치 하나 때문에 무리하게 전환하기보다 해당 배치만 JdbcTemplate으로 분리하는 편이 안전합니다.

> 주의: `allocationSize`와 DB 시퀀스의 `increment by`가 다르면 pooled 옵티마이저가 엉뚱한 구간을 나눠 ID 충돌이나 큰 공백이 생깁니다. 또 `reWriteBatchedInserts=true`를 켜면 `executeBatch()`가 돌려주는 행 수 배열이 개별 건수 대신 `SUCCESS_NO_INFO(-2)`로 채워집니다. 5건 배치로 확인해 보니 재작성을 끄면 `[1, 1, 1, 1, 1]`, 켜면 `[-2, -2, -2, -2, 1]`이 반환됐습니다. 따라서 반환값으로 성공 건수를 세는 코드가 있다면 확인이 필요합니다.
{: .prompt-warning }

- [ ] 세션 통계 로그에서 `JDBC batches`가 0이 아닌지 확인했는가?
- [ ] 대량 Insert 대상 엔티티가 IDENTITY 전략이 아닌가?
- [ ] `allocationSize`와 시퀀스 `increment by`가 일치하는가?
- [ ] 드라이버 URL에 `reWriteBatchedInserts` 또는 `rewriteBatchedStatements`를 켰는가?
- [ ] 1,000건 단위 `flush`/`clear`로 영속성 컨텍스트 크기를 제한했는가?
