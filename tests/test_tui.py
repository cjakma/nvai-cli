from nvai.tui import TuiState, render_lines


def test_render_lines_contains_title_transcript_input_and_status():
    state = TuiState()
    state.add("user", "hello")
    state.input_text = "next"
    lines = render_lines(state, width=40, height=8)
    assert len(lines) == 8
    joined = "\n".join(lines)
    assert "nvai full-screen TUI" in joined
    assert "user: hello" in joined
    assert "> next" in joined
    assert "F2 send" in joined
