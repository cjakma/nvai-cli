# nvai-cli Architecture / Architect

Repository: <https://github.com/cjakma/nvai-cli>

This document summarizes the architecture, implemented design, core logic, safety model, and planned extension points for `nvai-cli`.

---

## English

### 1. Purpose

`nvai-cli` is a Linux terminal coding assistant for NVIDIA AI / NIM OpenAI-compatible LLM APIs. It targets a workflow where NVIDIA API keys may expire daily, so the user must frequently enter a refreshed key.

The project provides a Codex-like command:

```bash
nvai
```

The process starts on demand, uses the caller's current working directory as project context, and exits back to the shell when the user quits.

### 2. Design goals

- Provide a global `nvai` command runnable from any project directory.
- Avoid manual virtualenv activation for normal use.
- Preserve the caller's current working directory.
- Keep API keys in user-local config, never in the project repository.
- Support daily-expiring API keys with a smooth prompt/refresh flow.
- Use the NVIDIA OpenAI-compatible API surface with minimal dependencies.
- Stream model output and show visible progress for long calls.
- Provide a portable Codex-like action protocol before depending on provider-native tool calling.
- Require preview and approval for writes and shell commands.
- Keep the first TUI implementation lightweight and stdlib-based.

### 3. Current implemented scope

Implemented through v0.0.3:

- `nvai` CLI entrypoint.
- REPL and one-shot prompt modes.
- NVIDIA OpenAI-compatible HTTP client.
- `/models` and `/chat/completions` integration.
- Streaming model output.
- Daily-expiring API-key storage and refresh flow.
- Masked API-key prompt with `*` feedback.
- Expiry date parsing for common ISO/slash formats.
- Pasted URL normalization for Slack/Markdown/browser shapes.
- User-local installer and uninstaller.
- `nvai doctor` diagnostics.
- Codex-like action loop:
  - `read_file`,
  - `patch_file`,
  - `shell`,
  - tool-result feedback to the model,
  - bounded rounds.
- Unified diff preview before patch application.
- Batch preview/approval for multiple patches.
- Shell command policy and approval flow.
- Streaming-time detection of complete action blocks.
- Minimal `curses` full-screen TUI via `nvai tui`.
- Test coverage for CLI routing, prompts, key store, date parsing, URL normalization, doctor output, action tools, batch patching, shell policy, streaming action detection, and TUI rendering.

Not implemented yet:

- Provider-native tool-calling adapters.
- Richer file search/list tools.
- TUI approval panel for patch/shell actions.
- GitHub Release artifacts.
- `.deb` packaging and apt repository distribution.

### 4. Runtime model

`nvai-cli` is not a daemon.

```text
user runs nvai
  -> shell resolves ~/.local/bin/nvai or editable install entrypoint
  -> Python runs nvai.cli
  -> ensure_valid_api_key()
  -> command dispatch: REPL / ask / models / doctor / auth / tui
  -> process exits on /exit, /quit, Ctrl+C, Ctrl+D, F10, or Esc depending on mode
  -> terminal prompt returns
```

### 5. Install model

User-local installation layout:

```text
~/.local/share/nvai-cli/
  app/                  # copied/cloned source tree
  .venv/                # isolated Python environment

~/.local/bin/nvai        # wrapper script
~/.config/nvai/keys.toml # user key store
~/.config/nvai/policy.toml # optional shell policy
```

The wrapper intentionally does not `cd` into the application directory. This preserves the user's project directory for context collection and tool execution.

### 6. Source layout

```text
src/nvai/
  __init__.py        # package metadata
  agent.py           # bounded model/action/tool-result loop
  auth_flow.py       # valid active API-key acquisition
  cli.py             # argparse entrypoint, REPL, one-shot commands, TUI command
  context.py         # lightweight project context collection
  datetime_utils.py  # expiry-date parsing/formatting
  doctor.py          # install/runtime diagnostics
  key_prompt.py      # setup prompts, masked input, URL normalization
  key_store.py       # TOML key-store load/save and 0600 permissions
  models.py          # dataclasses and defaults
  nvidia_client.py   # NVIDIA OpenAI-compatible HTTP client
  policy.py          # shell command allow/deny policy
  tools.py           # read_file, patch_file, shell, approvals, batch execution
  tui.py             # minimal curses full-screen UI
  ui.py              # status spinner / non-TTY status lines

tests/
  test_agent.py
  test_cli.py
  test_datetime_utils.py
  test_doctor.py
  test_key_prompt.py
  test_key_store.py
  test_tools.py
  test_tui.py
  test_ui.py

install.sh
uninstall.sh
scripts/install-user.sh
scripts/uninstall-user.sh
```

