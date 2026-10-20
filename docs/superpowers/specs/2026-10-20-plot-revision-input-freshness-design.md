---
orphan: true
---

# 입력 선택과 최신성 — 보존 계약 보완

2026-10-20 · [수명 설계](2026-10-20-plot-revision-input-lifecycle-design.md)·[ADR 0004](../../adr/0004-retained-input-revision-contract.md)의 한정 보완. 제품 구현·정책 배치는 아직 없다.

## 승인 수신과 이번 정리

사용자는 기존 설계 승인과 한정 freeze 예외 승인을 설명받은 뒤 이렇게 답했다.

> 좋아 진행해. 그런데 보관을 어디에다가 하는 거야? 유저가 이 부분을 인지하고 프롬프트를 날릴 수 있어? 그리고 그 데이터가 갱신되면, 과거 데이터에 기반해 그리는 건 혼란을 야기하잖아?

첫 문장은 앞서 설명한 수명 설계·한정 예외의 진행 승인으로 기록한다. 같은 승인을 반복해서 요구하지 않는다.
아래 선택 receipt는 새로 확정하는 엔지니어링 세부다. 이미 사용자가 그 필드 이름까지 검토했다고 기록하지 않는다.
별도 동기화 기능·추가 도구·원본 경로 공개·원본 수정 권한을 승인받은 것으로 넓히지 않는다. ADR의 제안 표시는 보완 문서 정합 전 상태이며 승인 수신을 부정하지 않는다.

## 현재 권위와 불변식

| role | path | 현재 실재 / 이 보완의 목표 |
| --- | --- | --- |
| purpose | `AGENTS.md`, 수명 설계 | native Figure/Axes, 문서 200줄 상한, 기존 잠금 보존 / 입력 선택을 사용자 의도와 맞춤 |
| architecture | `src/dartwork_mpl/mcp/artifacts/{transport,policy,store}.py` | render 4인자, 5멤버·6 manifest 키·7일 / 제안 revision의 report receipt만 구체화 |
| execution | `src/dartwork_mpl/mcp/execution.py` | trusted Python, 입력 보존 없음 / Copy·Retained를 명시 선택하고 자동 대체 금지 |
| verification | `tests/mcp/artifacts/`, 수명 설계 G1–G8 | 실제 파일·stdio 검증 가능 / 아래 F1–F5를 G1·G3·G6·G8의 판정 사례에 포함 |

Handbook은 없으며 초기화하지 않는다. 출하 색·역사 baseline·기존 오류 enum·5멤버·6 manifest 키는 그대로다.
이 보완은 서버가 보장하는 bytes 경계와 에이전트가 판단하는 데이터 의미를 구분한다.

## 보관 위치를 사용자가 아는 경로

보관은 **그 MCP 서버가 도는 호스트의 운영자 지정 private `storage_dir`**다. 클라이언트 PC·원본 폴더·클라우드 공유 저장소라고 추정하지 않는다.
정확한 디렉터리는 운영자가 `DARTWORK_MPL_INPUT_POLICY`가 가리키는 JSON의 `storage_dir`에 지정한다. 실제 정책·경로·grant는 아직 배치하지 않았으므로 지금 정해진 실경로는 없다.
수명 설계의 0700/0600·datasets 밖·root 겹침 금지·용량·7일·개별 삭제·오프라인 잔여물 규칙이 그대로 적용된다.
`Retained`는 그 저장소의 **고정된 bytes 복사본**이다. 원본을 열지 않으므로 원본 변경을 자동 발견할 수 없다. 사용자가 “현재 파일”을 원하면 원본을 새로 확보하는 Copy가 필요하다.

기존 MCP 경로로 `get_plot_artifact(id)` → 반환된 `report.json`·`manifest.json`을 읽으면 논리 입력명·digest·보존 locator·생성/만료 시각을 알 수 있다.
report의 locator·만료 시각은 생성 당시의 보존 receipt이며 현재 입력 존재를 보장하지 않는다. 입력을 삭제해도 report는 남을 수 있다.
현재 재사용 가능 여부는 실제 Retained admission에서 확인한다. 실시간 상태·목록 API는 추가하지 않는다.
보완된 render/get 안내와 입력 사용 안내는 `retained` locator가 서버 로컬 보관을 뜻한다고 설명한다. 정확한 `storage_dir`·허용 root 경로·원 basename은 보고서·오류·locator에 새로 넣지 않는다.
현행 `dartwork_mpl_info`에는 실제 입력 정책 경로를 조회하는 기능이 없다. 이 작업은 조회 도구나 정책 공개 기능을 추가하지 않는다.
운영자는 허용 `root_id`와 사용법을 연결 안내로 제공해야 한다. 사용자는 논리 ID로 재사용하므로 실제 경로를 기억할 필요가 없다. 정확한 보관 경로가 필요하면 운영자가 위 JSON의 `storage_dir`을 확인한다.
MCP 클라이언트가 사용자에게 무엇을 표시할지는 클라이언트가 결정한다. 서버가 안내·보고서를 제공하는 것과 강제 표시 보장은 다르다.

