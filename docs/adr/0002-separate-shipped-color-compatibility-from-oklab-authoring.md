---
orphan: true
---

# ADR 0002: shipped 색 호환성과 OKLab authoring의 분리

- 상태: **Rejected** (2026-08-02)
- 원래 상태: Accepted (2026-07-27)
- 정본: [ADR 0001](0001-oklab-centered-color-construction.md)이 계속 유효하다
- 기각한 전문: 커밋 `8ce8b852` — 이 파일 1,572줄과
  `docs/superpowers/specs/2026-07-27-oklab-authoring-extension-design.md` 13,337줄

## 무엇을 기각하는가

이 ADR과 짝을 이루는 설계문서는 shipped 색을 동결한 채 별도의 OKLab authoring
레인을 추가하려 했다. **그 목표는 옳다.** 기각하는 것은 목표가 아니라 거기에
도달하려고 채택한 절차다.

## 기각 사유

**1. 완료 조건이 이 저장소의 개발 환경에서 원리적으로 도달 불가능하다.**

설계문서 §15 acceptance criteria 18~28항은 아직 존재하지 않는 Linux 전용 정적
ELF supervisor 위에서만 만들 수 있는 증거를 요구한다. 같은 문서가
`:13723-13724`에서 "V1 environment publication is available only on Linux x86-64
and AArch64; Darwin and every other platform fail native preflight before Python"
이라고 스스로 밝힌다. 개발이 이루어지는 Darwin에서는 완료 조건을 만족시킬 수
없으므로, 이 계약을 따르는 한 브랜치는 영구히 머지 불가로 고정된다.

**2. 선행 ADR의 안전장치를 해제했다.**

원문 머리말은 이 결정을 "supersedes the overlapping migration requirements of
ADR 0001 **without using ADR 0001 as baseline or review evidence**"로 규정하고,
본문에서 "Files in a dirty worktree, including an earlier spec, ADR, prototype
implementation, or prototype JSON, have no authority for this decision"이라고
선언했다. 그 결과 ADR 0001이 걸어둔 exact-일치 잠금(200 palette · 2 cycle ·
43×256 LUT · curated · discrete의 byte-for-byte 동일성)과 이미 동작하던 구현이
함께 권위를 잃었다. **색을 지키던 장치를 스스로 해제한 것이 사고의 직접
원인이다.**

**3. 분량의 65%가 색 설계가 아니다.**

13,868줄 중 실제 설계 결정은 약 4,766줄이고 나머지 약 9,104줄은 검증 절차를
검증하는 메타 요구다 — seccomp, `pivot_root`, `memfd`, `clone3`, `LD_AUDIT`,
executable `.pth`, `sitecustomize`, sealed filesystem, 그리고 predecessor Git
객체 1,008개의 authority 전달 계약. 어느 것도 "색이 아름다운가"와 "코드가
맞는가"에 정보를 더하지 않는다.

**4. 종결 조건에 외부 판정기가 없었다.**

작업은 "독립 리뷰어 A·B가 모두 PASS할 때까지"를 종결 조건으로 삼았다. 그러나 두
리뷰어가 같은 문서만을 근거로 판정하는 구조에서는 언제나 새로운 gap을 찾을 수
있으므로 이 루프는 수렴하지 않는다. 실제로 마지막 7시간의 산출물은 코드가 아니라
문서 2개였다. 리뷰는 반복해서 통과했지만 사람은 한 번도 검토하지 못했다.

## 대신 채택한 것

이 ADR이 9,104줄로 보장하려던 단 하나의 실질 — **출하되는 색이 바뀌지 않았음**
— 은 `tests/test_shipped_colors_hash.py` 한 파일로 대체한다. 다섯 표면
(named 1,272 · colormaps 99×256 · presets 588 · discrete 1,344 · curated 15)의
sha256을 각각 고정하며, 색이론 지식 없이 pass/fail로 판정된다. 이 판정기는 main과
이 브랜치에서 모두 통과한다. 즉 색 불변은 이미 기계적으로 증명되어 있다.

설계문서에서 코드로 복원할 수 없는 계약은
[ADR 0001의 부록](0001-oklab-centered-color-construction.md)으로 흡수했다.
특히 2단계 gamut 경계를 교체 금지로 봉인하는 조항은 그대로 살렸다.

## 남길 교훈

`AGENTS.md`의 "설계 문서와 에이전트 작업 규칙"으로 옮겨 적었다. 요지는 넷이다.
설계문서는 200줄을 넘기지 않는다. 적대적 리뷰는 외부 판정기가 있을 때만 쓴다.
ADR은 선행 ADR의 잠금을 해제할 수 없다. 완료 조건에 이 저장소의 개발 환경에서
실행할 수 없는 것을 넣지 않는다.
