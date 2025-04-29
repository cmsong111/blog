---
title: Fixture Monkey를 활용한 더미 데이터 생성
description: Fixture Monkey를 활용한 더미 데이터 생성
date: 2025-03-24 12:00:00 +0000
categories: [Development]
tags: [Fixture-Monkey, 더미데이터, 테스트]
image:
  path: https://user-images.githubusercontent.com/10272119/227154042-b43ab281-ac73-4648-ba8f-7f2146cde6d5.png
---

## 테스트용 더미 데이터 생성

스프링에서 테스트용 더미 데이터를 구성할 때, 보통 `data.sql` 파일을 많이 사용했습니다. 
이 방식은 애플리케이션 실행 시 미리 정의된 데이터를 데이터베이스에 삽입할 수 있어 간단하게 활용할 수 있는 장점이 있습니다. 

하지만 `data.sql` 파일을 사용할 경우 몇 가지 불편함이 뒤따릅니다. 먼저, 데이터가 많아지면 관리가 어려워지고, 테스트 시마다 해당 파일을 일일이 확인해야 합니다. 
또한 파일 내용이 변경될 경우 기존 테스트가 실패할 가능성이 있으며, 정적인 데이터만으로는 다양한 케이스를 유연하게 테스트하기 어렵다는 단점이 있습니다.

이러한 한계를 해결하기 위해, 동적으로 테스트 데이터를 생성할 수 있는 방법을 찾던 중 네이버에서 개발하고 유지보수 중인 Fixture Monkey라는 라이브러리를 발견하게 되었습니다. 
Fixture Monkey는 테스트 데이터를 자동으로 생성해주는 라이브러리로, Kotlin과 Java에서 사용되는 @Valid, @NotNull 등의 검증 어노테이션을 인식하고, 이를 반영한 합리적인 데이터를 생성해줍니다. 
또한 Jqwik과 연계하여 Property-Based Testing도 가능하다는 장점이 있습니다.

Fixture Monkey는 다양한 데이터 타입을 지원하며, 커스터마이징도 뛰어나 원하는 형태의 데이터를 손쉽게 만들 수 있습니다. 
Faker처럼 무작위 데이터를 생성하는 도구를 넘어서, 실제 테스트 시나리오에 적합한 신뢰성 있는 데이터를 생성하는 데 유용합니다.

## Fixture Monkey 세팅
Fixture Monkey를 Gradle 환경에서 세팅하는 방법은 다음과 같습니다.

테스트 코드에서 데이터 생성과 로직을 명확히 분리하기 위해, `Fixture`라는 개념을 도입했습니다. 이를 통해 테스트의 준비 단계와 실제 검증 과정을 구분함으로써, 테스트 코드를 더 읽기 쉽고 유지보수가 용이하도록 만들 수 있습니다.

Gradle에서는 이러한 방식을 효과적으로 지원하기 위해 `java-test-fixtures` 플러그인을 활용합니다. 이 플러그인은 테스트 전용 데이터를 별도의 영역에 정의할 수 있도록 해주며, 테스트 코드에서 해당 데이터를 손쉽게 재사용할 수 있게 해줍니다.

Fixture Monkey와 함께 `testFixtures`를 활용하면, 복잡한 도메인 객체도 간편하게 생성할 수 있고, 다양한 테스트 상황에 맞춰 유연하게 데이터를 구성할 수 있습니다.

우선, `build.gradle.kts` 파일에 `java-test-fixtures` 플러그인을 적용하고, Fixture Monkey 관련 라이브러리를 `testFixturesImplementation`으로 설정합니다. 예를 들어, Fixture Monkey의 Kotlin 지원, Jqwik 플러그인, Jakarta Validation 플러그인을 함께 사용할 수 있도록 다음과 같이 설정합니다:

### Gradle 설정

`build.gradle.kts`
```kotlin
plugins {
    id("java-test-fixtures")
}

dependencies {
    val fixtureMonkeyVersion = "1.1.11"
    testFixturesImplementation(()"com.navercorp.fixturemonkey:fixture-monkey-starter-kotlin:$fixtureMonkeyVersion")
    testFixturesImplementation("com.navercorp.fixturemonkey:fixture-monkey-jakarta-validation:$fixtureMonkeyVersion")
}
```

### TestFixtures 생성

이제 `src/testFixtures/kotlin` 디렉터리에 테스트 픽스처를 정의하는 코드를 작성합니다. 예시로 `UsersFixture.kt` 파일을 만들어, `RegisterRequest`에 대한 무작위 데이터를 생성하는 메서드를 구현할 수 있습니다.