## 두 선택과 닫힌 receipt

추천은 기존 `copy`/`retained` 선택을 유지하고, **선택 사실만 report에 남기는 것**이다.
새 provenance v1은 아직 출하 전이므로 아래 `selection`을 같은 v1 입력 항목에 필수로 정한다. 최상위 render/get envelope·manifest는 바꾸지 않는다.

```text
report.provenance.inputs[i] = {
  name, sha256, size_bytes,
  retained: {artifact_id, name},
  selection: CopySelection | RetainedSelection,
  evidence: "copied_and_boundary_checked"
}
CopySelection = {kind: "copy"}
RetainedSelection = {kind: "retained", artifact_id: UUID4hex, input_name}
```

두 selection 객체는 각각 표시된 키만 허용한다. ID/name의 타입·한도는 revision과 같다. `selection`은 요청을 검증한 값에서 서버가 만들며 source가 제출한 설명을 믿지 않는다.
`retained`는 새 child 소유 세트를, `selection`의 ID/name은 그 요청이 선택한 이전 세트를 가리킨다. 서로 다른 역할이다.
내부 `inputs.json`에는 이 receipt를 추가하지 않는다. 재사용 admission은 기존 세트의 metadata/hash/commit을 검증하고, 새 report는 현재 검증한 요청에서 receipt를 만든다.
새 클라이언트는 report만으로 선택 종류·정확한 이전 세트·현재 재사용 locator를 구분한다. 부모 provenance를 못 읽으면 부모와의 bytes 비교 결과를 추측하지 않는다.

| 선택 | 서버가 보장하는 사실 | 보장하지 않는 사실 |
| --- | --- | --- |
| Copy | 이번 요청이 지정한 허용 파일 객체를 열어 기대 digest와 일치하는 bytes를 복사·사후 검증 | 가장 최신 upstream·같은 upstream의 갱신본·데이터 관측 시각 |
| Retained | 지정 세트/입력명의 live·unrevoked bytes를 기대 digest와 확인하여 새 child에 독립 복사 | 원본이 여전히 존재함·원본과 현재 같음·최신 데이터 |

`manifest.created_at/expires_at`은 **이 child와 그 복사 세트의 생성·만료 시각**이다. 원 데이터의 관측/작성/최종 갱신 시각이 아니다.
Retained를 다시 복사하면 child 생성 시각은 새로 생기지만 데이터가 최신화된 것은 아니다. 최초 복사 시각·원본 capture 시각·최근 upstream 확인 시각은 이번 schema가 저장하거나 주장하지 않는다.
`copied_and_boundary_checked`는 실제 소비·변환·그림 값의 의미 증명이 아니다. `reproducibility:"not_claimed"`도 유지한다.

## 사용자가 요청하고 에이전트가 선택하는 흐름

아래는 실행 UI가 아니라 사용자 프롬프트와 클라이언트 작업 규칙의 예시다.

| 사용자 표현 | 선택·확인 |
| --- | --- |
| “이전 그림의 데이터를 그대로 쓰고 색만 바꿔줘.” | report의 모든 필요한 입력명을 확인하여 Retained를 명시 선택. 이전 snapshot 사용과 원본 최신성 미확인을 결과에 알림. |
| “현재 파일의 새 데이터로 다시 그려줘.” | 이번에 접근 가능한 허용 파일과 기대 digest를 확보하여 Copy. 원본 경로가 없으면 파일/허용 위치를 요청. 예전 Retained로 대체하지 않음. |
| “새로 그려줘.” | 데이터 선택이 불명확하면 스타일 수정인지 현재 파일 갱신인지 확인. 만료·접근 오류나 문맥 부재를 snapshot 사용 동의로 보지 않음. |
| “A는 이전 값, B는 현재 파일로.” | A/B 각각 명시적인 name→선택을 만들고 두 입력의 차이를 결과에 함께 표시. 전체 그림에 일괄 ‘최신’ 표식을 붙이지 않음. |

