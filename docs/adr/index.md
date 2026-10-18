---
orphan: true
---

# Architecture decision records

This is a derived navigation index. Numbered records own their status and
relationships; this index does not establish current implementation or approval.
Proposed relationships have no effect and are excluded from approved successors.

| 번호·기록 | 제목 | 한 줄 결정 | 원문 상태 | 변경 대상·범위 | 승인된 후속 관계 |
| --- | --- | --- | --- | --- | --- |
| [ADR 0001](0001-oklab-centered-color-construction.md) | OKLab 중심 색 생성과 모델 기반 상대 Y 계약의 분리 | Generate in OKLab/OKLCH, preserve shipped outputs and isolate validation models. | Accepted | — | ADR 0003 partially supersedes only A1's full-live `mcp_discovery` equality scope; implemented ([evidence](../superpowers/specs/2026-10-18-mcp-artifact-delivery-design.md)). |
| [ADR 0002](0002-separate-shipped-color-compatibility-from-oklab-authoring.md) | shipped 색 호환성과 OKLab authoring의 분리 | Reject the authoring-extension procedure; ADR 0001 remains authoritative. | **Rejected** (2026-08-02) | — | — |
| [ADR 0003](0003-allow-scoped-mcp-artifact-discovery.md) | Allow scoped MCP artifact discovery | Approve exactly two artifact tools/five templates with historical-core and full-live discovery checks; implemented with local integration evidence ([spec](../superpowers/specs/2026-10-18-mcp-artifact-delivery-design.md)); final branch review pending. | Accepted (2026-10-18) | 부분 대체: ADR 0001 A1의 `mcp_discovery` live 전체 exact 일치 범위만 | — |
