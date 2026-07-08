from datetime import datetime, timedelta

from nvai.agent import run_agent_turn
from nvai.models import ApiKeyRecord


class FakeClient:
    def __init__(self):
        self.key = ApiKeyRecord(
            name="k",
            model="z-ai/glm-5.2",
            api_key="secret",
            expiredate=datetime.now().astimezone() + timedelta(days=1),
        )
        self.calls = 0

    def chat_stream(self, messages):
        self.calls += 1
        if self.calls == 1:
            yield 'Need to inspect.\n```nvai-actions\n[{"action":"read_file","path":"a.txt"}]\n```'
        else:
            yield "Done after reading."

    def chat(self, messages):
        self.calls += 1
        return "Done"


def test_run_agent_turn_executes_read_file_action(tmp_path, capsys):
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")
    client = FakeClient()
    history = [{"role": "user", "content": "read a"}]
    answer = run_agent_turn(client, history, cwd=tmp_path)
    captured = capsys.readouterr()
    assert answer == "Done after reading."
    assert "[actions] 1 proposed" in captured.out
    assert "read " in captured.out
    assert "hello" in captured.out
    assert client.calls == 2
