---
orphan: true
---

# 이 세션에서 허브를 고칠 때

소유자는 이 리포의 세션 하나에서 허브(`dartworklabs/dartwork-mpl-hub`, `mpl.dartwork.io`)도 고친다. 이 topic은 허브로 넘어갈 때의 순서와 주의를 적는다. 허브가 무엇을 지키는지는 허브의 Handbook이 정본이고, 여기서는 되풀이하지 않는다. 두 리포의 약속은 [../hub-contract.md](../hub-contract.md)에 있다.

## 1. 허브의 Handbook을 먼저 읽는다

허브 안에서는 **허브의 규칙이 이 리포의 규칙을 이긴다.** 이 리포의 `CLAUDE.md`와 Handbook(Python, slice, `uv`)은 허브 코드에 적용되지 않는다. 허브는 SvelteKit·Tailwind·Svelte 5, `pnpm`, `make`다.

허브 `docs/handbook/index.md`의 catalog에서 작업에 맞는 topic만 고른다.

| 하려는 일 | 허브에서 읽을 topic |
| --- | --- |
| 화면·컴포넌트·스타일 | `design.md`, `architecture.md`(토큰과 slice) |
| 갤러리 예제, 라이브러리 고정 | `architecture.md`(라이브러리와의 계약, 예제), `operations.md` |
| 사용자 문서 | `architecture.md`(사용자 문서) |
| MCP, 분석, 배포 | `operations.md` |
| 승인이 필요한지 | `change-flow.md` |
| 명령 | `commands.md`, `setup.md` |

현재 상태를 바꾸는 변경은 같은 PR에서 허브 Handbook의 해당 topic을 고친다. 되돌리기 어렵거나 trade-off가 있으면 허브 `docs/adr/`에 ADR을 쓴다(번호는 허브의 것을 잇는다).

## 2. 작업 자리는 허브 worktree다

허브의 공유 체크아웃(이 리포 옆 `../dartwork-mpl-hub`)은 고치지 않는다. 다른 세션이 쓴다. 일마다 `origin/main`에서 worktree를 만든다.

```bash
cd ../dartwork-mpl-hub && git fetch origin
git worktree add -b <종류>/<이름> ../dartwork-hub-<이름> origin/main
cd ../dartwork-hub-<이름>
ln -s ../dartwork-mpl-hub/.env .env      # 비밀값은 공유 체크아웃의 .env 하나뿐이다
pnpm install --frozen-lockfile
```

병합한 뒤 worktree와 로컬·원격 브랜치를 지운다. 브랜치 이름은 허브 관례(`feat/`, `fix/`, `docs/`, `design/`)를 따른다.

## 3. 검증

- **`make verify`**(check, lint, test, build)가 통과해야 PR을 연다. 돌리지 않은 검사는 통과로 적지 않고 NOTRUN으로 적는다.
- **화면 변경은 눈으로 본다.** `pnpm build` 뒤 `pnpm preview --port 4317 --strictPort`를 백그라운드로 띄우고 Playwright로 찍는다. 데스크톱(1440px)과 휴대폰(390px), 라이트와 다크를 본다. 서버는 `kill $(lsof -ti tcp:4317)`로 끈다. `pkill -f`는 쓰지 않는다(공유 머신이다). 서버를 띄운 채 다시 빌드하면 자산이 404가 되므로 서버를 다시 띄운다.
- **Playwright MCP는 작업 폴더에 `.playwright-mcp/`를 남긴다.** 이 리포의 작업 트리에 생기므로 끝나면 지운다.
- `make ship-preview`의 주소는 Vercel 로그인이 있어야 열린다. 에이전트는 로컬 빌드로 본다.

## 4. 결정 권한

- **디자인 값과 브랜딩은 원준님이 정한다**(허브 ADR-0003). 에이전트는 시안을 여럿 만들어 보여 주고, 고른 값은 DRAFT로 적는다.
- **`main` 병합과 production 배포는 소유자의 명시적 지시로만 한다**(허브 ADR-0015). "병합"이면 CI(`ci`)가 통과한 뒤 `gh pr merge <n> --squash --admin`으로 넣는다. 일반 병합은 ruleset `release-gate`가 거부하고, `--admin`은 팀 `release-owners`의 우회다. 우회 없는 `quality-gate`(CI)는 건너뛰지 못한다.
- **외부 서비스·런타임 의존성 추가, 공개 범위 변경은 승인 대상이다.** 허브 `change-flow.md`의 표를 본다.

## 5. production 배포

소유자가 "배포"라고 했을 때만, 병합된 `origin/main`의 깨끗한 worktree에서 한다.

```bash
export VERCEL_ORG_ID=$(jq -r .orgId ../dartwork-mpl-hub/.vercel/project.json)
export VERCEL_PROJECT_ID=$(jq -r .projectId ../dartwork-mpl-hub/.vercel/project.json)
UV_NO_CACHE=1 make ship-production      # 수 분 걸린다. 백그라운드로 돌린다
```

끝나면 `Aliased https://mpl.dartwork.io`를 확인하고, 바뀐 것이 라이브 HTML에 있는지 본다. 되돌리기는 허브 `operations.md`의 "되돌리기"다.

## 6. 두 리포를 함께 바꿀 때

- **순서는 한 방향이다.** 라이브러리 릴리스(소유자의 태그와 PyPI 승인, [change-flow.md](change-flow.md#릴리스)) → 허브 `make sync`로 새 판 고정 PR → 소유자 병합 → production. 허브는 PyPI에 없는 판을 production에 싣지 않는다.
- **갤러리 계약(manifest)은 두 리포가 함께 바꾼다.** 한쪽만 바꾸면 번들이 깨진다.
- **허브가 라이브러리에 바라는 것은 이 리포의 `[hub]` 이슈로 남긴다.** 허브 작업 중에 라이브러리 결함을 찾으면 허브에서 우회하지 말고 이슈를 쓴다. 이 세션이 라이브러리를 고칠 수 있어도, 그 수정은 이 리포의 PR과 릴리스를 거쳐 허브에 닿는다.
- **예제와 갤러리는 허브의 것이다.** 이 리포에 그림이나 예제를 두지 않는다([philosophy.md](philosophy.md)).

## 7. 자주 걸리는 것

- SvelteKit 3에서 개발 모드 판별은 `$app/env`다(`$app/environment`가 아니다).
- ESLint가 타입 단언(`as`)을 막는다. 밖에서 온 값은 `zod`로 parse한다.
- 색·크기는 `src/app.css`의 토큰만 쓴다. 컴포넌트에 raw 값을 쓰면 `lint:tokens`가 잡는다.
- 이미지는 git이 아니라 Vercel Blob에 있다. 렌더한 그림을 커밋하지 않는다.
- 셸은 zsh다. `set -- $var`로 단어를 나누지 못하고, macOS에는 `timeout`이 없다.
