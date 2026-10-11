---
title: "Watchtower를 활용한 도커 컨테이너 이미지 무중단 자동 갱신"
description: "홈서버에서 구동 중인 수많은 도커 컨테이너 이미지를 매번 수동으로 업데이트하지 않고, Watchtower를 통해 백그라운드에서 주기적으로 최신 이미지를 감지·갱신하며 메신저 알림까지 자동화하는 실무 구성법을 소개합니다."
date: 2025-03-25 10:00:00 +0900
tags: [docker, homelab, watchtower, automation, container-update]
mermaid: true
---

> 홈서버에 서비스가 늘어날수록 보안 패치와 기능 업데이트가 적용된 최신 도커 이미지를 지속해서 유지 관리하는 것은 번거로운 일입니다. 그렇다고 무작정 모든 컨테이너를 일괄 업데이트하면 DB 스키마 충돌이나 서비스 장애를 겪게 됩니다. Watchtower를 활용해 라벨(Label) 기반 선별적 업데이트 전략을 수립하고, 크론(Cron) 스케줄링과 디스코드/텔레그램 알림을 연동해 안전하고 자율적인 홈서버 유지보수 파이프라인을 구축한 과정을 공유합니다.

---

## 1. 배경: 방치되는 홈서버와 수동 업데이트의 딜레마

홈서버 환경을 구축하고 나면 Nginx Proxy Manager, Cloudflare DDNS, Portainer, AdGuard Home, 각종 미디어 서버 등 10~20개가 넘는 컨테이너가 24시간 내내 상시 가동됩니다.

하지만 운영 기간이 길어질수록 다음과 같은 딜레마에 부딪히게 됩니다.

1. **보안 취약점 방치**: OpenSSL, cURL, 런타임 라이브러리의 중요 보안 취약점(CVE)이 패치된 새 이미지가 레지스트리에 릴리즈되어도, 일일이 확인하고 `docker pull`을 수행하기 귀찮아 수개월 동안 구버전 컨테이너가 방치됩니다.
2. **무차별적 자동 업데이트의 위험성 (Breaking Change)**: 모든 컨테이너를 무턱대고 최신(`latest`) 버전으로 자동 업데이트하면, PostgreSQL이나 MariaDB 같은 데이터베이스 컨테이너의 메이저 버전이 올라가며 데이터 디렉토리 포맷이 깨지거나, 설정 파일 문법이 변경되어 서비스 전체가 다운되는 대형 사고가 발생합니다.
3. **디스크 용량 잠식 (Dangling Images)**: 수동으로 이미지를 갱신하다 보면 이전 버전의 오래된 `<none>` 태그 이미지들이 호스트 디스크에 누적되어, 용량이 제한적인 홈서버 SSD를 가득 채우게 됩니다.

이러한 문제를 해결하기 위해 필요한 것은 **"상태가 없는(Stateless) 가벼운 도구들은 주기적으로 자동 업데이트하고, 데이터가 중요한(Stateful) 데이터베이스는 건드리지 않으며, 모든 업데이트 내역을 메신저로 실시간 통보받는 스마트한 자동화 시스템"**입니다. 바로 **Watchtower**를 도입한 이유입니다.

---

## 2. Watchtower 동작 원리 및 전체 파이프라인

Watchtower는 도커 호스트 내부에서 작은 데몬 컨테이너로 동작하며, 지정된 스케줄에 따라 실행 중인 컨테이너들의 이미지 다이제스트(Digest SHA256)를 원격 레지스트리와 비교합니다.

