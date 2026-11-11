from coding_agent.tracing import trace_metadata


def test_shape_for_graph_run():
    md = trace_metadata("run-1", "graph", "fix_mean")
    assert md["langfuse_session_id"] == "run-1"
    assert md["langfuse_trace_name"] == "coding-agent/graph"
    assert md["langfuse_tags"] == ["graph", "fix_mean"]


def test_task_id_is_optional_and_extra_tags_are_appended_without_duplicates():
    md = trace_metadata("r", "single_shot", tags=["bug_fix", "graph", "bug_fix"])
    assert md["langfuse_tags"] == ["single_shot", "bug_fix", "graph"]
    assert trace_metadata("r", "graph", "t")["langfuse_tags"] == ["graph", "t"]


def test_values_are_langchain_metadata_safe():
    md = trace_metadata("r", "graph", "t", tags=["x"])
    assert all(k.startswith("langfuse_") for k in md)
    assert isinstance(md["langfuse_tags"], list)