이 클래스에서는 Fixture Monkey의 다양한 플러그인을 조합하여 빌더를 구성합니다. `KotlinPlugin()`을 통해 Kotlin 환경을 지원하고, `SimpleValueJqwikPlugin()`을 통해 Jqwik 기반의 값 생성을 가능하게 하며, `JakartaValidationPlugin()`을 사용하여 Jakarta Bean Validation(@Valid 등)을 반영한 객체 생성을 지원합니다. 생성된 `fixtureMonkey` 인스턴스를 통해 `giveMe(size)` 메서드를 사용하면 원하는 개수만큼 무작위 객체 리스트를, `giveMeOne()` 메서드를 사용하면 하나의 무작위 객체를 손쉽게 얻을 수 있습니다.

`src/testFixtures/kotlin/UsersFixture.kt`
```kotlin
import com.navercorp.fixturemonkey.FixtureMonkey
import com.navercorp.fixturemonkey.api.plugin.SimpleValueJqwikPlugin
import com.navercorp.fixturemonkey.jakarta.validation.plugin.JakartaValidationPlugin
import com.navercorp.fixturemonkey.kotlin.KotlinPlugin
import com.navercorp.fixturemonkey.kotlin.giveMe
import com.navercorp.fixturemonkey.kotlin.giveMeOne

object UsersFixture {
    private val fixtureMonkey: FixtureMonkey = FixtureMonkey.builder()
        .plugin(KotlinPlugin())
        .plugin(SimpleValueJqwikPlugin())
        .plugin(JakartaValidationPlugin())
        .build()

    fun getRandomRegisterRequest(size: Int): List<RegisterRequest> {
        return fixtureMonkey.giveMe(size)
    }

    fun getRandomRegisterRequest(): RegisterRequest {
        return fixtureMonkey.giveMeOne()
    }
}
```

이처럼 Fixture Monkey와 `testFixtures`를 결합하여 테스트 데이터를 분리하고 구조화하면, 테스트 코드가 더욱 직관적이고 명확해지며 재사용성도 높아집니다.

## 사용 예시

### 회원가입 폼

```kotlin
import io.swagger.v3.oas.annotations.media.Schema
import jakarta.validation.constraints.NotBlank
import jakarta.validation.constraints.NotNull
import jakarta.validation.constraints.Pattern
import jakarta.validation.constraints.Size

/** 회원가입 폼 */
@Schema(description = "회원가입 폼")
data class RegisterRequest(
    /** 이메일 */
    @field:Schema(description = "이메일", example = "test12345@test.com")
    @field:Size(max = 254, message = "이메일은 254자 이하로 입력해주세요")
    @field:Pattern(
        regexp = "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$",
        message = "이메일 형식이 올바르지 않습니다",
    )
    val email: String,
    /** 전화번호 */
    @field:Pattern(
        regexp = "^01(?:0|1|[6-9])-(?:\\d{3}|\\d{4})-\\d{4}\$",
        message = "전화번호 형식이 올바르지 않습니다",
    )
    @field:Schema(description = "전화번호", example = "010-1234-5678")
    @field:NotNull(message = "전화번호를 입력해주세요")
    val phone: String,
    /** 이름 */
    @field:Schema(description = "이름", example = "홍길동")
    @field:NotBlank(message = "이름을 입력해주세요")
    @field:Pattern(
        regexp = "^[가-힣a-zA-Z]{2,10}\$",
        message = "이름은 한글 또는 영어로만 작성해주세요",
    )
    val name: String,
    /** 비밀번호 */
    @field:Schema(description = "비밀번호", example = "Password1234~!")
    @field:NotBlank(message = "비밀번호를 입력해주세요")
    @field:Pattern(
        regexp = "^(?=.*[a-z])(?=.*[A-Z])(?=.*\\d)(?=.*[^\\da-zA-Z]).{5,}\$",
        message = "비밀번호는 대소문자, 숫자, 특수문자를 포함한 5자 이상이어야 합니다",
    )
    val password: String,
)
```

#### 📋 Validation 어노테이션 정리

| 어노테이션 | 설명                                                      |
| ---------- | --------------------------------------------------------- |
| @NotBlank  | null 또는 공백("")을 허용하지 않음 (문자열에만 사용 가능) |
| @NotNull   | null 값을 허용하지 않음                                   |
| @Size      | 문자열/컬렉션의 길이 또는 크기를 제한                     |
| @Pattern   | 정규 표현식을 이용한 값의 형식 검증                       |

### 🛠 랜덤 요청 예시 출력

```kotlin
println(
    UsersFixture.getRandomRegisterRequest(3).prettyJson(),
)
```