fresh 데이터 요청은 먼저 원본을 다시 확보해야 한다. 서버는 보존 report에서 원 경로를 복원하거나 그 경로를 자동 재개방할 수 없다.
사용자에게 보여 주는 최소 결과 안내는 입력별 `name`, Copy/Retained, 선택된 snapshot ID(해당 시), child 보존 만료, 원본 최신성 미확인이다. 전체 digest는 report로 열 수 있다.
예: “measurements: 이전 artifact의 보존 복사본 사용. 이번 복사본은 <만료 시각>까지 보관. 원본의 현재 상태는 확인하지 않았습니다.”
클라이언트의 일시 요청 문맥에 있는 Copy 사실은 재연결 후에도 `selection.kind`로 확인할 수 있지만, 당시 파일 경로·최신성은 복원하지 않는다.

## 갱신·불일치·여러 입력의 판정

- 기대 `sha256`와 실제 읽은 bytes가 다르면 기존 `invalid_request`로 실패한다. 새 digest를 자동 수용하거나 예전 복사본으로 fallback하지 않는다. 클라이언트는 현재 파일을 다시 읽어 새 기대값·선택을 명시하여 재요청한다.
- 부모 provenance의 같은 `name`과 Copy digest가 다르면 **이전 그림의 해당 입력과 bytes가 다름**만 확인된다. 새 데이터 요청에서는 새 digest를 사용한 Copy가 가능하다. 스타일만 수정하려던 클라이언트는 변경을 알리고 데이터 선택을 다시 확정해야 한다.
- 서버 revision에는 ‘스타일만’ 의도를 강제하는 필드가 없다. 서버가 자동으로 스타일 수정 의도를 판별·거부한다고 약속하지 않는다. 요청 digest 검증과 사용자의 데이터 선택은 서로 다른 책임이다.
- 같은 name·같은 digest는 같은 bytes이며 같은 upstream·같은 의미라는 증명이 아니다. name 변경·입력 추가/누락은 자동 매칭하지 않는다. 여러 입력은 각 name·hash·selection으로 식별하고 style-only에서는 필요한 입력 집합 전체를 확인한다.
- 부모 provenance가 legacy/unsupported/invalid이거나 필요한 입력을 찾지 못하면 비교 불가다. source의 경로 문자열·파일 basename·유사 이름·행 수로 연결을 추측하지 않는다.
- 원본 watcher·주기적 source 검사·백그라운드 최신화·원본 overwrite는 없다. 기존 maintenance는 보존 세트 수명 정리만 담당한다. 복사 중 바뀌었다 돌아온 파일이나 같은 bytes의 의미 변화까지 증명하지 않는다.

## 대안과 구현 판정

선택 receipt 없이 모든 결과를 ‘서버 보존 snapshot, 원본 최신성 미확인’으로만 안내하는 것도 정직하다. 다만 재연결 후 이번 실행이 Copy였는지 Retained였는지 잃으므로 이번 요구에는 receipt를 추천한다.
원본 경로·upstream ID·데이터 as-of·최신성 검사 시각까지 저장하는 동기화 모델은 별도 기능이다. 이번 필드가 이를 암시하지 않도록 한다. 이 선택으로 추가 사용자 결정이나 동기화 프로젝트를 만들지 않는다.

| 사례 | 수명 설계 gate에 추가할 관찰 가능한 oracle |
| --- | --- |
| F1 재연결 | Copy/Retained 혼합 2입력 실제 render→재시작·새 stdio→report resource의 입력별 receipt·hash·child locator를 확인. 결과 envelope·manifest 키는 기존대로. |
| F2 원본 갱신 | A bytes로 부모 생성→원본 B로 변경→A 기대 digest의 Copy는 invalid_request·미게시. B를 명시한 Copy는 B artist 값; Retained는 A artist 값. 어느 실패도 자동 fallback하지 않음. |
| F3 시각 | clock을 옮겨 Retained child 생성→새 manifest 시각과 변하지 않은 A bytes를 확인. capture/as-of/latest 필드를 생성하거나 최신으로 표기하지 않음. |
| F4 선택 경계 | 부모 같은 name/different hash, missing/renamed name, legacy/미지 provenance의 비교 가능/불가를 client 안내 fixture로 판정. 일반 source의 실제 소비 증명과 구분. |
| F5 정보 경계 | report selection 닫힌 shape·예상 ID/name round trip; 운영 설정 절대 경로·원 basename이 새 receipt/오류/locator에 없음. source/log의 기존 경로 노출 가능성은 그대로 별도 취급. |

F1–F5는 구현 후 실행할 사례이며 아직 실행·통과한 gate가 아니다. 수명 설계 G1–G8의 권한·정리·root 교체·삭제/fsync 계약은 이 보완으로 축소하지 않는다.
