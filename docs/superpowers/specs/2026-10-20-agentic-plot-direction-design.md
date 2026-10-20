---
orphan: true
---

# 프롬프트만으로 만드는 그림: 독립 진단과 방향 제안

2026-10-20 · 진단 기준 코드 `2c29e066` · **0단계 실행 승인·기준선/개선 평가 완료, Task 5·전체 브랜치 독립 검수 완료, 범위 한정 로컬 종료 승인**

사용자의 “후속작업 진행하자. 계획짜봐”로 0단계 방향·계획을 채택했고, 이후 실행 승인을 받아
[구현 계획](../plans/2026-10-20-agent-plot-loop.md)을 수행했다. 계획 작성 기준 `26b7eab1`은 역사적 기준이다.
이 승인은 1–3단계의 구체 계약, 데이터 보존·수명, 새 wire/discovery 변경의 승인이 아니다.

제품의 단위를 코드 조각에서 **검토하고 다시 열 수 있는 재현 가능한 그림의 판(revision)**으로 옮긴다.
사람은 데이터와 의도를 주고 그림을 고른다. 외부 에이전트는 언어 해석·추론·native Python 작성을 맡고,
dartwork-mpl MCP는 수용한 데이터, 실행, 검사, 출처와 전달의 결정적 계약을 맡는 방향을 추천한다.
이는 이번 AI 진단의 선택이다. 앞서 승인된 #482의 홈페이지·로그인·커뮤니티·별도 문서 범위와 구분한다.

## 현재 확인한 것과 아직 모르는 것

독립 코드 구조 진단, 별도 제공자의 제품 진단, 실제 stdio MCP 여정 리허설을 교차 확인했다.
구조·제품 작업자는 다른 보고서와 기존 미승인 수리 설계를 보지 않았다. 이 문서도 그 설계를 읽거나 채택하지 않았다.
Handbook은 없으며 초기화하지 않았다. 현재 권위는 [AGENTS](../../../AGENTS.md), 실제 코드와 승인된 결정이다.

| 확인한 사실 | 제품상 의미·한계 |
| --- | --- |
| native Figure/Axes와 스타일·물리 치수·레이아웃 계층이 존재한다. | 사람이 코드를 안 써도 내부 구현은 기존 Matplotlib로 충분하다. |
| 현재 발견 표면은 도구 18 / 정적 자원 10 / 자원 템플릿 9 / 프롬프트 2다. | 개수는 성공 지표가 아니다. 기존 이름·순서를 보존한다. |
| `create_plot`은 외부 에이전트에게 코드를 쓰게 하며, 사후 체인은 내구성 있는 전달까지 안내하지 않는다. | 먼저 기존 `render_plot`→이미지/보고서 확인→수정→재조회 고리를 닫는다. |
| artifact의 policy / delivery / transport와 실행 계층은 이미 분리돼 있다. | 전체 패키지 분할·공통 서비스층을 먼저 만들 근거가 없다. |
| 5개 멤버 v1 번들은 PNG/PDF/정확한 소스/보고서/manifest를 7일 보관한다. | 결과 재조회는 강점이다. 데이터·환경·의도·부모 판을 보존하는 계약은 아직 없다. |
| 실행은 새 Python 자식 프로세스이며 cwd·환경을 물려받는다. | 상태 분리와 호스팅 격리는 다르다. 제품 진단은 cwd의 `json.py`가 먼저 import되는 사례도 재현했다. |
| 데이터 상세 검사는 지원 범위를 명시하며, 일부 legacy 검사는 필드 존재만 확인한다. | `ready`/`ok`·lint 통과가 데이터 의미의 정확성을 보증하지 않는다. |

세 여정은 **assistant가 직접 코드를 작성한 한정된 리허설**이다. 자율 모델 벤치마크나 성공률 측정이 아니다.
숫자 문자열·결측 CSV, 데이터 고정 스타일 수정, 서버를 다시 시작한 뒤 재조회가 실제 stdio로 수행됐다.
새 서버에서 15개 멤버를 읽고 12개 내용 파일의 digest를 대조했다. 스타일 수정의 실제 artist 좌표도 외부 oracle로 확인했다.
반면 외부 CSV를 잠시 제거하자 복구한 소스의 재실행은 실패했다. **전달 복구와 재생성은 서로 다른 성질**이다.
입력 hash만 같다고 그림에 같은 값이 그려졌다고 판단할 수 없고, hash만 남겨서는 입력을 복구할 수도 없다.