### 7. API-key lifecycle

Every command that needs NVIDIA API access calls:

```python
ensure_valid_api_key()
```

High-level flow:

```text
load ~/.config/nvai/keys.toml
  -> read active_key
  -> if active key is missing: prompt for a new key
  -> if active key is expired: prompt for a new key
  -> validate with /models unless NVAI_SKIP_VALIDATE=1
  -> save key store with 0600 permissions
  -> return ApiKeyRecord
```

Key record fields:

```text
name
model
api_key
expiredate
base_url
created_at
last_used_at
```

### 8. Prompt and input design

The setup prompt handles common user input issues:

- API key input is masked with visible `*` feedback.
- Invalid ordinary fields re-prompt instead of crashing.
- Expiry dates support:
  - `YYYY-MM-DD`,
  - `YYYY-MM-DD HH:MM`,
  - `YYYY-MM-DDTHH:MM:SS+09:00`,
  - `YYYY/MM/DD`,
  - `MM/DD/YYYY`.
- Ambiguous slash dates such as `01/08/2027` are interpreted as `MM/DD/YYYY`.
- Base URLs pasted from Slack/Markdown/browser text are normalized:
  - `integrate.api.nvidia.com/v1`,
  - `<https://integrate.api.nvidia.com/v1|integrate.api.nvidia.com/v1>`,
  - `integrate.api.nvidia.com/v1 (https://integrate.api.nvidia.com/v1)`.

### 9. NVIDIA client

`src/nvai/nvidia_client.py` uses Python stdlib `urllib` to avoid mandatory runtime dependencies.

Supported endpoints:

```text
GET  /models
POST /chat/completions
```

Chat completion modes:

```text
stream=false -> full response via chat()
stream=true  -> SSE chunks via chat_stream()
```

Common HTTP handling:

```text
401 -> rejected/expired key guidance
403 -> model/key permission guidance
404 -> endpoint/model guidance
429 -> rate-limit guidance
other -> truncated response details
```

### 10. CLI command dispatch

Primary commands:

```text
nvai                         -> REPL
nvai "prompt"                -> one-shot prompt
nvai ask "prompt"            -> explicit one-shot prompt
nvai ask --policy strict      -> override shell policy
nvai ask --no-batch-patches   -> approve patches one by one
nvai ask --no-stream-detect   -> disable streaming action detection
nvai tui                     -> minimal full-screen curses UI
nvai models                  -> list NVIDIA models
nvai doctor                  -> diagnostics
nvai auth status/add/refresh/list/use
```

REPL commands:

```text
/help
/context
/exit
/quit
Ctrl+C
Ctrl+D
```

### 11. Project context model

`context.py` collects lightweight project context for one-shot asks. The wrapper preserves the caller's working directory, so context and tool execution target the user's actual project rather than the `nvai-cli` installation directory.

### 12. Codex-like action protocol

The current action protocol is provider-neutral fenced JSON:

````text
```nvai-actions
[
  {"action":"read_file","path":"README.md","max_bytes":12000},
  {"action":"patch_file","path":"file.py","old":"exact old text","new":"replacement text"},
  {"action":"shell","command":"pytest -q","timeout":120}
]
```
````

Action loop:

```text
model response
  -> parse explicit fenced JSON action blocks
  -> execute read-only tools immediately
  -> preview and approve patches/shell commands
  -> format tool results
  -> append tool results to conversation
  -> let the model continue
  -> stop after a bounded max round count
```

Rationale:

- Works across OpenAI-compatible endpoints even when native tool calling is uncertain.
- Keeps local side effects controlled by the CLI, not by the model.
- Makes previews and tool results auditable.

### 13. Patch design

`patch_file` uses exact text replacement:

```text
path
old
new
```

Safety rules:

- Target file must exist.
- `old` must appear exactly once.
- A unified diff is printed before writing.
- User approval is required unless `--yes` is supplied.
- Multiple valid patches in the same action batch can be approved together.
- If a batch contains invalid patches, invalid results are reported and partial silent application is avoided.

### 14. Shell command policy and execution

`shell` actions run through policy before approval.

Policy modes:

```text
ask    -> deny known-dangerous commands, then ask approval
strict -> allow only configured/known-safe first words/prefixes, then ask approval
off    -> skip policy checks, but approval still applies unless --yes is used
```

Execution rules:

- Show command preview.
- Check policy.
- Ask approval unless `--yes` is supplied.
- Run with timeout.
- Capture combined stdout/stderr.
- Return exit code and truncated output to the model.

Important: policy is a safety gate, not a sandbox.

### 15. Streaming action detection

During streaming, the agent accumulates chunks and checks whether a complete fenced `nvai-actions` block is visible. When detected, it prints a notice for the user.

Tools are still executed only after the assistant answer is complete. This avoids mixing approval prompts into streaming output and keeps terminal UX stable.

### 16. Full-screen TUI design

`src/nvai/tui.py` implements a minimal full-screen UI using stdlib `curses`.

Controls:

```text
F2   send current input
F10  quit
Esc  quit
```

Design boundaries:

- TUI currently provides a chat surface.
- It intentionally avoids complex patch/shell approval UI in the first implementation.
- Future work can add a dedicated approval panel and diff viewer.

### 17. Status/progress UI

`ui.py` provides visible progress around slower operations.

TTY example:

```text
⠋ Waiting for NVIDIA model response (z-ai/glm-5.2)... 1.2s
```

Non-TTY/log example:

```text
[status] Waiting for NVIDIA model response (z-ai/glm-5.2)...
[ok] Waiting for NVIDIA model response (z-ai/glm-5.2) (2.4s)
```

### 18. Verification strategy

Current verification commands:

```bash
uv run --with pytest -- python -m pytest -q -p no:cacheprovider
python3 -m compileall -q src tests
bash -n install.sh uninstall.sh scripts/install-user.sh scripts/uninstall-user.sh
nvai --help
nvai ask --help
```

Covered test areas:

- CLI parsing and routing.
- REPL help/exit behavior.
- Date parsing.
- Key-store persistence and permissions.
- Prompt masking and URL normalization.
- Doctor output.
- Action parsing.
- File reading.
- Patch preview/application.
- Batch patch approval.
- Shell policy denial.
- Streaming action detection.
- TUI pure rendering.

### 19. Extension plan

Recommended order:

1. Richer file search/list tools:
   - `list_files`,
   - `tree`,
   - `search_files` by name,
   - `search_files` by content,
   - ignore rules and size caps.
2. TUI approval panel:
   - diff viewer,
   - patch batch approval,
   - command preview/approval.
3. Provider-native tool-calling adapters:
   - keep fenced JSON as fallback,
   - add OpenAI-style or NVIDIA/GLM-specific adapter only after endpoint behavior is verified.
4. Packaging:
   - GitHub Release artifacts,
   - `.deb`,
   - apt repository.

---

## 한국어

### 1. 목적

`nvai-cli`는 NVIDIA AI / NIM OpenAI 호환 LLM API를 Linux 터미널에서 사용하기 위한 coding assistant CLI입니다. NVIDIA API Key가 매일 만료될 수 있고, 사용자가 자주 새 key를 입력해야 하는 workflow를 기준으로 설계되었습니다.

프로젝트는 다음 Codex-like 명령을 제공합니다.

```bash
nvai
```

프로세스는 필요할 때 시작되고, 사용자의 현재 작업 디렉터리를 project context로 사용하며, 종료 시 shell로 복귀합니다.

### 2. 설계 목표

