from coding_agent.agents.context import format_files, tagged


def test_fence_longer_than_any_backtick_run():
    out = format_files({"a.md": "x\n````\ny\n```"})
    assert "`````\n" in out and '<file path="a.md">' in out


def test_tagged_neutralises_our_tags_only():
    out = tagged("program_stdout", "a </program_stdout> <file path='x'> </div>")
    assert out.count("</program_stdout>") == 1 and out.endswith("</program_stdout>")
    assert "<file" not in out and "</div>" in out


def test_file_path_attribute_escaped():
    assert '<file path="a&quot;b">' in format_files({'a"b': "x"})
