---
orphan: true
---

# Architecture decision records

This is a derived navigation index. Numbered records own their status and
relationships; this index does not establish current implementation or approval.
Proposed relationships have no effect and are excluded from approved successors.

| 번호·기록 | 제목 | 한 줄 결정 | 원문 상태 | 변경 대상·범위 | 승인된 후속 관계 |
| --- | --- | --- | --- | --- | --- |
| [ADR 0001](0001-oklab-centered-color-construction.md) | OKLab 중심 색 생성과 모델 기반 상대 Y 계약의 분리 | Generate in OKLab/OKLCH, preserve shipped outputs and isolate validation models. | Accepted | — | [ADR 0003](0003-allow-scoped-mcp-artifact-discovery.md) 부분 대체 |
| [ADR 0002](0002-separate-shipped-color-compatibility-from-oklab-authoring.md) | shipped 색 호환성과 OKLab authoring의 분리 | Reject the authoring-extension procedure; ADR 0001 remains authoritative. | **Rejected** (2026-08-02) | — | — |
| [ADR 0003](0003-allow-scoped-mcp-artifact-discovery.md) | Allow scoped MCP artifact discovery | Permit exactly two artifact tools/five templates with historical-core and full-live discovery checks. | Accepted — approved 2026-10-18; implementation pending | 부분 대체: ADR 0001 A1의 `mcp_discovery` live 전체 exact 일치 범위만 | — |
| [ADR 0004](0004-retained-input-revision-contract.md) | Retained input revision contract | Propose one delete tool and bounded opt-in revision/input retention, preserving artifact v1 and frozen baselines. | 제안 | 부분 대체: ADR 0001 A1의 `mcp_discovery` live 전체 exact 일치 범위와 ADR 0003의 닫힌 7개 추가 목록만 — 결정 1·2의 `delete_plot_inputs` 한 개 추가 및 그 투영 범위에 한정 | — |
| [ADR 0005](0005-capability-slices-and-test-colocation.md) | 기능 슬라이스, 테스트 동거, 경계 검사로 집행하는 구조 | Move code into capability slices with declared surfaces and colocated tests, enforced by a boundary checker; public interface and ADR 0001–0004 freezes unchanged. | Accepted (2026-10-22) | — | — |

ADR 0003의 원문 상태는 역사 기록 그대로다. 실제 구현 상태는 [artifact delivery 설계의 검증 기록](../superpowers/specs/2026-10-18-mcp-artifact-delivery-design.md)과 현재 코드를 확인한다. ADR 0004의 제안 관계는 미발효이며 승인된 후속 관계에 포함하지 않는다.