제품 진단은 프롬프트 표본 잘림과 합성 템플릿 값 잔류 위험, 실제로 그려진 값의 판독 부재도 지적했다.
이는 반복 실패의 후보이며 아직 일반 발생률·모든 차트의 판독 가능성·보안 전체를 입증하지 않는다.
큰 표본·다른 열·합성 템플릿 값이 섞인 fixture로 실제 결과를 평가한다. 안내문에 특정 문자열이 있는지 검사하는 prose test는 채택하지 않는다.

## 승인된 0단계 실행 관측

기준 4회·개선 4회를 각각 한 번 수행하고 원 기록을 보존했다. 두 FAILED smoke의 실제 인프라 증거에 한정한 명시적 admission으로 진행했으며, 새 성공 smoke bootstrap이나 추가 반복은 없었다. 실제 새 agent 회수는 scored episode에서 측정했다.
기준선 line/bar의 최종 report 수신 누락은 실패다. bar는 evaluator NumPy scalar 직렬화 오류로 의미/pixel unchecked이며 이후 수정으로 기준선을 소급 통과시키지 않았다. scatter는 제품상 유효한 60초 요청을 모델에게 알리지 않은 evaluator 20초 제한이 거절해 artifact가 없고 비용은 미확인이다.
개선 4회는 전달·선언검사·모델검토·독립 의미 replay·독립 시각검토·사람 코드 0을 통과했다. candidate_gate=true지만 compare exit1은 기준선 실패/unchecked를 보존한다. bar evaluator 버전 차이와 단일 episode 수로 일반 성능·프롬프트 인과는 입증하지 않는다.
전역 chart hint의 custom2panel 경고도 남아 있다. 실제 PNG 14개·회수 bytes·정확한 source·엄격한 replay pixels는 [평가 안내](../../integrations/agent_plot_evaluation.md)에 연결했다. 기준선 수집 완료와 개선 quality gate를 구분하며 [최종 검수 기록](/Users/wonjun/.t3/worktrees/dartwork-mpl/t3-0c3dff26/.superpowers/sdd/2026-10-20-agent-plot-loop/final-review.md)는 검수 대상 HEAD `5ff1ef7e0bf219a1b77a95ee61036b98d3eae21c`의 범위 한정 로컬 종료를 승인했다. Critical/Important 0건이며 run_episode 감사 용이성 Minor 1건은 다음 lifecycle/generalization 변경으로 명시 유예했다. 단계 1–3·website/login/community/docs 분리의 승인 경계는 그대로다.

## 선택지와 추천 책임 경계

| 선택지 | 이점 | 비용과 판단 |
| --- | --- | --- |
| **A. 외부 에이전트 + native Python + 결정적 실행/판 기록** | 현재 표현력·호스트 모델·artifact를 활용한다. | 에이전트 품질 의존과 임의 Python 신뢰 경계가 남는다. **추천.** |
| B. 닫힌 템플릿/선언형 문법 | 지원 범위 안에서는 입력·의미 검사가 쉽다. | 복합 그림마다 문법이 커진다. 템플릿은 예시·제한된 빠른 경로로 사용한다. |
| C. 서버가 LLM·대화·수정 세션까지 소유 | 한 제품에서 경험을 통제할 수 있다. | 모델·키·비용·상태·보안 책임이 늘어난다. 현재 채택 근거가 없다. |

추천 흐름은 `사람의 의도 → 외부 에이전트 → MCP 경계 → 필요한 경우 작은 workflow → 기존 delivery → 실행 → dm/Matplotlib`다.
호스트는 차트 선택, 명확화, Python 생성, 이미지 검토와 수정 판단을 소유한다. 코드는 내부 구현이되 필요하면 정확한 소스를 열어볼 수 있다.
MCP는 입력·정책·실행 결과·검사 범위·산출물 연결을 사실로 돌려주며 자연어 통계 판단을 대신하지 않는다.
코어 plotting은 MCP·workflow·UI·웹사이트를 import하지 않는다. 홈페이지·로그인·커뮤니티와 별도 docs는 각각의 소유 경계를 유지한다.

