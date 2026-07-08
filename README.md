# nvai-cli

`nvai-cli` is a Linux terminal CLI for NVIDIA AI / NIM OpenAI-compatible LLM APIs. It provides the `nvai` command, manages daily-expiring NVIDIA API keys, and offers a Codex/Claude-style interactive assistant experience from any directory.

Repository: <https://github.com/cjakma/nvai-cli>

---

## English

### What it does

`nvai-cli` lets you run an NVIDIA-hosted LLM from your terminal:

```bash
nvai
nvai "Analyze this project"
nvai ask "Say OK"
nvai models
nvai doctor
```

The current default model is:

```text
z-ai/glm-5.2
```

The default NVIDIA OpenAI-compatible base URL is:

```text
https://integrate.api.nvidia.com/v1
```

### Key features

- `nvai` global command, runnable without manually activating a Python virtualenv.
- Interactive REPL mode with `/help`, `/context`, `/exit`, `/quit`, Ctrl+C, and Ctrl+D support.
- One-shot prompt mode: `nvai "your request"`.
- NVIDIA OpenAI-compatible `/models` and `/chat/completions` support.
- Daily-expiring API-key workflow:
  - stores key records in `~/.config/nvai/keys.toml`,
  - checks `expiredate` on every run,
  - prompts for a new key when missing or expired,
  - masks API-key input with `*`,
  - writes key storage with `0600` permissions.
- User-friendly setup prompts:
  - accepts `YYYY-MM-DD`, `YYYY-MM-DD HH:MM`, `YYYY/MM/DD`, and `MM/DD/YYYY`,
  - normalizes pasted Slack/Markdown/browser URLs such as `<https://...|...>` and `host (https://...)`.
- Visible progress while waiting for NVIDIA API/model responses.
- Streaming model output for interactive and one-shot asks.
- Codex-like action workflow:
  - model-proposed `read_file` actions execute and feed results back,
  - `patch_file` actions show a unified diff preview and ask for approval,
  - `shell` actions show the command preview and ask for approval,
  - `nvai ask --yes` can auto-approve proposed patch/shell actions for trusted automation.
- User-local installer for GitHub `curl | bash` installation.
- `nvai doctor` diagnostics for executable/Python/PATH/key status.

### Install from GitHub

After this repository is published to GitHub, install with:

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

The installer will:

1. clone `https://github.com/cjakma/nvai-cli.git`,
2. copy the app to `~/.local/share/nvai-cli/app`,
3. create an isolated virtualenv at `~/.local/share/nvai-cli/.venv`,
4. install `nvai-cli`,
5. create `~/.local/bin/nvai`,
6. ensure `~/.local/bin` is available from the user's shell,
7. verify `nvai --help`.

### Uninstall

Remove the user-local install while keeping API-key config:

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

If `uv` is not available:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
```

### First run

```bash
nvai
```

If no valid key exists, `nvai` asks for:

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

### Codex-like action workflow

The action workflow is intentionally model-proposed and user-approved. When the model needs evidence or wants to change/run something, it can emit:

```nvai-actions
[
  {"action":"read_file","path":"README.md","max_bytes":12000},
  {"action":"patch_file","path":"file.py","old":"exact old text","new":"replacement text"},
  {"action":"shell","command":"pytest -q","timeout":120}
]
```

`read_file` runs immediately. `patch_file` prints a unified diff preview and asks before applying. `shell` prints the command preview and asks before execution. In non-interactive automation, proposed patch/shell actions are denied unless `--yes` is supplied.

### Commands

```bash
nvai                     # interactive mode
nvai "Analyze this repo" # one-shot prompt with project context
nvai ask "Say OK"        # explicit one-shot ask
nvai ask --no-context "Say OK"
nvai ask --no-stream "Say OK"
nvai ask --yes "Inspect README and run a safe command if needed"
nvai models              # list NVIDIA models
nvai doctor              # inspect installation and key status
nvai auth status
nvai auth add
nvai auth refresh
nvai auth list
nvai auth use <name>
```

Inside interactive mode:

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
nvai doctor
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

### Notes

- `nvai-cli` is not a daemon. The process starts when you run `nvai` and exits when you press Ctrl+C, Ctrl+D, `/exit`, or `/quit`.
- API keys are user-local and are not stored in the project directory.
- The installer is user-local by default and does not require `sudo`.

---

## 한국어

### 프로젝트 소개

`nvai-cli`는 NVIDIA AI / NIM의 OpenAI 호환 LLM API를 Linux 터미널에서 사용하기 위한 CLI입니다. `nvai` 명령어를 제공하며, 매일 만료되는 NVIDIA API Key를 관리하고, `codex`나 `claude`처럼 터미널에서 바로 진입하는 인터랙티브 어시스턴트 경험을 제공합니다.

저장소: <https://github.com/cjakma/nvai-cli>

### 무엇을 할 수 있나

```bash
nvai
nvai "이 프로젝트 분석해줘"
nvai ask "Say OK"
nvai models
nvai doctor
```

현재 기본 모델은 다음을 기준으로 합니다.

```text
z-ai/glm-5.2
```

기본 NVIDIA OpenAI 호환 API 주소는 다음입니다.

```text
https://integrate.api.nvidia.com/v1
```

### 주요 기능

- `nvai` 전역 명령어 제공: 매번 Python virtualenv를 activate/deactivate 하지 않아도 됩니다.
- 인터랙티브 REPL 모드 지원:
  - `/help`, `/context`, `/exit`, `/quit`, Ctrl+C, Ctrl+D.
- 단발 요청 지원:
  - `nvai "요청 내용"`.
- NVIDIA OpenAI 호환 API 지원:
  - `/models`, `/chat/completions`.
- 매일 만료되는 API Key 관리:
  - `~/.config/nvai/keys.toml`에 key record 저장,
  - 실행할 때마다 `expiredate` 확인,
  - 만료되었거나 없으면 새 key 입력,
  - API Key 입력 시 `*` 표시,
  - key 파일 권한 `0600` 적용.
- 사용자가 붙여넣는 값을 보정:
  - 날짜 형식: `YYYY-MM-DD`, `YYYY-MM-DD HH:MM`, `YYYY/MM/DD`, `MM/DD/YYYY`,
  - URL 형식: `<https://...|...>`, `host (https://...)` 자동 정규화.
