from scripts.transcript_parser import parse_speaker_turns, parse_transcript, parse_speaker_analysis, match_speaker

def test_parse_single_turn():
    line = "[00:06][受访对象/产品测试用户]: [思考停顿] [认真语气] 如果说是落实到这个图标的话"
    turns = parse_speaker_turns([line], fragment_base_epoch=1771827235)
    assert len(turns) == 1
    assert turns[0]["speaker_label"] == "受访对象/产品测试用户"
    assert turns[0]["content"] == "如果说是落实到这个图标的话"
    assert turns[0]["offset_seconds"] == 6

def test_parse_strips_multiple_annotations():
    line = "[01:30][Speaker]: [音调平稳] [专业语气] [正常语速] 具体的设计比如说这种字体"
    turns = parse_speaker_turns([line], fragment_base_epoch=1000000)
    assert turns[0]["content"] == "具体的设计比如说这种字体"

def test_parse_skips_non_turn_lines():
    lines = [
        "[Fragment 1: 2026-02-23 06:13 - 2026-02-23 06:20]",
        "标题: APP设计方案",
        "类型: career",
        "",
        "[00:00][Speaker]: Hello"
    ]
    turns = parse_speaker_turns(lines, fragment_base_epoch=1000000)
    assert len(turns) == 1

def test_parse_calculates_absolute_timestamp():
    line = "[01:30][Speaker]: content"
    turns = parse_speaker_turns([line], fragment_base_epoch=1000000)
    assert turns[0]["absolute_epoch"] == 1000090

def test_parse_transcript_multi_fragment():
    transcript = """[Fragment 1: 2026-02-23 06:13 - 2026-02-23 06:20]
标题: Test
类型: career

[00:00][Speaker A]: Hello
[00:10][Speaker B]: World

[Fragment 2: 1771828000 - 1771829000]

[00:00][Speaker A]: Second fragment
[00:05][Speaker B]: More content"""
    turns = parse_transcript(transcript, event_start_epoch=1771827235)
    assert len(turns) == 4
    assert turns[0]["speaker_label"] == "Speaker A"
    assert turns[1]["speaker_label"] == "Speaker B"
    assert turns[2]["absolute_epoch"] == 1771828000
    assert turns[3]["absolute_epoch"] == 1771828005

def test_parse_speaker_analysis():
    json_str = '[{"unified_speaker_id": "unified_000", "is_user": true, "identity": "", "relation_to_user": "用户本人"}]'
    speakers = parse_speaker_analysis(json_str)
    assert len(speakers) == 1
    assert speakers[0]["is_user"] is True

def test_parse_speaker_analysis_empty():
    assert parse_speaker_analysis("") == []
    assert parse_speaker_analysis(None) == []

def test_parse_speaker_analysis_list_input():
    data = [{"unified_speaker_id": "u0", "is_user": True}]
    assert parse_speaker_analysis(data) == data

def test_match_speaker_by_relation():
    speakers = [
        {"unified_speaker_id": "u0", "identity": "", "relation_to_user": "用户本人"},
        {"unified_speaker_id": "u1", "identity": "用户研究员/产品经理", "relation_to_user": "访谈主持人"},
    ]
    result = match_speaker("访谈主持人/用户研究员/产品经理", speakers)
    assert result["unified_speaker_id"] == "u1"

def test_match_speaker_no_match():
    speakers = [{"unified_speaker_id": "u0", "identity": "Alice", "relation_to_user": "Friend"}]
    result = match_speaker("CompletelyDifferent", speakers)
    assert result is None