```mermaid
sequenceDiagram
    autonumber
    participant Cron as Cron 스케줄러 (새벽 4시)
    participant WT as Watchtower Daemon
    participant Sock as Docker Engine (/var/run/docker.sock)
    participant Reg as Docker Hub / GHCR
    participant Discord as Discord / Telegram Webhook
    Cron->>WT: 정기 검사 트리거 (0 0 4 * * *)
    WT->>Sock: 실행 중인 컨테이너 목록 및 라벨 조회
    Sock-->>WT: 라벨(enable=true) 부여된 대상 컨테이너 반환
    
    loop 대상 컨테이너 순회
        WT->>Reg: 원격 이미지 해시(SHA256) 조회
        Reg-->>WT: 최신 이미지 다이제스트 응답
        alt 새 이미지 감지됨
            WT->>Reg: docker pull (새 이미지 다운로드)
            WT->>Sock: 기존 컨테이너 안전 종료 (SIGTERM)
            WT->>Sock: 동일한 네트워크/볼륨/환경변수로 새 컨테이너 재생성 (run)
            WT->>Sock: 이전 dangling 이미지 정리 (docker rmi)
            WT->>Discord: 업데이트 완료 및 버전 리포트 전송
        else 변경 없음
            WT->>WT: 스킵 (아무 작업도 하지 않음)
        end
    end
```

새로운 이미지가 발견되면 Watchtower는 다음과 같은 일련의 작업을 무중단에 가깝게 자율적으로 처리합니다:
1. 기존 컨테이너가 사용하던 동일한 런타임 인자(네트워크, 포트 매핑, 볼륨 바인딩, 환경 변수 등)를 그대로 복제하여 기억합니다.
2. 기존 컨테이너에 `SIGTERM` 시그널을 보내 애플리케이션을 안전하게 종료(Graceful Shutdown)합니다.
3. 최신 이미지로 컨테이너를 다시 시작하고, 기존에 남아있던 구버전 이미지를 호스트에서 완전히 삭제(Prune)하여 디스크를 청소합니다.
4. 어떤 컨테이너가 어떤 이미지로 업데이트되었는지 디스코드/텔레그램 채널로 리포트를 발송합니다.

---

## 3. 1단계: 실전 `compose.yaml` 및 환경 변수 구성

Watchtower를 배포할 때 가장 중요한 엔지니어링 결정은 **Opt-in(명시적 선택) 방식**을 채택하는 것입니다. 기본 모드인 Opt-out(모든 컨테이너 대상, 특정 컨테이너만 제외)을 사용하면 실수로 새로 올린 DB 컨테이너까지 업데이트되어 장애를 유발할 수 있습니다.

### 3.1 환경 변수 분리 (`.env`)

알림을 수신할 웹훅 URL과 시간대를 정의합니다.

```ini
# .env (Watchtower 스택 디렉토리)
TZ=Asia/Seoul

# Discord 웹훅 URL (Shoutrrr 포맷)
# 형식: discord://token@webhookid
DISCORD_WEBHOOK_URL=discord://your-masked-token-xxxx@123456789012345678

# Telegram 알림을 사용할 경우:
# 형식: telegram://bot_token@telegram?channels=chat_id
# TELEGRAM_WEBHOOK_URL=telegram://123456789:ABCdef-masked-token@telegram?channels=-100123456789
```

