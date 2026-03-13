from pipeline.transcript_parser import parse_speaker_turns, parse_transcript, parse_transcript_with_metadata


def test_parse_single_turn_format_a():
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
        "[00:00][Speaker]: Hello",
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


# --- Format B tests ---


def test_parse_format_b_single_turn():
    """Format B: [speaker]: content (no timestamp)."""
    line = "[用户]: 你好，我想了解一下这个产品"
    turns = parse_speaker_turns([line], fragment_base_epoch=1000000)
    assert len(turns) == 1
    assert turns[0]["speaker_label"] == "用户"
    assert turns[0]["content"] == "你好，我想了解一下这个产品"


def test_parse_format_b_multiple_turns_with_duration():
    """Format B turns get interpolated timestamps when fragment duration is known."""
    lines = [
        "[Speaker A]: First line",
        "[Speaker B]: Second line",
        "[Speaker A]: Third line",
    ]
    turns = parse_speaker_turns(lines, fragment_base_epoch=1000000, fragment_duration=300)
    assert len(turns) == 3
    # Interpolated: 0, 100, 200 across 300s duration
    assert turns[0]["absolute_epoch"] == 1000000
    assert turns[1]["absolute_epoch"] == 1000100
    assert turns[2]["absolute_epoch"] == 1000200


def test_parse_format_b_no_duration_increments():
    """Format B turns without duration get 1s increments."""
    lines = [
        "[A]: Hello",
        "[B]: World",
    ]
    turns = parse_speaker_turns(lines, fragment_base_epoch=1000000, fragment_duration=0)
    assert turns[0]["absolute_epoch"] == 1000000
    assert turns[1]["absolute_epoch"] == 1000001


def test_parse_format_b_with_annotations():
    """Format B turns should also have annotations stripped."""
    line = "[Speaker]: [音调平稳] [正常语速] 这是内容"
    turns = parse_speaker_turns([line], fragment_base_epoch=1000000)
    assert len(turns) == 1
    assert turns[0]["content"] == "这是内容"


def test_parse_transcript_format_b_via_full_parser():
    """Integration: full transcript with Format B turns parsed correctly."""
    transcript = """[Fragment 1: 1000000 - 1000300]
标题: 测试对话
类型: daily

[用户]: 今天天气不错
[朋友]: 是啊很好"""
    result = parse_transcript_with_metadata(transcript, event_start_epoch=1000000)
    assert len(result["turns"]) == 2
    assert result["turns"][0]["speaker_label"] == "用户"
    assert result["turns"][1]["speaker_label"] == "朋友"
    assert result["title"] == "测试对话"
    assert "用户" in result["speakers"]
    assert "朋友" in result["speakers"]


def test_format_b_skips_fragment_headers():
    """Format B parser should not treat Fragment headers as speaker turns."""
    lines = [
        "[Fragment 1: 1000000 - 1000300]",
        "[Speaker]: Hello",
    ]
    turns = parse_speaker_turns(lines, fragment_base_epoch=1000000)
    assert len(turns) == 1
    assert turns[0]["speaker_label"] == "Speaker"


# --- Annotation whitelist tests ---


def test_annotation_whitelist_preserves_non_annotation_brackets():
    """Content with non-annotation brackets should be preserved."""
    line = "[00:10][Speaker]: [APP名称] 是一个好产品"
    turns = parse_speaker_turns([line], fragment_base_epoch=1000000)
    assert len(turns) == 1
    assert "[APP名称]" in turns[0]["content"]


def test_annotation_whitelist_strips_known_annotations():
    """Known annotation keywords should be stripped."""
    line = "[00:10][Speaker]: [犹豫停顿] [语速较快] 好的我知道了"
    turns = parse_speaker_turns([line], fragment_base_epoch=1000000)
    assert turns[0]["content"] == "好的我知道了"


def test_parse_transcript_normalized_format():
    """Integration: normalized transcript with 说话人N labels and no timestamps."""
    transcript = """[Fragment 1: 2026-03-14 10:00 - 2026-03-14 10:15]
标题: 产品讨论
类型: career

[用户]: 我们来看一下这个方案
[说话人1/男]: 这个方案不错
[说话人2/女]: 我同意
[同事/朋友]: 我也觉得可以"""
    result = parse_transcript_with_metadata(transcript, event_start_epoch=1000000)
    assert len(result["turns"]) == 4
    assert result["turns"][0]["speaker_label"] == "用户"
    assert result["turns"][1]["speaker_label"] == "说话人1/男"
    assert result["turns"][2]["speaker_label"] == "说话人2/女"
    assert result["turns"][3]["speaker_label"] == "同事/朋友"
    assert result["title"] == "产品讨论"
    assert result["types"] == ["career"]


def test_mixed_format_a_and_b_in_fragments():
    """Different fragments can have different formats."""
    transcript = """[Fragment 1: 1000000 - 1000300]
标题: Mixed
类型: career

[00:00][Speaker A]: Format A content

[Fragment 2: 1000300 - 1000600]

[Speaker B]: Format B content"""
    result = parse_transcript_with_metadata(transcript, event_start_epoch=1000000)
    assert len(result["turns"]) == 2
    assert result["turns"][0]["speaker_label"] == "Speaker A"
    assert result["turns"][1]["speaker_label"] == "Speaker B"
