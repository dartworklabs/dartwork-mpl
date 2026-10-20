---
orphan: true
---

# 그림 판과 입력 보존의 수명 — 진행 승인 수신·보완 중

2026-10-20 · 재정합 기준 `9c578b25` (PR #510 병합 main `4c28bbd3`의 제품 내용과 동등) · **기존 설계·한정 freeze 예외의 사용자 진행 승인 수신. 입력 선택·최신성 보완을 함께 정합 중이며 제품은 미구현이다.**
[방향 설계](2026-10-20-agentic-plot-direction-design.md) 1단계 중 입력 보존·부모 연결만 다룬다. 단계 전체 완료를 뜻하지 않는다.
기존 R1 검토·교정 뒤 현재 코드와의 한정 정합성 보완이다. 승인 문구·이번 receipt 세부·미구현 상태는 [입력 선택·최신성 보완](2026-10-20-plot-revision-input-freshness-design.md)에 구분해 기록한다. ADR 0004는 정합 중 초안이며, 이 문서 작성은 제품 변경·정책 배치가 아니다.

## 현재 권위와 상태

Handbook은 없고 초기화하지 않았다. 현재 동작과 변경 의도를 구분한다.

| role | path | 현재 실재·계약 / 제안 목표 |
| --- | --- | --- |
| purpose | `AGENTS.md`, 위 방향 설계 | native Figure/Axes, 200줄 상한, 별도 계약 승인 / 아래의 한정 보존 경로 |
| architecture | `src/dartwork_mpl/mcp/artifacts/{policy,store,delivery,transport}.py`, `mcp/server.py` | v1 5멤버·6 manifest 키·32 MiB·7일, render 인자 4개 / 선택 revision 인자·입력 복사 |
| execution | `src/dartwork_mpl/mcp/execution.py` | trusted local Python, cwd·환경 상속 / 입력 사용 요청에서만 명시적 경로 매핑 주입 |
| verification | `pyproject.toml`, `tests/mcp/artifacts`, `tests/test_shipped_colors_hash.py` | `tests/` 수집, Python ≥3.10 / 로컬 3.12·실제 파일·stdio, 새 의존성 없음 |
| evidence | `.superpowers/sdd/2026-10-20-agent-plot-loop/final-review.md` | 삭제된 CSV 복구는 0단계 범위 밖 / 새 클라이언트의 실제 수정 가능성 검증 |
| compatibility | `docs/adr/0001-oklab-centered-color-construction.md` A1, `docs/adr/0003-allow-scoped-mcp-artifact-discovery.md`, `tests/mcp/artifacts/test_artifact_discovery.py` | 현재 18/10/9/2; ADR 0003의 implementation pending은 drift / 사용자가 진행 승인한 ADR 0004의 한정 예외 밖 잠금 유지; 제품 적용 전 |

## 지켜야 할 현재 불변식·설계 이유

- 출하 색 digest와 역사 baseline은 수정·재생성하지 않는다. native Figure/Axes와 기존 5멤버·manifest·7일 계약을 보존한다.
- ADR 0003은 기록된 두 도구·다섯 템플릿만 허용했다. 새 ADR이 앞선 잠금을 스스로 해제하지 못한다.
- MCP 자원으로 전체 source/report/manifest를 이미 읽을 수 있다. 현재 viewer는 artifact reader가 아니며 이 설계의 선행 조건도 아니다.
- Python 실행은 OS sandbox가 아니다. 데이터·소스·해시·경로·모델 출력은 권한이 아니다. datasets에는 어떠한 결과·복사본도 쓰지 않는다.
- 기존 report의 열린 dict와 저장 probe의 성공은 확장 수용성 증거일 뿐 API·보존 계약 승인 증거가 아니다.

## 문제·선택지·추천

0단계의 disposable workspace 수명에서 추론한 실패 시나리오다: CSV가 삭제되면 정확한 source를 회수해도 다시 실행할 수 없다. 삭제 후 실패의 실측 receipt를 이 설계는 주장하지 않는다.
이름·digest는 identity만 남긴다. 접근 가능한 locator와 bytes가 별도로 없으면 입력 보존·수정 복구가 아니다.

| 선택 | 얻는 것·비용 | 판단 |
| --- | --- | --- |
| **서버가 명시적으로 받은 입력만 복사** | 원 cwd 삭제 뒤에도 이름→보존 bytes 연결. 복사 권한·삭제·용량·새 표면 필요 | **진행 승인받은 목표** |
| 호출자가 내구 저장소·locator를 관리 | 서버 복제 없음. 호출자가 접근·권한·수명을 계속 보장해야 함 | 유효 대안이나 disposable 입력 실패를 서버가 해결하지 않음 |
| 부모·digest만 기록 | 가장 작은 lineage-only 중간 단계. 입력 bytes·locator는 제공하지 않음 | 별도 승인 시 가능. 삭제 입력 수정은 명시적으로 unavailable이어야 함 |

최소 여정: CSV를 명시 복사하여 render → 원 cwd 삭제 → 서버 재시작·새 클라이언트 → 기존 자원의 source/report 회수 →
보존 입력을 지정해 스타일 수정 → 실제 native artist 값·행 정책과 부모 bytes 확인. 접근 종료 시 대체 파일을 찾지 않고 실패한다.
전체 파일 탐색·자동 의존성 추론·행/열 추출·child 목록·DB·event bus·provider orchestration·모델 선택 인자는 범위 밖이다.

## public 목표 계약 — 승인 수신·보완 정합 중

기존 네 인자는 그대로 두고 `render_plot(..., revision: object | None = None)` **선택 인자 하나**만 추가한다.
`None`이면 기존 실행·직렬화 경로에 새 필드·주입을 추가하지 않는다. 독립 실행 간 report byte 동일성을 약속하지 않는다.
`revision`은 아래 닫힌 객체다. FastMCP가 파싱한 인자에서 미지 키·잘못된 타입을 거부하며 `parent_artifact_id` 또는 비어 있지 않은 `inputs`가 필요하다.

```text
revision = {schema_version: 1, parent_artifact_id?: UUID4hex, inputs?: [Copy | Retained]}
Copy = {kind: "copy", name, root_id, relative_path, sha256}
Retained = {kind: "retained", name, artifact_id: UUID4hex, input_name, sha256}
```

- `inputs` 기본 빈 목록, 최대 8개·name 유일. name/input_name/root_id는 `[A-Za-z0-9_-]{1,64}`, sha256은 소문자 hex 64자.
- `relative_path`는 UTF-8 ≤1024 bytes의 상대 POSIX 경로다. 빈 요소·`.`·`..`·역슬래시·NUL·절대 경로를 거부한다. 경로 보정은 없다.
- 요청 revision ≤16 KiB·중첩 ≤4. `Copy`는 운영자가 허용한 root 안의 **요청한 파일만**, `Retained`는 해당 입력 세트의 이름만 읽는다.
- raw intent·prompt·transcript·그 digest·설명 metadata는 기본 저장하지 않고 이번 API에도 추가하지 않는다. exact source/기존 로그는 그대로다.

새 도구 **`delete_plot_inputs(artifact_id: str)`** 하나를 끝에 추가하는 한정 예외로 진행 승인을 수신했다.
성공은 `{schema_version:1, artifact_id, state:"deleted"|"absent"}`; 이전 오류 arm의 코드·형태를 그대로 사용한다.
해당 artifact가 소유한 입력 세트 전체를 철회하며 재호출은 `absent`다. source/report/그림·다른 child의 복사본은 삭제하지 않는다.
새 resource/template/static resource/prompt는 없다. 기존 등록의 순서를 보존하며 구현 확인 뒤 발견 수를 **19/10/9/2**로 바꾼다.
기존 render/get 출력 schema·오류 enum, v1 5멤버·6 manifest 키는 그대로다. input/report schema는 아래 범위이며 선택 receipt는 보완 문서가 구체화한다.

```text
report.provenance = {schema_version:1,
  parent: null | {artifact_id, manifest_sha256, source_sha256},
  inputs:[{name, sha256, size_bytes, retained:{artifact_id,name},
           selection: CopySelection | RetainedSelection, evidence:"copied_and_boundary_checked"}], reproducibility:"not_claimed"}
```

`revision`을 쓴 성공 render에만 provenance를 붙인다. `CopySelection={kind:"copy"}`, `RetainedSelection={kind:"retained",artifact_id,input_name}`는 닫힌 객체다. parent는 호출자가 선택한 관계이고 digest는 당시 검증한 bytes의 사실이다.
부모 코드·데이터가 실제 사용되었다는 증명은 아니다. root/depth·substring 기반 source 참조 추정은 만들지 않는다.
부모 provenance 부재/미지 버전/잘못된 내용은 각각 legacy/unsupported/invalid metadata다. 부모 5멤버 검증과 분리하고 추론하지 않는다.
이 부모들도 정상 번들이면 직접 parent로 고정할 수 있다. 새 report schema의 미지 버전은 해석하지 않고 원문 자원 조회는 유지한다.

## 이후 source가 입력을 여는 경로 — 새 opt-in 실행 계약

입력 있는 revision은 검증·복사한 private stage의 파일 경로를 **예약 global `dartwork_inputs`**의 읽기 전용 name→path 매핑으로 제공한다.
예: `pd.read_csv(dartwork_inputs["measurements"])`. 표준 라이브러리 매핑을 실행 bootstrap에서 주입하며 dm core의 MCP 의존성은 없다.
서버가 source를 고쳐 쓰지 않는다. 회수한 source의 옛 경로를 바꿀 필요가 있으면 에이전트가 명시 수정하고 새 exact source로 저장한다.
새 클라이언트는 report의 `retained` 식별자·digest를 다음 `Retained` 인자로 보내고 서버가 bytes를 열어 새 stage에 복사한다.
name·digest만으로 파일을 찾지 않는다. child report의 locator는 **그 child가 새로 소유한 세트**를 가리킨다.
외부 Python에서 source를 실행할 때는 호출자가 매핑을 공급해야 한다. 이식 가능한 독립 source나 전체 재현성을 약속하지 않는다.
cwd·상속 환경·기존 timeout 의미는 유지한다. 매핑은 stdin/상속 FD의 private 채널로 전달하며 argv·환경 변수에 넣지 않는다. provenance에는 매핑의 임시 절대 경로를 기록하지 않는다.
exact source·기존 stdout/stderr·traceback·자동 `exc_msg`에는 사적 경로·내용이 남을 수 있다. “절대 경로 없음”은 주장하지 않는다.

## 복사 권한·안전 경계 — 추천 기본값

principal은 기존의 **로컬 서버 OS 사용자/운영자**다. hosted identity·다중 tenant·새 인증 scheme은 도입하지 않는다.
`DARTWORK_MPL_INPUT_POLICY`가 가리키는 운영자 소유·타인 쓰기 불가 JSON 파일을 시작 시 한 번 읽는다. 기본 미설정은 입력 복사·재사용 거부다.
닫힌 설정은 `{schema_version:1, storage_dir:<절대 경로>, copy_roots:{root_id:<절대 디렉터리>}}`뿐이다. config/저장 JSON은 중복 키를 거부한다. config는 ≤16 KiB의 no-follow regular file로 열어 descriptor의 소유자·쓰기 mode를 검사한다. 모든 config 조상은 root 또는 운영자 소유이며 group/other 쓰기 불가여야 한다(ACL·sandbox 보장 아님).
이 파일을 배치하는 행위가 아래 범위의 **무인 복사·재사용·삭제 허용 grant**다. 도구 문자열·dataset 내용으로 grant를 만들거나 넓힐 수 없다.
운영자는 자신이 복사 권한을 가진 입력만 허용한다. 이 제안은 어떤 실제 파일에도 현재 grant를 부여하지 않는다.
storage_dir은 datasets 밖의 private 디렉터리(0700, 파일 0600)다. 같은 host의 로컬 filesystem·datasets 밖 저장은 운영자 전제이며 범용 mount 탐지로 보장하지 않는다. 설정 검사는 storage_dir 대 artifact/copy root의 동일 객체·조상/자손 중첩을 거부한다. copy_roots끼리의 중첩은 금지하지 않는다.
config·root는 구성요소 전체가 non-symlink인 canonical 경로를 no-follow로 연다. macOS `/tmp`·`/var`·`/etc` 별칭도 거부하므로 실제 경로를 설정한다. 설정 경로는 artifact에 저장하지 않는다.

한 authorization 지점이 설정과 OS principal에서 root/store capability를 만든다. 요청은 root_id를 이 capability에서 선택할 뿐 경로로 권한을 만들지 못한다.
root를 시작 시 디렉터리 descriptor로 고정하고 각 요청에 duplicate한다. 루트 경로가 교체되면 새 copy 요청은 거부하고 운영자 재시작을 요구한다.
각 descendant를 `dir_fd`·`O_NOFOLLOW`로 하나씩 열고 중간 요소는 directory, 마지막은 `O_NONBLOCK|O_NOCTTY`로 연 뒤 `fstat` regular file로 확인한다. unchecked symlink는 따르지 않는다.
복사 원본은 이미 연 regular 객체가 범위이며 origin·hardlink 유일성은 증명하지 않는다. rename 경쟁에서 경로를 다시 열지 않는다. store 소유 파일의 소유자·mode·단일 link·객체 identity 검사는 약화하지 않는다.
문자열 realpath 검사는 권한 근거가 아니다. 필요한 descriptor 연산이 없는 OS는 보존 기능만 configuration_error로 거부하고 unsafe fallback은 없다.
startup가 장기 descriptor·store 잠금을 소유한다. shutdown/부분 실패는 새 admission을 막고 수용한 call·owned worker를 drain/회수한 뒤 FD·잠금을 닫는다. per-call descriptor·worker·stage는 성공/오류/취소/timeout 모두 정리한다.

서버 자신의 복사에 **8개/파일 8 MiB/요청 총 32 MiB**, 입력 저장소에 **512 MiB·128세트** 상한을 고정 제안한다(설정 override 없음).
metadata·revoked 잔여물·pending stage·진행 중 예약도 세고, 살아 있는 세트는 자동 축출하지 않는다. payload 한도는 metadata와 별개다. 예약은 요청 payload 상한+metadata/marker 여유를 포함하고, 부족하면 실행 전 publication_error로 거부한다.
크기·누적 bytes는 streaming 중에도 제한한다. 64 KiB chunk로 복사·해시하고, 예상 digest 불일치·소실·비정규 파일·초과·읽기 실패는 모두 거부한다.
입력 복사와 실행 후 전체 재읽기의 data 읽기는 초과 탐지까지 최대 65 MiB다. Retained hash 검증은 복사와 한 pass로 한다. 이 한도는 parent bundle 검증·bounded manifest/metadata·실행 자체의 읽기를 포함하지 않는다. 복사 10초·사후 검증 5초의 별도 deadline에 owned I/O worker 종료·회수를 요구한다.
회수 확인 전 예약/stage를 해제·재사용하지 않는다. 15초는 두 I/O phase의 deadline 합이고 Python timeout과 별개다. kernel wait·worker 회수·export/publication까지 포함한 wall-clock 상한이나 OS quota를 약속하지 않는다.
보존 render·delete·maintenance는 store 내 직렬 처리한다. 같은 host의 한 store에서 두 번째 서버는 보존 startup lock 실패로 해당 기능만 거부한다. cross-host lock exclusion은 보장하지 않는다.

## 저장·수명·삭제·실패 — 추천 기본값

v1 번들에 여섯째 멤버를 넣지 않는다. 위 private root에 `<artifact_id>/inputs.json`과 고정 생성 파일명으로 입력을 보관한다. 내부 stage는 정확한 `.pending-<UUID4hex>/`뿐이며 payload·metadata fsync 뒤 `<artifact_id>/`로 rename·root fsync하여 InputSetCommitted가 된다. 이 namespace 구분은 public schema가 아니다.
`inputs.json`은 내부 `{schema_version:1,artifact_id,created_at,expires_at,files:[{name,sha256,size_bytes}]}`(≤16 KiB)이며 public resource가 아니다.
files의 순서로 `000.bin`–`007.bin`을 정한다. 호출자 경로·원 basename은 저장하지 않고 lookup은 검증한 ID/name과 capability만 받는다. 인덱스·dedupe·별도 revision DB는 없다.
원 파일 전체 bytes를 복사한다. 열 선택·변환·재인코딩을 하지 않는다. copied bytes는 publication 시 child 소유이며 그 artifact와 같은 ID·UTC created_at·expires_at을 쓴다. CopiesChecked 뒤 clock을 한 번 읽어 양쪽에 전달하며 expires_at=created_at+**7일**이다.
`Retained`도 새 child에 독립 복사·7일 grant를 적용한다. 이는 원본 수명을 연장하지 않지만 반복 수정으로 데이터 보존이 이어질 수 있는 **명시 승인 정책**이다.
읽기는 어느 수명도 연장하지 않는다. 부모 copy 만료/철회는 이미 commit된 child copy에 전파하지 않는다. 전체 파생본 철회는 제공하지 않는다.
copy_roots 축소는 다음 재시작부터 새 Copy만 막는다. 기존 bytes 철회는 delete 도구로 세트별 수행한다. 설정 해제는 모든 보존 접근을 막되 bytes를 삭제하지 않는다.
delete는 기존 grant·직렬 lock 아래 모든 상태를 처리한다. 유효 metadata·live expiry·matching bundle은 삭제의 선행 조건이 아니다.

| 삭제 대상 상태 | 처리·자동 정리 범위 |
| --- | --- |
| live | 공통 삭제 순서로 철회·제거한다. |
| expired-unswept | `expired`로 거절하지 않고 제거한다. 검증된 만료의 maintenance도 같은 순서다. |
| revoked residue | marker를 유지하며 공통 삭제를 재시도한다. |
| corrupt / metadata-less | 수동 delete로 안전한 고정 bytes를 제거한다. metadata 부재를 미게시·만료 증거로 삼지 않는다. |
| uncommitted orphan | 정확한 pending namespace의 소유권이 확인된 세트만 startup가 공통 순서로 제거할 수 있다. |
| unknown commit | bundle 부재·손상·관찰 불능은 rollback 근거가 아니다. 수동 delete는 허용하고 자동 제거는 자체의 검증된 expiry까지 보류한다. |

삭제는 owned worker 종료를 기다린다. 검증된 UUID에 대응하는 committed/pending 디렉터리를 no-follow dir_fd로 열고 소유권·객체 identity를 확인한다. 고정 `000.bin`–`007.bin`, `inputs.json`, `.revoked`만 다루며 recursive 삭제·이름 추측은 없다.
공통 순서(user delete·검증된 expiry·확실한 자기 orphan): `.revoked` 원자 생성·파일 fsync·세트 directory fsync → 고정 payload unlink → metadata unlink → 세트 directory fsync → marker 마지막 unlink → rmdir → storage root fsync → `deleted`다.
미지 항목·symlink·비정규 파일·불안전한 소유권은 보수적으로 거부하고 그 항목을 남긴다. 안전한 고정 파일만 제거할 수 있고 남은 세트의 marker는 보존/재영속화하여 재시도한다. 결과는 `publication_error`이며 잔여물은 계속 용량에 센다.
어떤 durability barrier라도 실패하면 `deleted`/`absent`를 반환하지 않는다. `absent`도 안전한 namespace 부재 확인과 root fsync 뒤에만 반환한다. marker 생성/fsync 실패 시 payload를 지우지 않고 오류·현재 프로세스 접근 거부만 보장하며 재시작 철회는 미보장이다. fsync 순서·process-crash 복구 의도이며 hardware power-loss 보장은 아니다.
입력 lookup은 grant→안전한 세트 열기→revoked→metadata 검증→만료→matching bundle commit→복사 중 파일 검증 순이다. revoked/없는 세트는 not_found가 만료보다 우선하고 검증된 만료는 expired다. bundle 부재는 not_found, 손상은 corrupt, 관찰 불능은 publication_error로 거부한다.
commit 관찰은 기존 `MAX_MANIFEST_BYTES`(512 KiB) 한도·초과 탐지의 manifest-only read다. root 생성·cleanup·`ArtifactStore.load` 호출이 없고 matching ID·시각만 검증한다. 입력 세트와 bundle의 commit이 확인되어야 재사용할 수 있다.
만료 시 접근은 즉시 거부한다. startup·매 작업·60초 maintenance는 활성 작업 종료 뒤 위 규칙으로 정리한다. 서버가 꺼져 있으면 bytes는 다음 시작까지 남고 unlink는 secure erase·백업 제거가 아니다. 응답을 잃으면 client가 ID를 몰라 개별 삭제할 수 없는 복사본도 자체 7일 만료·offline cleanup까지 용량에 남는다. listing/idempotency는 추가하지 않는다. 이 한계도 진행 승인받은 범위다.

순서: Parse → Grant/ParentPinned → QuotaReserved → InputsCopied → Executed → CopiesChecked → InputSetCommitted → BundleCommitted → Ready. parent-only는 입력 단계·세트 생성을 건너뛴다.
실행 후 모든 copy의 digest·크기를 다시 확인한다. 실패/변경이면 게시를 거부한다. 코드는 이미 실행되었을 수 있으며 부작용을 되돌리지 않는다.
report의 digest/size는 실제 복사 bytes에서 계산한다. `copied_and_boundary_checked`는 그 bytes와 실행 후 전체 재읽기가 일치했다는 뜻이며 Python의 실제 소비·그려진 값 증명이 아니다.
중간에 바뀌었다 돌아온 파일·선언했지만 읽지 않은 파일도 가능하다. semantic 연속성은 일반 경우 unchecked이고 지원 fixture의 artist 검사는 별도다.
입력 세트는 bundle manifest보다 먼저 commit한다. ready는 양쪽 commit 뒤에만 반환한다. 실패/취소 시 artifact stage context가 완전히 종료된 뒤 직렬 lock 안에서 공개 store surface로 관찰한다. matching commit이면 보존하고, 이 call 소유·미게시가 확실한 세트만 공통 순서로 rollback한다. rename 뒤 fsync/cleanup 실패로 불명확하면 보존·계산한다.
startup는 소유권이 확인된 pending만 rollback한다. committed namespace는 metadata가 없거나 손상되어도 미게시 증거가 아니다. 유효 metadata의 미철회 committed 세트는 현재 artifact root에 bundle이 없어도 자체 expiry까지 보존·계산한다(명시 delete는 별도). `DARTWORK_MPL_ARTIFACT_DIR`/HOME/설정·mount 변경은 삭제 근거가 아니며 원 root를 만료 전에 복원하면 재사용 가능하다. 관찰 불능/손상 잔여물은 거부·계산·운영자 수리 대상이다. 영속 artifact-root binding은 추가하지 않는다.
cleanup은 이 저장소의 제한된 namespace만 읽고 다른 파일을 스캔하지 않는다. 기존 artifact store의 별도 crash 잔여물·전체 quota 수리는 범위 밖이다.
worker 회수와 미게시가 확인된 자기 예약·stage만 해제한다. commit 관찰 불능 잔여물은 계속 용량에 센다. 재시도는 새 ID다. 이 설계는 idempotency key·임의 Python exactly-once를 추가하지 않는다.

부모는 **admission 시 live인 verified bundle**을 요구하는 정책을 추천한다. 그때 manifest/source bytes와 digest를 immutable 값으로 고정하고 실행 중 만료되어도 다시 열지 않는다.
Retained도 admission에 live·unrevoked 세트를 검증·복사하여 pin한다. 직렬 작업 중 만료되어도 이미 수용한 stage는 계속할 수 있고 child는 새 7일이다. 대기 중인 delete는 그 작업 종료 뒤 적용되며 이미 commit된 child로 전파되지 않는다.
자식은 자기 5멤버만 검증한다. 부모 만료/삭제/손상은 별도 ancestor lookup의 expired/not_found/corrupt이며 healthy child를 corrupt로 바꾸지 않는다.
입력 lookup 역시 별도다. 자체 child bundle은 정상이어도 입력은 철회/소실/만료될 수 있다. 입력을 조용히 복원·대체하거나 부모를 재생성하지 않는다.
오류 매핑: 형식·권한/digest/경계 거부→invalid_request; 설정→configuration_error; 입력/부모 lookup→not_found/expired/corrupt;
quota·I/O deadline·commit/삭제 실패→publication_error; 실행 실패→기존 실행 코드. 안전한 field 이름을 쓰며 제출 경로·내용을 오류에 추가하지 않는다.

## 수용 판정 G1–G8 — 구현 후 실행할 제안, 지금 통과한 gate가 아님

Python 3.10 최소 문법, 로컬 3.12, stdlib seeded properties, 실제 temp files/store/MCP stdio만 사용한다. LLM·계정·새 의존성은 필요 없다.
신규 시험은 `tests/mcp/artifacts/`에 둔다(`testpaths=["tests"]`). 파일 이름·CI 등록은 구현자가 기존 CI 담당과 정하며 사용자 선택 사항이 아니다.
기본 실행: `UV_PYTHON=3.12 uv run pytest tests/mcp/artifacts tests/test_shipped_colors_hash.py`; JUnit 실행 증거는 기존 3.12 guard에 등록한다.

| ID | 실행 가능한 oracle |
| --- | --- |
| G1 호환 | 동일한 controlled execution result에 대한 legacy 직렬화 bytes·로그 보존; 별도 실제 실행은 안정 schema/행동만 비교. 정확한 schema diff는 revision·delete·provenance·global·설정의 승인 delta, 발견은 구현 확인 뒤 19/10/9/2; 기존 5멤버·6 manifest 키·32 MiB·7일 유지. |
| G2 동결 | shipped-color 시험 무수정 통과, 역사 baseline/digest diff 0. 기존 discovery identity·상대 순서 유지, 추가는 delete 한 개뿐. |
| G3 순수 규칙 | seeded bounded JSON/경로 입력은 값 또는 named refusal; 고정 provenance 직렬화 round trip·결정성; quota·전이 sequence 불변. parent legacy/unknown/invalid metadata에서 ancestry를 추측하지 않음. |
| G4 실제 경계 | root 밖·symlink·ancestor/root 교체·FIFO/비정규 파일·성장·digest 불일치에서 실제 sentinel/descriptor로 범위 확인. 강제로 막은 owned I/O worker에 10초/5초 deadline·취소를 직접 일으켜 process 회수·FD/stage/예약 잔여 0, counting seam으로 입력 복사/사후검증 read ≤65 MiB와 별도 manifest 한도 확인; 오류 문구·mode 000은 oracle 아님. |
| G5 독립성 | parent pin→child commit→부모 만료/삭제/1-byte 손상→재시작·실제 stdio에서 child 5멤버 bytes 유지. child read 성공과 ancestor lookup 실패를 각각 확인; child copy는 독립 유지. |
| G6 실제 복구 | CSV→매핑 사용 render→원 cwd 삭제→재시작·새 stdio 클라이언트→report/source 회수→Retained로 스타일 수정. 실제 native artist 값·순서·결측/제외 행 정책을 독립 기대값과 비교; 부모 bytes 불변. 일반 임의 source 의미는 unchecked. |
| G7 보존 정책 | 주입 clock으로 7일·pin 후 만료·공통 ID/시각·읽기 불연장·child 새 7일·revoked 우선순위, 실제 bytes/예약으로 8개/8 MiB/32 MiB/512 MiB/128세트·live 축출 없음·두 서버 lock 거부 확인. 위 6개 삭제 상태·반복·unknown entry/unsafe member 잔여 계산, marker 실패·각 fsync/unlink/rename 실패에서 공통 순서와 오류를 owned filesystem seam+실제 재시작으로 확인한다. stage 종료 뒤 rename/fsync 실패(artifact cleanup 성공/실패 양쪽), pending crash 정리·응답 전 commit 보존을 판정한다. 실제 재시작 사이 DARTWORK_MPL_ARTIFACT_DIR·HOME·missing mount/root를 바꿔 committed bytes 0삭제·조회 거부 후 원 root 복원·만료 전 재사용을 확인한다. process-crash/fault 결과는 hardware power-loss 증명이 아니다. |
| G8 증거·수집 | 변했다 돌아온/읽지 않은 copy는 소비 증명 아님; 사후 실패는 미게시. provenance/metadata의 경로 배제와 기존 source/log/자동 exc_msg를 구분한다. 실제 import·stdio start/close·부분 startup 실패·설정 없음/손상·미지원 OS에서 legacy 유지·보존 거부·잔여 자원 0 확인. 지원 FastMCP 2/3의 출하 stdio·in-process session 경로에서 동시 client session과 blocked call 중 close로 admission 중지→call/worker drain→FD/lock close의 단일 owned lifecycle을 검증하며 once-per-process를 가정하지 않는다. 기존 ENTRY_POLICIES/entry-policy 시험에 delete를 등록하고 import/authority RED/GREEN·수집·JUnit 실행을 기록한다. |

G1–G8은 CI가 매 변경에 실행·보호하도록 등록된 뒤 merge gate라 부른다. 3.10 호환·실행 불가 항목은 숨기지 않고 보고한다.
이 검증은 전체 재현성·일반 semantic proof·remote CI·배포 준비를 인증하지 않는다. 새 slice/provider 프레임워크는 필요 없다.

## 구현 책임과 승인 수신 범위

추천 배치: 기존 artifacts capability가 소유한다. `policy.py`는 순수 파싱·상태/직렬화, 새 `artifacts/inputs.py`는 grant·복사/삭제·보존 I/O를 맡는다.
`delivery`가 store/inputs를 조합하고 transport는 schema/오류를 맡는다. execution은 opt-in 매핑만 받는다. 새 state/refusal은 내부 immutable 값으로 구분하고 wire 문자열은 transport에서만 매핑한다.
현재 StagedBundle의 ID는 private이고 output_stem만 공개다. store에 읽기 전용 stage ID와 제한된 commit 관찰/자기 미게시 stage rollback surface를 **새로 설계·검증**한다. delivery/inputs는 private 필드·저장 경로를 해석하지 않는다.
현재 server는 import 시 global FastMCP·store를 구성하고 lifespan이 없다. global mcp·등록 순서는 보존하되 input config/descriptor/lock/maintenance는 새 lifecycle이 생성·주입·drain·close한다. lifespan/session 동작을 검증하여 단일 소유를 보장하고 import만으로 자원을 열지 않는다.
미설정은 보존 비활성, 설정 오류·미지원 descriptor/lock은 보존 configuration_error다. parent-only revision은 input policy 없이 허용하고 기존 render/get/자원/발견의 경로·오류 의미는 유지한다. lifespan의 부분 실패/이중 close/취소 cleanup도 검증한다; 서버 전체 시작 실패로 확대하지 않는다.
방향은 transport→delivery→{inputs,store,execution}, inputs→policy이며 순수 policy는 I/O·타 capability를 import하지 않는다.
public `__all__`/import-graph와 authorization 생성 경계를 검증한다. 새 DB·범용 repository·shared 승격이나 기존 runner 분해는 이 작업에 필요 없다.

1. **설계 진행 승인 수신:** 앞서 설명한 revision/report/global/config/delete·명시 복사·한도·각 판 7일·독립 파생본·삭제·root 변경 보존·응답 소실/오프라인 삭제 한계에 사용자가 “좋아 진행해”라고 답했다. 실제 입력 grant·정책 배치와는 구분한다.
2. **한정 freeze 예외 진행 승인 수신:** 두 승인을 설명받은 같은 응답으로 [ADR 0004](../../adr/0004-retained-input-revision-contract.md)의 ADR 0001 A1·ADR 0003 한정 부분 대체와 delete 한 개를 더한 19/10/9/2 범위에 진행 승인을 수신했다. 기존 ADR·역사 baseline은 수정하지 않는다.

입력 선택·최신성 보완은 그 응답의 추가 질문을 구체화한 엔지니어링 정합이다. 같은 승인을 반복 요구하지 않는다. 보완 검토 뒤 시공 계획을 만들며 제품 코드·실제 정책/입력 grant·MCP 등록은 이 문서 작성으로 변경되지 않는다.