- 어느 프로젝트 디렉터리에서든 전역 `nvai` 명령 실행.
- 일반 사용 시 virtualenv 수동 activate 불필요.
- 사용자의 현재 작업 디렉터리 보존.
- API Key는 사용자 로컬 설정에 저장하고 repository에는 저장하지 않음.
- 매일 만료되는 API Key를 자연스럽게 prompt/refresh.
- NVIDIA OpenAI 호환 API surface 사용 및 의존성 최소화.
- 모델 출력 streaming 및 긴 호출의 진행 상태 표시.
- provider-native tool calling에 의존하기 전, 이식 가능한 Codex-like action protocol 제공.
- 파일 수정과 shell command에는 preview와 승인 적용.
- 첫 TUI 구현은 가볍고 stdlib 기반으로 유지.

### 3. 현재 구현 범위

v0.0.3까지 구현됨:

- `nvai` CLI entrypoint.
- REPL 및 단발 prompt 모드.
- NVIDIA OpenAI 호환 HTTP client.
- `/models`, `/chat/completions` 연동.
- streaming model output.
- 매일 만료되는 API Key 저장 및 refresh flow.
- `*` 표시가 있는 API Key prompt.
- 주요 ISO/slash 날짜 형식 parsing.
- Slack/Markdown/browser에서 붙여넣은 URL 정규화.
- user-local installer/uninstaller.
- `nvai doctor` 진단.
- Codex-like action loop:
  - `read_file`,
  - `patch_file`,
  - `shell`,
  - tool result를 모델에게 재전달,
  - bounded rounds.
- patch 적용 전 unified diff preview.
- 여러 patch batch preview/approval.
- shell command policy 및 승인 flow.
- streaming 중 complete action block 감지.
- `nvai tui` 최소 `curses` full-screen TUI.
- CLI routing, prompt, key store, date parsing, URL normalization, doctor, action tools, batch patching, shell policy, streaming action detection, TUI rendering 테스트.

아직 미구현:

- provider-native tool-calling adapter.
- 더 정교한 file search/list tool.
- patch/shell action을 위한 TUI approval panel.
- GitHub Release artifact.
- `.deb` packaging 및 apt repository 배포.

### 4. 실행 모델

`nvai-cli`는 daemon이 아닙니다.

```text
사용자가 nvai 실행
  -> shell이 ~/.local/bin/nvai 또는 editable install entrypoint 확인
  -> Python이 nvai.cli 실행
  -> ensure_valid_api_key()
  -> 명령 dispatch: REPL / ask / models / doctor / auth / tui
  -> mode에 따라 /exit, /quit, Ctrl+C, Ctrl+D, F10, Esc 등으로 종료
  -> terminal prompt 복귀
```

### 5. 설치 모델

user-local 설치 구조:

```text
~/.local/share/nvai-cli/
  app/                  # 복사/clone된 source tree
  .venv/                # 독립 Python 환경

~/.local/bin/nvai        # wrapper script
~/.config/nvai/keys.toml # 사용자 key store
~/.config/nvai/policy.toml # 선택적 shell policy
```

wrapper는 앱 디렉터리로 `cd`하지 않습니다. 사용자가 실행한 프로젝트 디렉터리를 context 수집과 tool 실행 기준으로 유지하기 위함입니다.

### 6. 소스 구조

```text
src/nvai/
  __init__.py        # package metadata
  agent.py           # bounded model/action/tool-result loop
  auth_flow.py       # 유효한 active API Key 확보
  cli.py             # argparse entrypoint, REPL, 단발 명령, TUI 명령
  context.py         # 가벼운 프로젝트 context 수집
  datetime_utils.py  # 만료일 parsing/formatting
  doctor.py          # 설치/실행 진단
  key_prompt.py      # setup prompt, masked input, URL 정규화
  key_store.py       # TOML key-store load/save 및 0600 권한
  models.py          # dataclass 및 기본값
  nvidia_client.py   # NVIDIA OpenAI 호환 HTTP client
  policy.py          # shell command allow/deny policy
  tools.py           # read_file, patch_file, shell, 승인, batch 실행
  tui.py             # 최소 curses full-screen UI
  ui.py              # status spinner / non-TTY status line

tests/
  test_agent.py
  test_cli.py
  test_datetime_utils.py
  test_doctor.py
  test_key_prompt.py
  test_key_store.py
  test_tools.py
  test_tui.py
  test_ui.py

install.sh
uninstall.sh
scripts/install-user.sh
scripts/uninstall-user.sh
```