> `prettyJson()` 메서드는 따로 확장 함수를 만들어 Json을 예쁘게 출력하는 기능을 추가했습니다.

### 출력 결과

아래와 같이 랜덤한 회원가입 요청 정보를 생성할 수 있습니다. 

```json
[ {
  "email" : "JD_PJfkJPEUPugIC%STbwvIA9emM@pBYfF4vxOVPJATLMUTZ7uJdxE628L9HPbAAtbbu.ZKKZxqtK",
  "phone" : "010-711-9539",
  "name" : "홳테뮊붇쑕뻗붡샥쬼",
  "password" : "e@?H{n L\\#rWlsT^PM23\"#RQUS/@iEK;\"kW@poS\\[$,yMsc52_<peT d2p`E5am(2}QgZTXTpj,'K(rX~O:C=ffBvE'HJ63sq<AFZ.FL Uw%k\"b&=5c@s,;WYjn5{B,Vijx]p8 q4T8K);[q%c,`}4BT'&qoo}_FY!W8/4Ej6i!+~!te`Ho;{364TJmK,-PqdIM-=:D@>F~&)26pW'S\\9\"5TG21/&;N8lM=ZS%`}R\\ @t1AaL^;kBVx_|A*ioW;-O[*2!Y|s=E'_$7M1|)5Yu8O}9A5,/8O:AQ`,|Z^bR^Tn`L=u+c"
}, {
  "email" : "ZJTxPio0khu6E+FGagD5wMmGitx.K1TTPQ.d2c_+KN+azf3gI049pZNuVI_E0UHR%5tJJBOv.@nEk7DUqAeUgHYMPIu1SyDrUKbtly2B3G3s5CN7QiFLU0b8rtbDIK699swITAt2sO.qSdjH4IxyRtdn4ZI2iwQ.QfpaZlctB",
  "phone" : "010-997-3963",
  "name" : "쩀쫔빙끦졇헡쑳쭹",
  "password" : "YcYA.n'FR`[>5per7|sNneO7!@K~u]9MgB&p0[ !q=H.F'i\"Y/Qa*]^ip28c'\\qsn^XZ34X(()PX&NEF!D` qQQxo>\\EA9&:3n*/gO!)# L1DAb{IxmH~.1{.+]5aQ>\\qH]>x&`}j3!(myqplYT7DK/Qm-A?dHqff`R`OZGg)F*7/H.srQ\"AXN0skCx_|7<~=LmT~a\"_V\\yyAzlMa'>PQg/EuwIU],p-^|t'D[#F'N\\A:.oF<`I8rIoNPzvKH.8ye`<7Y={<<K8KO>T \"fo}K:KPo1ScKB'"
}, {
  "email" : "R.0km.5@2oNfdzWLQdrMJBQ2Wn4TtFerKFfhzW2YrmuvgwKI.NfIokRDuBlbjkaESlQWEJJsllVlhrkUrGUjdhKcMNRPjoeuuhPuAUrImiNWlnZswiPSWYGvmzFIkxKcdUJFIas",
  "phone" : "010-024-9565",
  "name" : "G잭씵",
  "password" : "[7RyTr!anY8oj|@xkx`:z5EXP YpI)v}+Bm$2nn7l+.f44Ce#-r6|,IrQ]Jcrc.dO9xX8x6/Ait)lx:4k29*:/TNnf]w+s\"!E!c^<W1bE}87_JiZ>|7q0,bHDns hwv<\"A$+o}whNH()&LHAQmaAJUG!m/C92dhH.p5Vc2m=GSWC7yM==:m(-`4};&y8XK|m;iH{eVlnF:\"J%C='=X`~eMWB+@3 []r]Qv-:.sL~rj54HAcR[lM>MdZqmyE#y*zi57_G(/8ptMnX`$Bqp4\\$\\f\\3-yW6K#O#[-}.}ga%EY(n\\CJ:rb'"
} ]
```

이러한 데이터를 사용하면, 개발 시 예상치 못한 예외 상황을 미리 확인할 수 있고, 다양한 케이스를 테스트할 수 있습니다. 
또한, `data.sql` 파일과의 데이터를 비교하지 않아도 되므로, 테스트 코드가 더욱 간결해지고 유지보수성이 향상됩니다.

이렇게 Fixture Monkey를 활용하면, 테스트 데이터 생성이 훨씬 간편해지고, 다양한 테스트 케이스를 쉽게 작성할 수 있습니다.


## References

{% linkpreview "https://naver.github.io/fixture-monkey/v1-1-0/" %}
