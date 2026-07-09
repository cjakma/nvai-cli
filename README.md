# nvai-cli

`nvai-cli` is a Linux CLI coding assistant for NVIDIA AI / NIM OpenAI-compatible LLM APIs. It provides the global `nvai` command, manages daily-expiring NVIDIA API keys, and offers a Codex-like workflow with file reading, patch preview/approval, safe shell execution, streaming output, and a minimal full-screen TUI.

Repository: <https://github.com/cjakma/nvai-cli>

---

## English

### Overview

`nvai-cli` lets you use an NVIDIA-hosted LLM from a Linux terminal:

```bash
nvai
nvai "Analyze this repository"
nvai ask "Say OK"
nvai models
nvai doctor
nvai tui
```

Default model:

```text
z-ai/glm-5.2
```

Default NVIDIA OpenAI-compatible base URL:

```text
https://integrate.api.nvidia.com/v1
```

### Current capability summary

- Global `nvai` command from any directory.
- No manual virtualenv activation for normal use.
- Current-working-directory preserving wrapper, so project context is collected from the directory where the user runs `nvai`.
- Interactive REPL with `/help`, `/context`, `/exit`, `/quit`, Ctrl+C, and Ctrl+D.
- One-shot prompt mode with `nvai "prompt"` or `nvai ask "prompt"`.
- NVIDIA OpenAI-compatible API support:
  - `GET /models`
  - `POST /chat/completions`
  - streaming chat completions.
- Daily-expiring API-key lifecycle:
  - stores records in `~/.config/nvai/keys.toml`,
  - checks `expiredate` on every run,
  - prompts for a new key when missing or expired,
  - masks API-key input with `*`,
  - saves the key store with `0600` permissions.
- User-friendly setup input handling:
  - accepts `YYYY-MM-DD`, `YYYY-MM-DD HH:MM`, `YYYY-MM-DDTHH:MM:SS+09:00`, `YYYY/MM/DD`, and `MM/DD/YYYY`,
  - normalizes pasted URL shapes such as `<https://...|...>` and `host (https://...)`.
- Visible status while waiting for network/model calls.
- NVIDIA reasoning-model timeout handling:
  - catches socket/read timeouts as concise CLI errors instead of Python tracebacks,
  - keeps the REPL alive after provider errors,
  - exposes bounded `--max-tokens` / `--timeout` flags and `NVAI_MAX_TOKENS` / `NVAI_TIMEOUT` environment variables.
- Streaming model output.
- Streaming-time action-block detection.
- Codex-like action workflow:
  - model-proposed `read_file`,
  - model-proposed `patch_file` with unified diff preview,
  - batch preview/approval for multiple patches,
  - model-proposed `shell` with policy check and approval,
  - bounded model/action/tool-result loop.
- Shell command allow/deny policy:
  - `ask`, `strict`, and `off` modes,
  - optional `~/.config/nvai/policy.toml`.
- Minimal full-screen TUI via `nvai tui` using Python stdlib `curses`.
- GitHub `curl | bash` user-local installer and uninstaller.
- `nvai doctor` diagnostics.

### Install from GitHub

```bash
curl -fsSL https://raw.githubusercontent.com/cjakma/nvai-cli/main/install.sh | \
  NVAI_REPO_URL=https://github.com/cjakma/nvai-cli.git bash
```

Optional installer variables:

```bash
NVAI_REF=main
NVAI_INSTALL_DIR=~/.local/share/nvai-cli
NVAI_BIN_DIR=~/.local/bin
```

The installer:

1. clones/copies the app,
2. creates an isolated virtualenv,
3. installs `nvai-cli`,
4. creates `~/.local/bin/nvai`,
5. checks that `~/.local/bin` is reachable from the shell,
6. verifies `nvai --help`.

### Uninstall

Keep user config/API keys:

```bash
curl -fsSL https://raw.githubusercontent.com/cjakma/nvai-cli/main/uninstall.sh | bash
```

Remove install files and user config/API keys:

```bash
curl -fsSL https://raw.githubusercontent.com/cjakma/nvai-cli/main/uninstall.sh | \
  NVAI_REMOVE_CONFIG=1 bash
```

### Local development install

```bash
git clone https://github.com/cjakma/nvai-cli.git
cd nvai-cli
uv venv .venv --python 3.11
. .venv/bin/activate
uv pip install -e .
nvai --help
```

Fallback without `uv`:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

### First run and daily API-key refresh

```bash
nvai
```

If no valid key exists, or the active key is expired, `nvai` asks for:

```text
Name
Model
Base URL
API Key
Expire date
```

Example:

```text
Name [daily-glm-5-2-2026-07-08]: NVIDIABuild-Autogen-99
Model [nvidia/z-ai/glm-5.2]: z-ai/glm-5.2
Base URL [https://integrate.api.nvidia.com/v1]:
API Key: **********************************************************************
Expire date [2026-07-09T00:00:00+09:00]: 01/08/2027
```

`01/08/2027` is interpreted as `MM/DD/YYYY`, so it becomes `2027-01-08`.

### Codex-like action workflow

The model can propose local actions in a fenced JSON block:

```nvai-actions
[
  {"action":"read_file","path":"README.md","max_bytes":12000},
  {"action":"patch_file","path":"file.py","old":"exact old text","new":"replacement text"},
  {"action":"shell","command":"pytest -q","timeout":120}
]
```

Behavior:

- `read_file` executes immediately and sends file content back to the model.
- `patch_file` requires exact unique old text, prints a unified diff, and asks before applying.
- Multiple `patch_file` actions in one block are shown as one batch diff preview and can be approved together.
- `shell` prints the command, checks shell policy, asks for approval, enforces timeout, and captures combined stdout/stderr plus exit code.
- In non-interactive automation, patch/shell actions are denied unless `--yes` is supplied.
- Streaming output detects complete `nvai-actions` blocks while chunks arrive, but tools run only after the assistant answer completes so prompts do not interrupt streaming text.

### Shell command policy

Per-run override:

```bash
nvai ask --policy ask "Run safe checks if needed"
nvai ask --policy strict "Run only policy-approved commands if needed"
nvai ask --policy off "Disable shell policy checks for this trusted run"
```

Optional policy file:

```toml
# ~/.config/nvai/policy.toml
[shell]
mode = "strict" # ask | strict | off
allow = ["pytest", "uv run", "python -m pytest"]
deny = ["rm -rf /", "mkfs", "shutdown"]
```

The policy is a safety gate before approval. It is not a sandbox.

### Full-screen TUI

```bash
nvai tui
```

Controls:

```text
F2   send current message
F10  quit
Esc  quit
```

The current TUI is a lightweight `curses` chat surface. Patch/shell approvals are still best handled through `nvai ask` or the normal REPL until a dedicated TUI approval panel is added.

### Commands

```bash
nvai                         # interactive REPL
nvai "Analyze this repo"     # one-shot prompt with project context
nvai ask "Say OK"            # explicit one-shot ask
nvai ask --no-context "Say OK"
nvai ask --no-stream "Say OK"
nvai ask --yes "Inspect README and run safe commands if needed"
nvai ask --policy strict "Run tests if needed"
nvai ask --no-batch-patches "Approve proposed patches one by one"
nvai ask --no-stream-detect "Disable streaming action detection"
nvai ask --max-tokens 512 --timeout 240 "Use a longer NVIDIA wait budget"
nvai tui                     # minimal full-screen curses UI
nvai models                  # list NVIDIA models
nvai doctor                  # inspect installation and key status
nvai auth status
nvai auth add
nvai auth refresh
nvai auth list
nvai auth use <name>
```

Interactive REPL commands:

```text
/help      Show help
/context   Add current project context to the conversation
/exit      Quit
/quit      Quit
Ctrl+C     Quit and return to terminal
Ctrl+D     Quit and return to terminal
```

### Default paths

```text
Key store:       ~/.config/nvai/keys.toml
Policy file:     ~/.config/nvai/policy.toml
Installed app:   ~/.local/share/nvai-cli/app
Installed venv:  ~/.local/share/nvai-cli/.venv
Wrapper command: ~/.local/bin/nvai
```

### Diagnostics

```bash
nvai doctor
```

Example output:

```text
Executable: /home/ubuntu/.local/bin/nvai
Python: /home/ubuntu/.local/share/nvai-cli/.venv/bin/python
Python exists: OK
Current directory: /home/ubuntu/my-project
PATH contains ~/.local/bin: OK
Key store: /home/ubuntu/.config/nvai/keys.toml
Key store exists: OK
Active key: NVIDIABuild-Autogen-99
Model: z-ai/glm-5.2
Base URL: https://integrate.api.nvidia.com/v1
API Key: nvapi-****abcd
Expire date: 2027-01-08T00:00:00+09:00
Key status: valid
```

### Recent server update: NVIDIA timeout handling

The latest server-applied update addresses `TimeoutError: The read operation timed out` from NVIDIA GLM-5.2 chat completions.

What changed:

- Default chat completion output cap is now responsive: `DEFAULT_MAX_TOKENS=1024` instead of the earlier 8192-token default.
- Default NVIDIA request timeout is now `180s`.
- `TimeoutError` and `socket.timeout` are converted into `NvidiaApiError` messages, so users see a concise `error: NVIDIA API timed out...` message instead of a Python traceback.
- REPL mode catches provider errors, removes the failed user turn from conversation history, and continues prompting.
- `nvai ask` supports per-run tuning:

```bash
nvai ask --max-tokens 512 --timeout 240 "Use a longer NVIDIA wait budget"
```

Equivalent environment variables are also supported:

```bash
NVAI_MAX_TOKENS=512 NVAI_TIMEOUT=240 nvai
```

Server deployment notes for this host:

- Live command: `/home/ubuntu/.local/bin/nvai`
- Live project/venv target: `/home/ubuntu/agent-work/hermes/nvai-cli/.venv/bin/python`
- Applied commit: `57c5422 fix: handle NVIDIA API timeouts`
- Verified from caller directory: `/home/ubuntu/web-service`
- Verification command examples:

```bash
nvai ask --help
nvai doctor
uv run pytest -q
cd /home/ubuntu/web-service
nvai ask '안녕' --no-context --max-tokens 16 --timeout 5
```

The short-timeout smoke test intentionally times out, but now exits cleanly with a CLI error rather than a traceback.

### Current limitations / next work

- The TUI is currently a minimal chat surface, not yet a full patch/shell approval workbench.
- Provider-native tool-calling adapters are not implemented yet.
- Richer file search/list tools are not implemented yet.
- `.deb` packaging and apt repository distribution are not implemented yet.

---

## 한국어

### 개요

`nvai-cli`는 NVIDIA AI / NIM OpenAI 호환 LLM API를 Linux 터미널에서 사용하기 위한 coding assistant CLI입니다. 전역 `nvai` 명령을 제공하고, 매일 만료되는 NVIDIA API Key를 관리하며, 파일 읽기, patch preview/승인, 안전한 shell 실행, streaming 출력, 최소 full-screen TUI를 포함한 Codex-like workflow를 제공합니다.

저장소: <https://github.com/cjakma/nvai-cli>

### 기본 사용

```bash
nvai
nvai "이 저장소 분석해줘"
nvai ask "Say OK"
nvai models
nvai doctor
nvai tui
```

기본 모델:

```text
z-ai/glm-5.2
```

기본 NVIDIA OpenAI 호환 API 주소:

```text
https://integrate.api.nvidia.com/v1
```

### 현재 기능 요약

- 어느 디렉터리에서든 실행 가능한 전역 `nvai` 명령.
- 일반 사용 시 Python virtualenv 수동 activate/deactivate 불필요.
- wrapper가 현재 작업 디렉터리를 보존하므로, 사용자가 `nvai`를 실행한 프로젝트 기준으로 context 수집.
- `/help`, `/context`, `/exit`, `/quit`, Ctrl+C, Ctrl+D를 지원하는 인터랙티브 REPL.
- `nvai "prompt"` 또는 `nvai ask "prompt"` 단발 요청.
- NVIDIA OpenAI 호환 API 지원:
  - `GET /models`,
  - `POST /chat/completions`,
  - streaming chat completions.
- 매일 만료되는 API Key 관리:
  - `~/.config/nvai/keys.toml`에 key record 저장,
  - 실행할 때마다 `expiredate` 확인,
  - key가 없거나 만료되면 새 key 입력,
  - API Key 입력 시 `*`로 masking,
  - key store 권한 `0600` 적용.
- 사용자 입력 보정:
  - `YYYY-MM-DD`, `YYYY-MM-DD HH:MM`, `YYYY-MM-DDTHH:MM:SS+09:00`, `YYYY/MM/DD`, `MM/DD/YYYY` 지원,
  - `<https://...|...>`, `host (https://...)` 같은 붙여넣기 URL 정규화.
- 네트워크/모델 응답 대기 중 상태 표시.
- NVIDIA reasoning model timeout 처리:
  - socket/read timeout을 Python traceback 대신 간단한 CLI error로 표시,
  - provider error 후에도 REPL 유지,
  - 제한 검증이 있는 `--max-tokens` / `--timeout` flag와 `NVAI_MAX_TOKENS` / `NVAI_TIMEOUT` 환경변수 제공.
- streaming model output.
- streaming 중 action block 감지.
- Codex-like action workflow:
  - 모델이 제안하는 `read_file`,
  - unified diff preview를 포함하는 `patch_file`,
  - 여러 patch batch preview/승인,
  - policy 검사와 승인을 거치는 `shell`,
  - 제한된 model/action/tool-result loop.
- shell command allow/deny policy:
  - `ask`, `strict`, `off` 모드,
  - 선택적 `~/.config/nvai/policy.toml`.
- Python 표준 라이브러리 `curses` 기반 최소 full-screen TUI: `nvai tui`.
- GitHub `curl | bash` user-local installer/uninstaller.
- `nvai doctor` 진단 명령.

### GitHub 설치

```bash
curl -fsSL https://raw.githubusercontent.com/cjakma/nvai-cli/main/install.sh | \
  NVAI_REPO_URL=https://github.com/cjakma/nvai-cli.git bash
```

설치 옵션:

```bash
NVAI_REF=main
NVAI_INSTALL_DIR=~/.local/share/nvai-cli
NVAI_BIN_DIR=~/.local/bin
```

설치 스크립트는 다음을 수행합니다.

1. 앱 clone/copy,
2. 독립 virtualenv 생성,
3. `nvai-cli` 설치,
4. `~/.local/bin/nvai` 생성,
5. shell에서 `~/.local/bin` 접근 가능 여부 확인,
6. `nvai --help` 검증.

### 삭제

사용자 설정/API Key는 보존하고 설치 파일만 삭제:

```bash
curl -fsSL https://raw.githubusercontent.com/cjakma/nvai-cli/main/uninstall.sh | bash
```

설치 파일과 사용자 설정/API Key까지 삭제:

```bash
curl -fsSL https://raw.githubusercontent.com/cjakma/nvai-cli/main/uninstall.sh | \
  NVAI_REMOVE_CONFIG=1 bash
```

### 로컬 개발 설치

