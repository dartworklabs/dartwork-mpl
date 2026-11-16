---
handbook_format: markdown
catalog_schema: 1
orphan: true
---

# dartwork-mpl System Handbook

이 Handbook은 dartwork-mpl이 지금 무엇을 지키고 어떻게 검증하는지 설명한다. 코드에서 바로 읽히는 것은 위치만 가리키고, 코드만 봐서는 알 수 없는 의도·경계·불변식·합격 기준을 쓴다. 작업 전에는 아래 catalog에서 작업과 관련된 topic만 골라 읽는다.

## Catalog

| order | role | file | responsibility | read or update when |
| --- | --- | --- | --- | --- |
| 1 | `purpose` | [purpose.md](purpose.md) | 존재 이유, 사용자, 리포 범위, 영역별 진실 소스 | 새 기능·제거·리포 범위 변경, 어떤 파일이 정답인지 모를 때 |
| 2 | — | [philosophy.md](philosophy.md) | 개발 철학: 리포에 두는 것, 타입으로 말하기, slice 독립, skill의 범위, 커밋 원칙 | 무엇을 넣을지·어떻게 짤지·어떻게 커밋할지 판단할 때 |
| 3 | `architecture` | [architecture.md](architecture.md) | slice 구조, compose와 platform, functional core 경계, 불변식, 채택한 리팩터 목표 | 모듈을 만들거나 옮길 때, 의존을 추가할 때, 불변식을 건드릴 때 |
| 4 | `verification` | [verification.md](verification.md) | 게이트별 측정 대상·적용 조건·명령·합격 기준 | PR 합격 판정, 게이트 추가·완화, baseline 갱신 |
| 5 | — | [change-flow.md](change-flow.md) | 결정 권한, 설계에서 머지까지의 흐름, 리포 잠금, 릴리스, 용어 | 결정이 누구 몫인지, 잠금·릴리스 절차가 필요할 때 |

연속으로 읽을 때는 위 순서를 따른다.

## Semantic filemap

| path pattern | 의미 | 수정할 때 같이 볼 topic |
| --- | --- | --- |
| `src/dartwork_mpl/<slice>/` | 코어 slice 하나. `model`, `decide`, `edges`, `measure`/`apply`, 개념 이름의 모듈, `assets/`, `tests/`. 다른 slice를 import하지 않는다 | architecture |
| `src/dartwork_mpl/<slice>/edges.py` | 그 slice의 이름 붙은 엣지 케이스(`EDGES`, `<NAME>_EDGES`). 새 특수 처리는 목록 끝에 더한다 | architecture |
| `src/dartwork_mpl/compose/<slice>.py` | 그 slice가 다른 slice를 쓰는 자리. 공개 함수를 조립만 한다. 루트만 import한다 | architecture |
| `src/dartwork_mpl/vocab/` | slice들이 함께 쓰는 순수 어휘. 모듈 하나가 어휘 하나(`axis`, `align`, `box`, `edge`, `projection`, `number`, `locale`) | architecture |
| `src/dartwork_mpl/length/`, `colorspace/` | 두 slice 이상이 쓰는 순수 타입과 산술(platform) | architecture |
| `src/dartwork_mpl/geometry/` | 두 slice 이상이 쓰는 figure 측정 코드(platform, matplotlib) | architecture |
| `src/dartwork_mpl/edgecase/` | 엣지 케이스 등록 장치(platform) | architecture |
| `src/dartwork_mpl/hidden/` | 자동 동작의 보고. 도구가 스스로 바꾼 것을 한 줄씩 stderr에 쓴다(`dm.quiet()`로 끈다) | philosophy(7절), architecture |
| `skills/dartwork-mpl/` | skill의 단 하나의 원본. `npx skills add`가 여기서 읽고, 패키지는 `src/dartwork_mpl/guide/assets/skill` 링크로 같은 폴더를 싣는다 | purpose, verification(지침 게이트) |
| `src/dartwork_mpl/guide/assets/` | 안티패턴 목록과 skill 링크. 에이전트가 읽는 전부 | purpose, verification(지침 게이트) |
| `src/dartwork_mpl/color/assets/`, `tests/test_shipped_colors_hash.py` | 출하 색 값과 그 고정점 | architecture(미감 불변식), verification |
| `tests/visual/` | 픽셀 장면과 기준 이미지 | verification |
| `tests/corpus/` | 개발용 코퍼스. 현실적인 차트 스크립트(`charts/`)와 대충 그린 것(`rough/`), 증거를 세는 `tally.py`. 기능을 지우거나 더할 때의 근거다 | philosophy(1절), verification |
| `tests/architecture/` | 경계(`boundaries.py`), 조립 규칙(`composition.py`), 도메인 파일 규칙, 순수 import, fitness | architecture, verification |
| `docs/adr/` | 결정 기록과 index | change-flow |
| `docs/hub-contract.md` | 허브(`mpl.dartwork.io`)와 약속한 것 | purpose |
| `docs/example-candidates.md` | 재구성하며 지운 기능의 기록과 원본을 읽는 커밋 | philosophy(1절) |
| `.github/workflows/` | CI(`lint`, `test`)와 릴리스 | verification, change-flow |