우선 기존 recipe로 학습한다. 판·입력 정책에 실제 상태 전이가 필요해질 때만 작은 `agent_workflow` capability를 추가한다.
그 안에 해당 규칙·operation·adapter·기록을 모으고, 순수 결정은 값만 받는다. shell이 공개된 artifact/실행 표면을 호출한다.
기존 handler는 요구 행동이 바뀌거나 두 번째 실제 호출자가 생길 때 소유 capability로 추출한다.
파일 길이·private import 개수의 일괄 목표, 범용 utils·공통 repository·대규모 패키지 재배치는 두지 않는다.
경계를 새로 만들면 허용 의존을 명시하고 private 경유·shared 경유·순환·미선언 의존·결정부의 타 feature import를 검사한다.

MCP의 `structuredContent`/`outputSchema`는 기계가 읽는 결과를 표현한다. 판의 수명·실패·재시도 규칙은 애플리케이션이 정해야 한다.
이는 [공식 Tools 명세](https://modelcontextprotocol.io/specification/2026-07-28/server/tools)의 사용 범위에 관한 설명이며 프로토콜 업그레이드 제안이 아니다.
현재 `fastmcp>=2.13.3,<4` 지원을 유지한다.

## 믿을 수 있는 판의 최소 계약 — 다음 설계에서 확정할 제안

**기존 v1 번들의 모양과 7일 수명을 유지**하고, 그 artifact ID를 참조하는 작은 불변 run/revision 기록을 별도로 제안한다.
필수 범주는 원 요청/수정 의도, 부모 판, 정확한 소스 digest, 수용 데이터의 bytes identity와 접근 참조,
선택한 필드·단위·행 정책, 수행한 변환, 실행 옵션·환경/버전·관련 폰트/스타일·난수 정보, 결과 artifact와 검사 범위다.
아직 포착하지 못한 외부 파일·시간·네트워크 의존은 미확인으로 기록한다. 이 목록이 새 public wire schema를 승인하는 것은 아니다.
실패한 시도는 성공 판으로 승격하지 않고 부모를 덮지 않는다. 세션이 필요하면 불변 판을 가리키는 뷰로 시작한다.

데이터 변환은 숫자 변환·결측 처리·필터·집계·정규화·시간대·단위 변경별 전후 사실을 남긴다.
사용자 지시나 승인된 한정 정책이 의미를 정한 경우에만 적용한다. 불명확한 분모·집계·단위는 질문이 필요한 결과로 반환한다.
읽은 파일을 추적하거나 hash를 남기는 것만으로 실제 plotted value를 검증했다고 하지 않는다.
스냅샷을 채택한다면 **보존 bytes·읽을 권한·수명·삭제·용량 정책**이 함께 필요하다. 7일 번들과 다른 수명을 조용히 추가하지 않는다.
입력 접근이 끝나면 명시적인 MissingInput/Expired 결과를 낸다. 연구 결과와 로그를 공유 `datasets`에 넣지 않는다.

그림의 상태는 **전달됨 / 선언한 검사를 통과함 / 지원 의미를 검증함 / 사용자가 시각적으로 선호함**으로 구분한다.
지원 차트의 row IDs·값·mask·그룹·단위는 fixture oracle 또는 독립적인 artist 판독과 비교한다.
일반 Python·임의 custom artist의 의미를 전부 증명할 수는 없다. 지원하지 않는 의미는 `unchecked`로 명시한다.
스타일만 수정한 경우 입력 identity뿐 아니라 실제 값·행 정책의 불변도 확인해야 한다.

같은 요청 키의 재시도는 **이미 commit된 알려진 결과만** 재조회한다. 다른 payload는 충돌로 다룬다.
실행 직후 crash처럼 commit 여부가 불명확하면 재실행을 성공으로 간주하지 않는다.
임의 Python의 파일·외부 부작용에 대해 crash 이후 exactly-once를 약속하지 않는다.
NeedsDecision·InvalidData·MissingInput·Conflict·ExecutionRejected·IncompleteValidation·Published 등은 해당 operation별 결과로 다룬다.
구체 이름과 공개 매핑은 후속 계약 설계 사항이며 기존 문자열 응답과 v1 응답은 호환 유지한다.

새 프로세스당 렌더를 유지한다. [Matplotlib 공식 FAQ](https://matplotlib.org/stable/users/faq.html#work-with-threads)는 thread safety를 보장하지 않는다.
로컬 실행 hardening은 작업 cwd·환경·출력·timeout/취소/자식 정리 경계를 명시하되 OS sandbox라고 광고하지 않는다.
호스팅은 별도 책임이다: 홈페이지의 검증된 principal에서 객체 권한을 얻고, 입력·산출물·캐시에 scope를 전파하며,
격리된 worker의 CPU/메모리/프로세스/출력·네트워크·secret 접근을 제한하고 실제 격리 시험을 통과해야 한다.
데이터 속 문장이나 에이전트의 코드는 권한의 근거가 아니다. 새 로그인 체계는 만들지 않는다.

## 가장 작은 첫 고리와 단계별 완료 기준

첫 범위는 **로컬 CSV 하나 → 논문/보고서용 정적 그림 → 스타일 수정 한 번 → 원판/수정판 확인 → 새 클라이언트에서 재조회**다.
사람은 Python을 작성·수정하지 않는다. agent가 전체 데이터를 사용했는지, 결측을 어떻게 다뤘는지가 그림과 함께 확인돼야 한다.
처음부터 XLSX·모든 차트·호스팅·장기 보존을 한 고리에 넣지 않는다. 먼저 측정한 반복 실패 하나씩 개선한다.

| 단계 | 우선 작업 | 다음 단계로 넘어갈 실행 가능한 기준 |
| --- | --- | --- |
| **0. 실제 agent 기준선 + 기존 고리 닫기** | 작은 고정 episode corpus와 host recipe. `render_plot`으로 최종 전달, image/report 검토, 수정, 재조회까지 연결. 표본·합성값·추가 저장 지침 구분. | 실제 MCP agent로 line/결측, grouped bar, scatter, custom 다중 패널의 4 episode와 표본/다른 열/합성값 위험을 평가. 실패도 남기면 기준선 수집은 완료다. 선택한 첫 고리 개선은 대상 episode의 fixture 값·행 정책, 출력 회수·스타일 수정·새 client 재조회 통과, 사람 코드 개입 0을 gate로 삼는다. |
| **1. 최소 출처 + 불변 판 + 데이터 정책** | 위 기록의 최소 항목과 소유 operation, retained input 정책을 별도 승인 후 추가. | 부모 bytes 불변, 스타일 수정의 실제 좌표/행 정책 보존, 의도한 필터의 제외 행 기록, 불명확한 집계의 질문, 입력 소실의 명시 실패, commit된 retry 재조회·변경 payload 충돌을 실제 저장소/stdio에서 확인. |
| **2. 한정된 수정 + 시각 선호 학습** | 측정된 실패만 유한 repair budget으로 개선. 레이아웃 측정과 전후 그림의 선호 예시 축적. | 검증하지 않은 의미를 검증 완료로 표시하지 않음. 미검증 범위를 공개한 전달과 완전 의미검증은 구분. 수정 횟수·시간·토큰 한도에서 종료하거나 이유 반환. 같은 데이터의 전후 검증과 사용자/독립 시각 검토를 분리 기록. |
| **3. 홈페이지·커뮤니티·docs 경로** | 승인된 제품 범위 안에서 viewer/내보내기, 로그인 연계, 공유, 별도 docs 연결. hosted 실행은 별도 격리 설계. | 실제 사용자가 PNG/PDF와 판을 열 수 있음. 권한·다른 사용자 객체 접근 거부·만료·격리·재시작 복구를 해당 운영 환경에서 확인. 로컬 실행 결과로 대체하지 않음. |

각 corpus run은 fixture digest, 서버/패키지/클라이언트·transport, 당시 지원되는 실제 모델/effort와 예산을 기록한다.
기준선은 모델 우열 홍보가 아니다. 의미 정확성·사람 코드 개입·정당한 명확화·도구 실패/수정·undeclared 변환·
판/데이터 회수·재생성·실제 토큰·전체 지연/비용을 episode별로 남긴다. 예쁜 그림과 올바른 값을 다른 지표로 둔다.

PR에서는 저렴한 deterministic fixture/계약, 실제 임시 파일 저장소·stdio, 색 digest·기존 discovery 호환을 gate로 제안한다.
판 전이와 parse/serialize 불변식은 property 검사, 잘못된 값·행 정책·부모 연결을 넣은 mutation으로 oracle을 확인한다.
기존 좁은 검사 출발점은 `uv run pytest tests/mcp/artifacts tests/test_mcp_data_repair_contract.py tests/test_shipped_colors_hash.py`다.
새 workflow 검사는 현재 수집 경로 `tests/` 안에 두고 CI에 연결한 뒤에만 gate라 부른다. 이 진단에서는 전체 시험을 실행하지 않았다.
실제 모델 run은 opt-in/manual/release 단일 대표 환경에서 고정 corpus와 사전 예산으로 실행한다.
비싼 LLM·이미지 검사를 모든 Python matrix에 곱하지 않는다. 회귀는 deterministic fixture로 남기고 실모델 run은 실패 양상을 검증한다.
릴리스 판정은 테스트 수·도구 수가 아니라 **정확한 plotted value/행 정책 + 사람 코드 0 + 원판 보존 + 다시 열기**다.

## 기존 로드맵과 연결, 이후 승인 경계

11개 열린 항목은 유지한다. #482는 우산이며, 나머지는 아래 고리에 기여하는 작업으로 연결한다.
출하 viewer 결함 #499(P0)는 단계 3까지 기다리지 않는 독립 즉시수리 트랙이다. #470의 CI 측정·경량화도 처음부터 병행한다.

| 항목 | 제안 연결 |
| --- | --- |
| #483 agent guidance · #498 local execution · #500 lint safety | 0단계의 recipe/안전한 수정/실행 경계. 전부 완료한 뒤 첫 episode를 시작하는 순서는 아니다. |
| #501 atomicity/data policy · #355 semantic figure checks | 1단계의 publication·입력 정책·검증 범위. 지원 의미 밖은 unchecked. |
| #209 bounded layout · #470 measured CI | 2단계 유한 수정. CI 측정·경량화는 0단계부터 병행하며 값싼 PR gate·별도 실제 agent 평가로 연결. |
| #499 viewer · #484 website/community/hosted · #485 docs split | #499 P0 즉시수리는 독립 진행. 3단계의 viewer 확장·제품 접근·각 소유 경계와 분리. 호스팅은 별도 보안 책임. |

현재 목록만으로는 **완전한 episode 평가 소유자, 입력↔그림↔판의 추적, 수정 불변식·context 소실 후 회수**가 닫히지 않는다.
이를 첫 고리의 횡단 완료 기준으로 추가 제안한다. 기존 버그 전체를 선행 조건으로 만들지 않는다.
후속으로 범위를 잘라 승인할 것은 최소 run/revision·데이터 수명 계약, 필요한 wire/discovery 변화, hosted 실행·권한 계약이다.
새 등록은 [ADR 0003](../../adr/0003-allow-scoped-mcp-artifact-discovery.md)의 제한을 별도 승인 없이 넓히지 않는다.
해당 ADR의 “implementation pending”은 현재 코드/발견 결과와 어긋나는 문서 drift이며 새 권한이 아니다.
이 문서는 universal DSL, 서버 LLM, mutable live Figure 세션, mega tool, 새 배포 패키지, 색 해동, 장기 보존을 채택하지 않는다.
방향 검토 뒤 다음 산출물은 선택한 첫 범위의 설계와 구현 계획이다. 이 문서 자체는 task 단위 시공 계획이 아니다.

근거 원본: [구조 진단](/Users/wonjun/scratch/dartwork-mpl-independent-diagnosis-2026-10-20/architecture/report.md),
[실제 stdio 리허설](/Users/wonjun/scratch/dartwork-mpl-independent-diagnosis-2026-10-20/journeys/report.md),
[독립 제품 진단](/Users/wonjun/scratch/dartwork-mpl-independent-diagnosis-2026-10-20/product/report.md).