```bash
git clone https://github.com/cjakma/nvai-cli.git
cd nvai-cli
uv venv .venv --python 3.11
. .venv/bin/activate
uv pip install -e .
nvai --help
```

`uv`가 없다면:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

### 최초 실행과 매일 API Key 갱신

```bash
nvai
```

유효한 key가 없거나 active key가 만료되면 다음 정보를 입력받습니다.

```text
Name
Model
Base URL
API Key
Expire date
```

예시:

```text
Name [daily-glm-5-2-2026-07-08]: NVIDIABuild-Autogen-99
Model [nvidia/z-ai/glm-5.2]: z-ai/glm-5.2
Base URL [https://integrate.api.nvidia.com/v1]:
API Key: **********************************************************************
Expire date [2026-07-09T00:00:00+09:00]: 01/08/2027
```

`01/08/2027`은 `MM/DD/YYYY`로 해석되어 `2027-01-08`이 됩니다.

### Codex-like action workflow

모델은 fenced JSON block으로 local action을 제안할 수 있습니다.

```nvai-actions
[
  {"action":"read_file","path":"README.md","max_bytes":12000},
  {"action":"patch_file","path":"file.py","old":"exact old text","new":"replacement text"},
  {"action":"shell","command":"pytest -q","timeout":120}
]
```

동작:

- `read_file`은 즉시 실행되고 파일 내용이 모델에게 다시 전달됩니다.
- `patch_file`은 exact unique old text를 요구하며, unified diff를 출력한 뒤 승인 후 적용합니다.
- 한 block 안에 여러 `patch_file`이 있으면 batch diff preview를 보여주고 한 번에 승인할 수 있습니다.
- `shell`은 command를 출력하고, shell policy를 검사하고, 승인받고, timeout을 적용하며, stdout/stderr와 exit code를 수집합니다.
- non-interactive 자동화에서는 `--yes`가 없으면 patch/shell action이 거부됩니다.
- streaming 중 완성된 `nvai-actions` block을 감지하지만, 실제 tool 실행은 assistant 응답이 끝난 뒤 진행해 prompt가 streaming 출력을 방해하지 않게 합니다.

### Shell command policy

실행별 override:

```bash
nvai ask --policy ask "필요하면 안전한 검사를 실행해줘"
nvai ask --policy strict "필요하면 policy가 허용한 명령만 실행해줘"
nvai ask --policy off "신뢰하는 실행에서 shell policy 검사를 끄기"
```

선택적 policy 파일:

```toml
# ~/.config/nvai/policy.toml
[shell]
mode = "strict" # ask | strict | off
allow = ["pytest", "uv run", "python -m pytest"]
deny = ["rm -rf /", "mkfs", "shutdown"]
```

policy는 approval 전 safety gate이며 sandbox는 아닙니다.

### Full-screen TUI

```bash
nvai tui
```

조작:

```text
F2   현재 메시지 전송
F10  종료
Esc  종료
```

현재 TUI는 가벼운 `curses` chat surface입니다. patch/shell 승인은 dedicated TUI approval panel이 추가되기 전까지 `nvai ask` 또는 일반 REPL에서 처리하는 것이 적합합니다.

### 명령어

```bash
nvai                         # 인터랙티브 REPL
nvai "이 repo 분석해줘"       # 현재 디렉터리 context 포함 단발 요청
nvai ask "Say OK"            # 명시적 단발 요청
nvai ask --no-context "Say OK"
nvai ask --no-stream "Say OK"
nvai ask --yes "README 확인 후 필요한 안전한 명령을 실행해줘"
nvai ask --policy strict "필요하면 테스트를 실행해줘"
nvai ask --no-batch-patches "patch는 하나씩 승인할게"
nvai ask --no-stream-detect "streaming action 감지를 끄기"
nvai ask --max-tokens 512 --timeout 240 "NVIDIA 응답 대기 시간을 더 길게 사용"
nvai tui                     # 최소 full-screen curses UI
nvai models                  # NVIDIA 모델 목록
nvai doctor                  # 설치 및 key 상태 진단
nvai auth status
nvai auth add
nvai auth refresh
nvai auth list
nvai auth use <name>
```