- NVIDIA API 응답 대기 중 진행 상태 표시.
- 인터랙티브/단발 요청에서 streaming model output 지원.
- Codex-like action workflow 지원:
  - 모델이 제안한 `read_file` action은 실행 후 결과를 다시 모델에 전달,
  - `patch_file` action은 unified diff preview를 보여준 뒤 승인 후 적용,
  - `shell` action은 command preview를 보여준 뒤 승인 후 실행,
  - 신뢰 가능한 자동화에서는 `nvai ask --yes`로 patch/shell action 자동 승인 가능.
- GitHub `curl | bash` 방식의 user-local 설치 지원.
- `nvai doctor`로 설치/실행 상태 진단.

### GitHub에서 설치

GitHub에 배포된 뒤 다음 명령으로 설치할 수 있습니다.

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

1. `https://github.com/cjakma/nvai-cli.git` clone,
2. 앱을 `~/.local/share/nvai-cli/app`에 복사,
3. `~/.local/share/nvai-cli/.venv` virtualenv 생성,
4. `nvai-cli` 설치,
5. `~/.local/bin/nvai` wrapper 생성,
6. `~/.local/bin` PATH 확인 및 필요 시 `.bashrc` 보정,
7. `nvai --help` 검증.

### 삭제

API Key 설정은 보존하고 설치 파일만 삭제:

```bash
curl -fsSL https://raw.githubusercontent.com/cjakma/nvai-cli/main/uninstall.sh | bash
```

설치 파일과 API Key 설정까지 삭제:

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

### 최초 실행

```bash
nvai
```

유효한 key가 없으면 아래 정보를 입력받습니다.

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

### Codex-like action workflow

action workflow는 모델이 제안하고 사용자가 승인하는 구조입니다. 모델이 근거 확인, 파일 수정, 명령 실행이 필요하다고 판단하면 다음 JSON block을 출력할 수 있습니다.

```nvai-actions
[
  {"action":"read_file","path":"README.md","max_bytes":12000},
  {"action":"patch_file","path":"file.py","old":"exact old text","new":"replacement text"},
  {"action":"shell","command":"pytest -q","timeout":120}
]
```

`read_file`은 즉시 실행됩니다. `patch_file`은 unified diff preview를 보여주고 승인 후 적용합니다. `shell`은 command preview를 보여주고 승인 후 실행합니다. non-interactive 자동화 환경에서는 `--yes`를 주지 않으면 patch/shell action은 거부됩니다.

### 명령어

```bash
nvai                         # 인터랙티브 모드
nvai "이 repo 분석해줘"       # 현재 디렉터리 context 포함 단발 요청
nvai ask "Say OK"            # 명시적 단발 질문
nvai ask --no-context "Say OK"
nvai ask --no-stream "Say OK"
nvai ask --yes "README를 확인하고 필요한 안전한 명령을 실행해줘"
nvai models                  # NVIDIA 모델 목록
nvai doctor                  # 설치 및 key 상태 진단
nvai auth status
nvai auth add
nvai auth refresh
nvai auth list
nvai auth use <name>
```

인터랙티브 모드 내부 명령:

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
nvai doctor
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

### 참고

- `nvai-cli`는 daemon이 아닙니다. `nvai`를 입력할 때 프로세스가 시작되고, Ctrl+C, Ctrl+D, `/exit`, `/quit`로 종료하면 터미널로 복귀합니다.
- API Key는 사용자 로컬 설정에 저장되며 프로젝트 디렉터리에 저장되지 않습니다.
- 기본 설치 방식은 user-local이며 `sudo`가 필요 없습니다.
