# nvai-cli Architecture

Repository: <https://github.com/cjakma/nvai-cli>

---

## English

### 1. Purpose

`nvai-cli` is a Linux terminal assistant that connects to NVIDIA AI / NIM OpenAI-compatible LLM APIs. It was designed for a workflow where the NVIDIA API key may expire daily and must be refreshed by the user.

The project aims to provide a small Codex/Claude-like CLI entrypoint:

```bash
nvai
```

It starts an interactive REPL, manages API-key rotation, calls the NVIDIA API, and returns control to the terminal when the user exits.

### 2. Design goals

- Run from any directory with a global `nvai` command.
- Avoid manual virtualenv activation/deactivation for normal use.
- Preserve the caller's current working directory so project context comes from the user's actual project, not the `nvai-cli` install directory.
- Support daily-expiring NVIDIA API keys.
- Keep key storage local to the user and outside the project repository.
- Provide visible progress while waiting for network/model responses.
- Provide a GitHub `curl | bash` installer before introducing `.deb` or apt repository packaging.
- Keep dependencies minimal and use Python standard library wherever practical.

### 3. Current scope

Implemented:

- `nvai` CLI entrypoint.
- Interactive REPL.
- One-shot prompt mode.
- NVIDIA OpenAI-compatible HTTP client.
- API-key storage and expiration logic.
- Base URL normalization.
- Expire-date parsing for multiple common formats.
- Masked API-key input.
- Status/spinner output.
- User-local install/uninstall scripts.
- `nvai doctor` diagnostics.
- Tests for auth/date parsing, key storage, CLI routing, progress UI, doctor, and prompt utilities.

Not implemented yet:

- Agent tool protocol for file patching.
- Safe shell command execution loop.
- Diff preview and patch approval.
- Full-screen TUI.
- `.deb` package and apt repository.
- Streaming token output.

### 4. Runtime model

`nvai-cli` is not a daemon. It does not need a background service.

Runtime flow:

```text
user runs `nvai`
  -> shell resolves wrapper from PATH
  -> wrapper executes installed venv Python
  -> python -m nvai.cli
  -> ensure_valid_api_key()
  -> REPL or one-shot command
  -> Ctrl+C/Ctrl+D//exit//quit
  -> process exits and terminal prompt returns
```

### 5. Install model

The user-local installer creates this layout:

```text
~/.local/share/nvai-cli/
  app/                  # copied/cloned source tree
  .venv/                # isolated Python environment

~/.local/bin/nvai       # wrapper script
~/.config/nvai/keys.toml # user key store, created at first auth
```

The wrapper does not `cd` into the app directory. This is intentional: `nvai` should analyze the caller's current directory.

Wrapper behavior:

```bash
exec "$NVAI_PYTHON" -m nvai.cli "$@"
```

### 6. Source layout

```text
src/nvai/
  __init__.py
  auth_flow.py       # ensures a valid active API key exists
  cli.py             # argparse entrypoint, REPL, one-shot commands
  context.py         # lightweight project context collection
  datetime_utils.py  # expire-date parsing/formatting
  doctor.py          # install/runtime diagnostics
  key_prompt.py      # setup prompts, masked input, URL normalization
  key_store.py       # TOML key-store load/save and permissions
  models.py          # dataclasses and defaults
  nvidia_client.py   # NVIDIA OpenAI-compatible HTTP client
  ui.py              # status spinner / non-TTY status lines

tests/
  test_cli.py
  test_datetime_utils.py
  test_doctor.py
  test_key_prompt.py
  test_key_store.py
  test_ui.py

install.sh
uninstall.sh
scripts/install-user.sh
scripts/uninstall-user.sh
```

### 7. API-key lifecycle

Every command that needs NVIDIA API access begins with:

```python
ensure_valid_api_key()
```

High-level logic:

```text
load ~/.config/nvai/keys.toml
  -> find active_key
  -> if missing: prompt for a new key
  -> if expired: prompt for a new key
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

The default key store path is:

```text
~/.config/nvai/keys.toml
```

It can be overridden for tests or automation:

```bash
NVAI_KEY_STORE=/tmp/keys.toml nvai auth status
```

### 8. Expire-date parsing

Supported input formats:

```text
YYYY-MM-DD
YYYY-MM-DD HH:MM
YYYY-MM-DDTHH:MM:SS+09:00
YYYY/MM/DD
MM/DD/YYYY
```

For slash dates like `01/08/2027`, ambiguous values are interpreted as `MM/DD/YYYY`, matching common NVIDIA/US-style dates. Therefore:

```text
01/08/2027 -> 2027-01-08 00:00 local time
```

### 9. Base URL normalization

The setup prompt accepts common copied URL shapes and normalizes them:

```text
integrate.api.nvidia.com/v1
<https://integrate.api.nvidia.com/v1|integrate.api.nvidia.com/v1>
integrate.api.nvidia.com/v1 (https://integrate.api.nvidia.com/v1)
```

All become:

```text
https://integrate.api.nvidia.com/v1
```

### 10. NVIDIA client

`src/nvai/nvidia_client.py` uses Python standard-library `urllib` to keep dependencies minimal.

Endpoints:

```text
GET  /models
POST /chat/completions
```

The client handles common HTTP cases:

```text
401 -> rejected/expired key
403 -> permission/model access issue
404 -> endpoint/model issue
429 -> rate limit
5xx/other -> reported with details
```

### 11. CLI behavior

Commands:

```text
nvai                     -> interactive mode
nvai "prompt"            -> one-shot prompt
nvai ask "prompt"        -> explicit one-shot prompt
nvai models              -> list NVIDIA models
nvai doctor              -> local diagnostics
nvai auth status/add/refresh/list/use
```

Interactive commands:

```text
/help
/context
/exit
/quit
Ctrl+C
Ctrl+D
```

### 12. Status/progress UI

`src/nvai/ui.py` provides a `Status` context manager.

On TTY:

```text
⠋ Waiting for NVIDIA model response (z-ai/glm-5.2)... 1.2s
```

On non-TTY/logs:

```text
[status] Waiting for NVIDIA model response (z-ai/glm-5.2)...
[ok] Waiting for NVIDIA model response (z-ai/glm-5.2) (2.4s)
```

This makes long-running model/API calls visibly active.

### 13. Installer design

`install.sh` and `scripts/install-user.sh` support:

```text
NVAI_REPO_URL
NVAI_REF
NVAI_SOURCE_DIR
NVAI_INSTALL_DIR
NVAI_BIN_DIR
```

`NVAI_SOURCE_DIR` exists to test the install flow without pushing to GitHub.

The installer uses `uv` if available and falls back to `python3 -m venv` plus `pip`.

### 14. Uninstaller design

`uninstall.sh` and `scripts/uninstall-user.sh` remove:

```text
~/.local/bin/nvai
~/.local/share/nvai-cli
```

By default they preserve:

```text
~/.config/nvai
~/.local/share/nvai
```

To remove user config/API keys too:

```bash
NVAI_REMOVE_CONFIG=1 bash uninstall.sh
```

### 15. Test and verification strategy

Tests are written with `pytest` and cover:

- CLI routing and REPL helper behavior.
- `/help`, `/exit`, and Ctrl+C handling.
- Expire-date parsing.
- Key-store read/write and `0600` permissions.
- URL normalization.
- Status UI on non-TTY streams.
- `nvai doctor` output.

Typical verification:

```bash
uv run --with pytest -- python -m pytest -q -p no:cacheprovider
NVAI_SOURCE_DIR=$PWD NVAI_INSTALL_DIR=/tmp/nvai-install-test NVAI_BIN_DIR=/tmp/nvai-bin-test bash install.sh
PATH=/tmp/nvai-bin-test:$PATH nvai doctor
NVAI_INSTALL_DIR=/tmp/nvai-install-test NVAI_BIN_DIR=/tmp/nvai-bin-test bash uninstall.sh
```

### 16. Future architecture work

Recommended next steps:

1. Add an action-block tool protocol.
2. Implement `read_file`, `write_patch`, and `shell` tools.
3. Add patch preview and approval.
4. Add safe command execution with confirmation.
5. Add streaming model output.
6. Add optional `prompt_toolkit` or full-screen TUI.
7. Add GitHub Release packaging.
8. Add `.deb` packaging and, later, apt repository support.

---

## 한국어

### 1. 목적

`nvai-cli`는 NVIDIA AI / NIM OpenAI 호환 LLM API를 Linux 터미널에서 사용하기 위한 CLI입니다. NVIDIA API Key가 매일 만료되고 사용자가 새 key를 입력해야 하는 워크플로우를 기준으로 설계되었습니다.

목표는 다음처럼 `codex`, `claude`와 비슷한 CLI 진입점을 제공하는 것입니다.

```bash
nvai
```

실행하면 인터랙티브 REPL에 진입하고, API Key 갱신을 처리하고, NVIDIA API를 호출한 뒤, 사용자가 종료하면 다시 터미널로 돌아옵니다.

### 2. 설계 목표

- 어느 디렉터리에서든 `nvai` 명령으로 실행.
- 일반 사용자는 virtualenv activate/deactivate 없이 사용.
- 사용자의 현재 작업 디렉터리를 보존하여 실제 프로젝트 context를 기준으로 동작.
- 매일 만료되는 NVIDIA API Key 지원.
- API Key는 사용자 로컬 설정에 저장하고 프로젝트 repo에는 저장하지 않음.
- 네트워크/모델 응답 대기 중 진행 상태 표시.
- `.deb` 또는 apt repository 이전 단계로 GitHub `curl | bash` 설치 지원.
- 의존성을 최소화하고 가능한 한 Python 표준 라이브러리 사용.

### 3. 현재 구현 범위

구현됨:

- `nvai` CLI entrypoint.
- 인터랙티브 REPL.
- 단발 prompt 모드.
- NVIDIA OpenAI 호환 HTTP client.
- API Key 저장 및 만료 확인 로직.
- Base URL 정규화.
- 여러 날짜 형식 parsing.
- `*` 표시가 있는 API Key 입력.
- 상태 spinner/progress 출력.
- user-local install/uninstall script.
- `nvai doctor` 진단 명령.
- auth/date/key/CLI/progress/doctor 관련 테스트.

아직 미구현:

- 파일 patching용 agent tool protocol.
- 안전한 shell command 실행 loop.
- diff preview 및 patch 승인.
- full-screen TUI.
- `.deb` 패키지와 apt repository.
- token streaming 출력.

### 4. 실행 모델

`nvai-cli`는 daemon이 아닙니다. 백그라운드에서 계속 떠 있을 필요가 없습니다.

실행 흐름:

```text
사용자가 `nvai` 실행
  -> shell이 PATH에서 wrapper 검색
  -> wrapper가 설치된 venv Python 실행
  -> python -m nvai.cli
  -> ensure_valid_api_key()
  -> REPL 또는 단발 명령 실행
  -> Ctrl+C/Ctrl+D//exit//quit
  -> 프로세스 종료 후 터미널 복귀
```

### 5. 설치 모델

user-local installer는 다음 구조를 만듭니다.

```text
~/.local/share/nvai-cli/
  app/                  # 복사/clone된 source tree
  .venv/                # 독립 Python 환경

~/.local/bin/nvai        # wrapper script
~/.config/nvai/keys.toml # 최초 인증 시 생성되는 key store
```

wrapper는 앱 디렉터리로 `cd`하지 않습니다. 이것은 의도된 설계입니다. `nvai`는 사용자가 실행한 현재 디렉터리를 기준으로 프로젝트 context를 수집해야 하기 때문입니다.

wrapper 핵심 동작:

```bash
exec "$NVAI_PYTHON" -m nvai.cli "$@"
```

### 6. 소스 구조

```text
src/nvai/
  __init__.py
  auth_flow.py       # 유효한 active API Key 보장
  cli.py             # argparse entrypoint, REPL, 단발 명령
  context.py         # 가벼운 프로젝트 context 수집
  datetime_utils.py  # expire-date parsing/formatting
  doctor.py          # 설치/실행 진단
  key_prompt.py      # setup prompt, masked input, URL 정규화
  key_store.py       # TOML key-store load/save 및 권한 처리
  models.py          # dataclass 및 기본값
  nvidia_client.py   # NVIDIA OpenAI 호환 HTTP client
  ui.py              # spinner/status line

tests/
  test_cli.py
  test_datetime_utils.py
  test_doctor.py
  test_key_prompt.py
  test_key_store.py
  test_ui.py

install.sh
uninstall.sh
scripts/install-user.sh
scripts/uninstall-user.sh
```

### 7. API Key 생명주기

NVIDIA API 접근이 필요한 명령은 먼저 다음을 호출합니다.

```python
ensure_valid_api_key()
```

상위 로직:

```text
~/.config/nvai/keys.toml 로드
  -> active_key 탐색
  -> 없으면 새 key 입력
  -> 만료되었으면 새 key 입력
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

기본 key store 경로:

```text
~/.config/nvai/keys.toml
```

테스트나 자동화에서는 다음처럼 override할 수 있습니다.

```bash
NVAI_KEY_STORE=/tmp/keys.toml nvai auth status
```

### 8. 만료일 parsing

지원 형식:

```text
YYYY-MM-DD
YYYY-MM-DD HH:MM
YYYY-MM-DDTHH:MM:SS+09:00
YYYY/MM/DD
MM/DD/YYYY
```

`01/08/2027`처럼 `/`를 사용하는 모호한 형식은 NVIDIA/미국식 날짜 입력을 고려해 `MM/DD/YYYY`로 해석합니다.

```text
01/08/2027 -> 2027-01-08 00:00 local time
```

### 9. Base URL 정규화

setup prompt는 다음과 같은 붙여넣기 형태를 받아 정규화합니다.

```text
integrate.api.nvidia.com/v1
<https://integrate.api.nvidia.com/v1|integrate.api.nvidia.com/v1>
integrate.api.nvidia.com/v1 (https://integrate.api.nvidia.com/v1)
```

모두 다음으로 저장됩니다.

```text
https://integrate.api.nvidia.com/v1
```

### 10. NVIDIA client

`src/nvai/nvidia_client.py`는 의존성을 최소화하기 위해 Python 표준 라이브러리 `urllib`를 사용합니다.

사용 endpoint:

```text
GET  /models
POST /chat/completions
```

주요 HTTP 상태 처리:

```text
401 -> key 거부/만료 가능성
403 -> 권한 또는 모델 접근 문제
404 -> endpoint 또는 model 문제
429 -> rate limit
기타 -> 세부 메시지와 함께 보고
```

### 11. CLI 동작

명령어:

```text
nvai                     -> 인터랙티브 모드
nvai "prompt"            -> 단발 요청
nvai ask "prompt"        -> 명시적 단발 요청
nvai models              -> NVIDIA 모델 목록
nvai doctor              -> 로컬 진단
nvai auth status/add/refresh/list/use
```

인터랙티브 명령:

```text
/help
/context
/exit
/quit
Ctrl+C
Ctrl+D
```

### 12. 상태/progress UI

`src/nvai/ui.py`는 `Status` context manager를 제공합니다.

TTY에서는 다음처럼 spinner를 출력합니다.

```text
⠋ Waiting for NVIDIA model response (z-ai/glm-5.2)... 1.2s
```

로그/비TTY 환경에서는 다음처럼 출력합니다.

```text
[status] Waiting for NVIDIA model response (z-ai/glm-5.2)...
[ok] Waiting for NVIDIA model response (z-ai/glm-5.2) (2.4s)
```

이를 통해 모델/API 응답 대기 중인지 사용자가 확인할 수 있습니다.

### 13. Installer 설계

`install.sh`와 `scripts/install-user.sh`는 다음 환경변수를 지원합니다.

```text
NVAI_REPO_URL
NVAI_REF
NVAI_SOURCE_DIR
NVAI_INSTALL_DIR
NVAI_BIN_DIR
```

`NVAI_SOURCE_DIR`는 GitHub push 전에도 설치 흐름을 테스트하기 위해 추가했습니다.

installer는 `uv`가 있으면 `uv`를 사용하고, 없으면 `python3 -m venv`와 `pip`로 fallback합니다.

### 14. Uninstaller 설계

`uninstall.sh`와 `scripts/uninstall-user.sh`는 다음을 삭제합니다.

```text
~/.local/bin/nvai
~/.local/share/nvai-cli
```

기본적으로 아래 설정은 보존합니다.

```text
~/.config/nvai
~/.local/share/nvai
```

API Key 설정까지 삭제하려면:

```bash
NVAI_REMOVE_CONFIG=1 bash uninstall.sh
```

### 15. 테스트 및 검증 전략

`pytest` 기반 테스트는 다음을 검증합니다.

- CLI routing 및 REPL helper 동작.
- `/help`, `/exit`, Ctrl+C 처리.
- expire-date parsing.
- key-store read/write 및 `0600` 권한.
- URL 정규화.
- non-TTY status UI.
- `nvai doctor` 출력.

일반 검증 명령:

```bash
uv run --with pytest -- python -m pytest -q -p no:cacheprovider
NVAI_SOURCE_DIR=$PWD NVAI_INSTALL_DIR=/tmp/nvai-install-test NVAI_BIN_DIR=/tmp/nvai-bin-test bash install.sh
PATH=/tmp/nvai-bin-test:$PATH nvai doctor
NVAI_INSTALL_DIR=/tmp/nvai-install-test NVAI_BIN_DIR=/tmp/nvai-bin-test bash uninstall.sh
```

### 16. 향후 개발 방향

추천 다음 단계:

1. action-block tool protocol 추가.
2. `read_file`, `write_patch`, `shell` tool 구현.
3. patch preview 및 승인 flow 추가.
4. 안전한 command 실행 확인 flow 추가.
5. streaming model output 추가.
6. 선택적으로 `prompt_toolkit` 또는 full-screen TUI 추가.
7. GitHub Release packaging 추가.
8. `.deb` packaging 및 나중에 apt repository 지원.