REPL 내부 명령:

```text
/help      도움말 출력
/context   현재 프로젝트 context를 대화에 추가
/exit      종료
/quit      종료
Ctrl+C     종료 후 터미널로 복귀
Ctrl+D     종료 후 터미널로 복귀
```

### 기본 경로

```text
Key 저장:       ~/.config/nvai/keys.toml
Policy 파일:    ~/.config/nvai/policy.toml
설치 앱:        ~/.local/share/nvai-cli/app
설치 venv:      ~/.local/share/nvai-cli/.venv
실행 wrapper:   ~/.local/bin/nvai
```

### 진단

```bash
nvai doctor
```

예시 출력:

```text
Executable: /home/ubuntu/.local/bin/nvai
Python: /home/ubuntu/.local/share/nvai-cli/.venv/bin/python
Python exists: OK
Current directory: /home/ubuntu/my-project
PATH contains ~/.local/bin: OK
Key store: /home/ubuntu/.config/nvai/keys.toml
Key store exists: OK
Active key: NVIDIABuild-Autogen-99
Model: z-ai/glm-5.2
Base URL: https://integrate.api.nvidia.com/v1
API Key: nvapi-****abcd
Expire date: 2027-01-08T00:00:00+09:00
Key status: valid
```

### 최근 서버 반영 내용: NVIDIA timeout 처리

최근 서버 반영 버전은 NVIDIA GLM-5.2 chat completion 호출 중 발생하던 `TimeoutError: The read operation timed out` 문제를 개선합니다.

변경 내용:

- 기본 chat completion 출력 cap을 기존 8192 token에서 `DEFAULT_MAX_TOKENS=1024` 낮춰 기본 응답성을 개선했습니다.
- 기본 NVIDIA request timeout을 `180s`로 조정했습니다.
- `TimeoutError`, `socket.timeout`을 `NvidiaApiError`로 변환하여 Python traceback 대신 `error: NVIDIA API timed out...` 형태의 간단한 CLI error를 출력합니다.
- REPL mode에서 provider error가 발생해도 실패한 user turn을 history에서 제거하고 prompt를 계속 유지합니다.
- `nvai ask`에서 실행별 조정이 가능합니다.

```bash
nvai ask --max-tokens 512 --timeout 240 "NVIDIA 응답 대기 시간을 더 길게 사용"
```

동일한 설정은 환경변수로도 지정할 수 있습니다.

```bash
NVAI_MAX_TOKENS=512 NVAI_TIMEOUT=240 nvai
```

이 서버의 반영 정보:

- 실제 실행 명령: `/home/ubuntu/.local/bin/nvai`
- 실제 project/venv target: `/home/ubuntu/agent-work/hermes/nvai-cli/.venv/bin/python`
- 반영 commit: `57c5422 fix: handle NVIDIA API timeouts`
- caller directory 검증 위치: `/home/ubuntu/web-service`
- 검증 명령 예시:

```bash
nvai ask --help
nvai doctor
uv run pytest -q
cd /home/ubuntu/web-service
nvai ask '안녕' --no-context --max-tokens 16 --timeout 5
```

짧은 timeout smoke test는 의도적으로 timeout을 발생시키지만, 이제 traceback이 아니라 CLI error로 정상 처리됩니다.

### 현재 한계 / 다음 작업

- TUI는 아직 최소 chat surface이며, 완전한 patch/shell approval workbench는 아닙니다.
- provider-native tool-calling adapter는 아직 구현하지 않았습니다.
- 더 정교한 file search/list tool은 아직 구현하지 않았습니다.
- `.deb` packaging 및 apt repository 배포는 아직 구현하지 않았습니다.