> [!TIP]
> Watchtower는 다양한 메신저 알림을 위해 [Shoutrrr](https://containrrr.dev/shoutrrr/) 라이브러리를 내장하고 있습니다. Discord 웹훅 URL(`https://discord.com/api/webhooks/12345/token`)을 Shoutrrr 형식으로 변환할 때는 `discord://token@12345` 형태로 프로토콜과 인자 순서를 변경해야 합니다.
{: .prompt-tip }

### 3.2 완성형 `compose.yaml` 정의

```yaml
# compose.yaml (Watchtower 스택)
name: homelab-watchtower

services:
  watchtower:
    image: containrrr/watchtower:latest
    container_name: watchtower
    restart: unless-stopped
    volumes:
      - /etc/localtime:/etc/localtime:ro
      - /var/run/docker.sock:/var/run/docker.sock:rw # 컨테이너 제어 및 재생성을 위해 rw 필수
    environment:
      - TZ=${TZ}
      # 1. 스케줄링: 매일 새벽 4시 정각에 검사 (Cron 6필드 형식: 초 분 시 일 월 요일)
      - WATCHTOWER_SCHEDULE=0 0 4 * * *
      
      # 2. 안전 모드 (Opt-in): 특정 라벨이 붙은 컨테이너만 갱신
      - WATCHTOWER_LABEL_ENABLE=true
      
      # 3. 디스크 정리: 갱신 후 구버전 이미지 자동 삭제 (docker image prune 효과)
      - WATCHTOWER_CLEANUP=true
      
      # 4. 서비스 가용성: 중지된 컨테이너는 갱신 대상에서 제외
      - WATCHTOWER_INCLUDE_STOPPED=false
      
      # 5. 롤링 리스타트: 컨테이너들을 한꺼번에 재시작하지 않고 순차적으로 교체
      - WATCHTOWER_ROLLING_RESTART=true
      
      # 6. 알림 설정 (Shoutrrr)
      - WATCHTOWER_NOTIFICATIONS=shoutrrr
      - WATCHTOWER_NOTIFICATION_URL=${DISCORD_WEBHOOK_URL}
      - WATCHTOWER_NOTIFICATION_TEMPLATE={% raw %}{{- range . -}}📦 Container: {{.Name}} ({{.ImageName}})\n🔄 Status: {{.State}}\n{{- end -}}{% endraw %}
      
      # 7. 기타: Watchtower 자체 컨테이너도 갱신 대상에 포함할지 여부
      - WATCHTOWER_NO_STARTUP_MESSAGE=false
    labels:
      # Watchtower 자체도 최신 이미지로 자동 갱신되도록 라벨 부여
      - "com.centurylinklabs.watchtower.enable=true"
    networks:
      - npm-network

networks:
  npm-network:
    external: true
```

컨테이너를 실행합니다:

```bash
docker compose up -d
```

---

## 4. 2단계: 안전한 업데이트 전략 (Opt-in 라벨 부여 가이드)

`WATCHTOWER_LABEL_ENABLE=true` 옵션을 적용했으므로, 이제 아무 라벨도 붙지 않은 일반 컨테이너들은 Watchtower의 감시망에서 완전히 제외됩니다.

따라서 홈서버의 서비스들을 그 특성에 따라 **Stateless 서비스**와 **Stateful 서비스**로 명확히 분류하고 라벨을 선별 적용해야 합니다.

### 4.1 자동 업데이트를 적극 권장하는 서비스 (Stateless)

설정 파일이 볼륨으로 잘 분리되어 있고, 이미지 교체만으로 즉시 최신 보안 패치 혜택을 볼 수 있는 서비스들입니다. 대상 서비스의 `compose.yaml`에 아래 라벨을 추가합니다:

```yaml
labels:
  - "com.centurylinklabs.watchtower.enable=true"
```

- **Cloudflare DDNS (`favonia/cloudflare-ddns`)**: 공인 IP를 감지하는 바이너리 데몬으로 언제든 재시작되어도 무방합니다.
- **Nginx Proxy Manager (`jc21/nginx-proxy-manager`)**: 웹 콘솔과 Nginx 엔진으로, 데이터와 인증서가 볼륨에 영속화되어 있어 마이너/패치 버전 갱신이 안전합니다.
- **AdGuard Home / Pi-hole**: DNS 차단 목록 및 코어 엔진 최신화.
- **IT-Tools, Speedtest Tracker 등**: 데이터베이스 마이그레이션이 없는 순수 유틸리티 웹 서비스.

### 4.2 자동 업데이트를 절대 금지해야 하는 서비스 (Stateful)

다음 서비스들에는 **절대로 라벨을 추가하지 않거나**, 명시적으로 `false`를 선언해야 합니다:

```yaml
labels:
  - "com.centurylinklabs.watchtower.enable=false"
```

- **관계형 데이터베이스 (PostgreSQL, MySQL, MariaDB)**:
  - 예: PostgreSQL 16 ➔ 17로 자동 업데이트되면 데이터 디렉토리 바이너리 포맷 불일치로 컨테이너가 크래시 루프에 빠집니다 (`FATAL: database files are incompatible with server`).
  - 데이터베이스는 반드시 수동 백업(`pg_dump`)을 수행한 후 계획된 유지보수 시간에 업그레이드해야 합니다.
- **암호화 볼트 (Vaultwarden / Bitwarden)**:
  - 개인 비밀번호를 관리하는 핵심 서비스는 예기치 않은 버그로 인한 데이터 락다운을 방지하기 위해 릴리즈 노트를 직접 검토한 후 수동 업데이트하는 것이 안전합니다.

---

## 5. 3단계: 디스코드 & 텔레그램 실시간 알림 검증

Watchtower가 정상적으로 동작하는지 확인하기 위해 새벽 4시까지 기다릴 필요는 없습니다. `--run-once` 플래그를 주어 1회성 즉시 점검을 트리거할 수 있습니다.

### 5.1 1회성 수동 실행 및 알림 테스트

다음 명령어로 Watchtower 컨테이너에 1회 실행 시그널을 전달하거나 임시 컨테이너로 검증합니다:

```bash
docker exec -it watchtower /watchtower --run-once
```

Watchtower가 도커 소켓을 스캔하여 대상 컨테이너들의 이미지를 검사하고, 변경 사항이 있을 경우 아래와 같은 알림이 디스코드 채널에 실시간으로 전송됩니다:

```text
[Watchtower Update Report]
📦 Container: cloudflare-ddns (favonia/cloudflare-ddns:latest)
🔄 Status: Updated (pulled new digest: sha256:4a8f9c...)

📦 Container: nginx-proxy-manager (jc21/nginx-proxy-manager:latest)
🔄 Status: Updated (pulled new digest: sha256:7b2e1a...)
```

이로써 관리자는 아침에 일어나 디스코드 알림만 확인하면 어떤 컨테이너가 최신 패치되었는지 한눈에 파악할 수 있습니다.

---

## 6. 4단계: Nginx Proxy Manager 환경 연동 시 주의사항

Nginx Proxy Manager(NPM) 자체를 Watchtower 자동 업데이트 목록에 포함했을 때 고려해야 할 엔지니어링 세부 사항입니다.

1. **약 5~10초간의 프록시 순단**:
   - NPM 컨테이너가 새 이미지로 교체되는 동안 외부 트래픽(443 포트)이 일시적으로 중단됩니다.
   - 따라서 스케줄을 트래픽이 거의 없는 **새벽 4시(`0 0 4 * * *`)**로 설정하는 것이 매우 중요합니다.
2. **도커 소켓 권한(`:rw`)**:
   - Watchtower는 단순한 모니터링 도구가 아니라 컨테이너를 직접 `stop`, `rm`, `create`해야 하므로 소켓 마운트 시 `:ro`(읽기 전용)가 아닌 **`:rw`(읽기/쓰기)** 권한이 필수적입니다.
   - 따라서 Watchtower 컨테이너의 포트는 절대로 외부에 노출하지 말고 호스트 내부 네트워크에만 격리해야 합니다.

---

## 7. 마치며

이번 포스트를 통해 구축한 홈서버 자동화 유지보수 파이프라인의 핵심 성과는 다음과 같습니다.

- **안전한 Opt-in 정책**: 데이터 손상 위험이 있는 DB는 보호하고, 경량 유틸리티만 100% 자율 업데이트
- **디스크 낭비 방지**: `WATCHTOWER_CLEANUP=true`를 통한 지속적인 구버전 이미지 자동 회수
- **투명한 관찰 가능성(Observability)**: 디스코드 웹훅 알림을 통해 모든 컨테이너 변경 내역 실시간 추적

이제 우리의 홈서버(Homelab)는 다음과 같은 3단계 완전체 인프라를 갖추게 되었습니다:

1. **Cloudflare DDNS + Nginx Proxy Manager**: 외부 접속 및 와일드카드 SSL 자동화
2. **Portainer CE + GitOps**: 선언적 스택 배포 및 웹 UI 중앙 제어
3. **Watchtower**: 무중단 이미지 최신화 및 스마트 알림

더 이상 번거로운 서버 관리와 수동 작업에 시간을 뺏기지 않고, 홈서버 위에서 본인이 만들고 싶은 애플리케이션 개발에만 온전히 집중할 수 있는 쾌적한 인프라가 완성되었습니다.