### 7. API Key 생명주기

NVIDIA API 접근이 필요한 명령은 다음을 호출합니다.

```python
ensure_valid_api_key()
```

상위 flow:

```text
~/.config/nvai/keys.toml load
  -> active_key 확인
  -> active key가 없으면 새 key 입력
  -> active key가 만료되었으면 새 key 입력
  -> NVAI_SKIP_VALIDATE=1이 아니면 /models로 검증
  -> key store를 0600 권한으로 저장
  -> ApiKeyRecord 반환
```

Key record 필드:

```text
name
model
api_key
expiredate
base_url
created_at
last_used_at
```

### 8. Prompt와 입력 설계

setup prompt는 일반적인 사용자 입력 문제를 처리합니다.

- API Key 입력은 `*`로 masking하면서 입력 진행이 보입니다.
- 일반 입력 오류는 traceback 대신 재입력하도록 합니다.
- 만료일 지원 형식:
  - `YYYY-MM-DD`,
  - `YYYY-MM-DD HH:MM`,
  - `YYYY-MM-DDTHH:MM:SS+09:00`,
  - `YYYY/MM/DD`,
  - `MM/DD/YYYY`.
- `01/08/2027` 같은 slash 날짜는 `MM/DD/YYYY`로 해석합니다.
- Slack/Markdown/browser에서 붙여넣은 Base URL을 정규화합니다.

### 9. NVIDIA client

`src/nvai/nvidia_client.py`는 필수 runtime dependency를 줄이기 위해 Python stdlib `urllib`를 사용합니다.

지원 endpoint:

```text
GET  /models
POST /chat/completions
```

Chat completion mode:

```text
stream=false -> chat()로 full response
stream=true  -> chat_stream()으로 SSE chunk
```

주요 HTTP 처리:

```text
401 -> key 거부/만료 안내
403 -> model/key 권한 안내
404 -> endpoint/model 안내
429 -> rate-limit 안내
기타 -> 잘라낸 응답 detail 제공
```

### 10. CLI command dispatch

주요 명령:

```text
nvai                         -> REPL
nvai "prompt"                -> 단발 prompt
nvai ask "prompt"            -> 명시적 단발 prompt
nvai ask --policy strict      -> shell policy override
nvai ask --no-batch-patches   -> patch를 하나씩 승인
nvai ask --no-stream-detect   -> streaming action 감지 비활성화
nvai tui                     -> 최소 full-screen curses UI
nvai models                  -> NVIDIA 모델 목록
nvai doctor                  -> 진단
nvai auth status/add/refresh/list/use
```

REPL 명령:

```text
/help
/context
/exit
/quit
Ctrl+C
Ctrl+D
```

### 11. Project context 모델

`context.py`는 단발 요청에 사용할 가벼운 project context를 수집합니다. wrapper가 현재 작업 디렉터리를 보존하므로, context와 tool execution은 `nvai-cli` 설치 디렉터리가 아니라 사용자의 실제 project를 대상으로 합니다.

### 12. Codex-like action protocol

현재 action protocol은 provider-neutral fenced JSON입니다.

````text
```nvai-actions
[
  {"action":"read_file","path":"README.md","max_bytes":12000},
  {"action":"patch_file","path":"file.py","old":"exact old text","new":"replacement text"},
  {"action":"shell","command":"pytest -q","timeout":120}
]
```
````

Action loop:

```text
model response
  -> 명시적 fenced JSON action block parse
  -> read-only tool은 즉시 실행
  -> patch/shell command preview 및 승인
  -> tool result format
  -> conversation에 tool result 추가
  -> 모델이 이어서 답변
  -> 제한된 max round 이후 중단
```

설계 이유:

- native tool calling이 불확실한 OpenAI 호환 endpoint에서도 동작합니다.
- local side effect를 모델이 아니라 CLI가 통제합니다.
- preview와 tool result를 사용자가 확인할 수 있습니다.

### 13. Patch 설계

`patch_file`은 exact text replacement를 사용합니다.

```text
path
old
new
```

안전 규칙:

- 대상 파일이 존재해야 합니다.
- `old`는 정확히 한 번만 등장해야 합니다.
- 쓰기 전에 unified diff를 출력합니다.
- `--yes`가 없으면 사용자 승인이 필요합니다.
- 같은 action batch 안의 여러 valid patch는 한 번에 승인할 수 있습니다.
- batch에 invalid patch가 있으면 결과를 보고하고 조용한 partial apply를 피합니다.

### 14. Shell command policy와 실행

`shell` action은 승인 전에 policy를 통과해야 합니다.

Policy mode:

```text
ask    -> 알려진 위험 명령 차단 후 승인 요청
strict -> 설정/기본 safe first word/prefix만 승인 요청
off    -> policy 검사는 생략하지만 --yes가 없으면 승인은 유지
```

실행 규칙:

- command preview 출력.
- policy 검사.
- `--yes`가 없으면 승인 요청.
- timeout 적용.
- stdout/stderr 통합 capture.
- exit code와 잘라낸 output을 모델에게 반환.

중요: policy는 sandbox가 아니라 safety gate입니다.

### 15. Streaming action detection

streaming 중 agent는 chunk를 누적하고 complete fenced `nvai-actions` block이 보이는지 검사합니다. 감지되면 사용자에게 notice를 출력합니다.

tool 실행은 assistant 응답이 끝난 뒤에만 진행합니다. approval prompt가 streaming output 중간에 끼어드는 것을 막기 위한 설계입니다.

### 16. Full-screen TUI 설계

`src/nvai/tui.py`는 stdlib `curses` 기반 최소 full-screen UI입니다.

조작:

```text
F2   현재 입력 전송
F10  종료
Esc  종료
```

설계 경계:

- 현재 TUI는 chat surface에 집중합니다.
- 첫 구현에서는 복잡한 patch/shell approval UI를 넣지 않았습니다.
- 향후 dedicated approval panel과 diff viewer를 추가할 수 있습니다.

### 17. Status/progress UI

`ui.py`는 느린 작업 주변에 진행 상태를 표시합니다.

TTY 예시:

```text
⠋ Waiting for NVIDIA model response (z-ai/glm-5.2)... 1.2s
```

non-TTY/log 예시:

```text
[status] Waiting for NVIDIA model response (z-ai/glm-5.2)...
[ok] Waiting for NVIDIA model response (z-ai/glm-5.2) (2.4s)
```

### 18. 검증 전략

현재 검증 명령:

```bash
uv run --with pytest -- python -m pytest -q -p no:cacheprovider
python3 -m compileall -q src tests
bash -n install.sh uninstall.sh scripts/install-user.sh scripts/uninstall-user.sh
nvai --help
nvai ask --help
```

테스트 범위:

- CLI parsing/routing.
- REPL help/exit.
- 날짜 parsing.
- key-store 저장 및 권한.
- prompt masking 및 URL normalization.
- doctor output.
- action parsing.
- file reading.
- patch preview/application.
- batch patch approval.
- shell policy denial.
- streaming action detection.
- TUI pure rendering.

### 19. 확장 계획

추천 순서:

1. 더 정교한 file search/list tool:
   - `list_files`,
   - `tree`,
   - 파일명 기반 `search_files`,
   - 내용 기반 `search_files`,
   - ignore rule과 size cap.
2. TUI approval panel:
   - diff viewer,
   - patch batch approval,
   - command preview/approval.
3. Provider-native tool-calling adapter:
   - fenced JSON을 fallback으로 유지,
   - endpoint 동작 검증 후 OpenAI-style 또는 NVIDIA/GLM-specific adapter 추가.
4. Packaging:
   - GitHub Release artifact,
   - `.deb`,
   - apt repository.
