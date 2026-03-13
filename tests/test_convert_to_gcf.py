# tests/test_convert_to_gcf.py
from scripts.convert_to_gcf import (
    parse_fragments, normalize_speaker, should_skip_speaker,
    build_gcf_groups, convert_event,
)

# --- parse_fragments tests ---


def test_parse_fragments_single_fragment():
    transcript = """[Fragment 1: 1771798380 - 1771798800]
标题: 用户反馈讨论
类型: career, self_awareness

[00:00][Speaker A]: Hello
[00:10][Speaker B]: World"""
    frags = parse_fragments(transcript, event_start_epoch=1771827235)
    assert len(frags) == 1
    assert frags[0]["title"] == "用户反馈讨论"
    assert frags[0]["types"] == ["career", "self_awareness"]
    assert len(frags[0]["turns"]) == 2
    assert frags[0]["turns"][0]["speaker_label"] == "Speaker A"
    assert frags[0]["base_epoch"] == 1771798380
    assert frags[0]["end_epoch"] == 1771798800


def test_parse_fragments_multi_fragment():
    transcript = """[Fragment 1: 1000000 - 1000300]
标题: First Topic
类型: career

[00:00][A]: First

[Fragment 2: 1000300 - 1000600]
标题: Second Topic
类型: social

[00:00][B]: Second"""
    frags = parse_fragments(transcript, event_start_epoch=1000000)
    assert len(frags) == 2
    assert frags[0]["title"] == "First Topic"
    assert frags[0]["types"] == ["career"]
    assert frags[1]["title"] == "Second Topic"
    assert frags[1]["types"] == ["social"]


def test_parse_fragments_no_fragment_headers():
    """Events with no Fragment headers treat entire transcript as one implicit fragment."""
    transcript = """[用户]: 你好
[朋友]: 嗨"""
    frags = parse_fragments(transcript, event_start_epoch=1000000)
    assert len(frags) == 1
    assert frags[0]["title"] is None
    assert len(frags[0]["turns"]) == 2


def test_parse_fragments_skips_passive_media():
    transcript = """[Fragment 1: 1000000 - 1000300]
标题: 收听播客
类型: interest

(被动媒体，转录内容已略过)

------------------------------------------

[Fragment 2: 1000300 - 1000600]
标题: 聊天
类型: social

[00:00][A]: Active content"""
    frags = parse_fragments(transcript, event_start_epoch=1000000)
    assert len(frags) == 1
    assert frags[0]["title"] == "聊天"


def test_parse_fragments_per_fragment_title_types():
    """Each fragment can have its own title and types."""
    transcript = """[Fragment 1: 1000000 - 1000300]
标题: Topic A
类型: career

[00:00][X]: content1

[Fragment 2: 1000300 - 1000600]
标题: Topic B
类型: social, home

[00:00][Y]: content2"""
    frags = parse_fragments(transcript, event_start_epoch=1000000)
    assert frags[0]["title"] == "Topic A"
    assert frags[0]["types"] == ["career"]
    assert frags[1]["title"] == "Topic B"
    assert frags[1]["types"] == ["social", "home"]


# --- Speaker normalization tests ---


def test_normalize_speaker_main_user():
    assert normalize_speaker("user") == "user_main"
    assert normalize_speaker("用户") == "user_main"
    assert normalize_speaker("User") == "user_main"


def test_normalize_speaker_preserves_others():
    assert normalize_speaker("unified_001") == "unified_001"
    assert normalize_speaker("SPEAKER_01") == "SPEAKER_01"
    assert normalize_speaker("访谈主持人/用户研究员/产品经理") == "访谈主持人/用户研究员/产品经理"


def test_should_skip_speaker_background():
    assert should_skip_speaker("背景音") is True
    assert should_skip_speaker("背景声") is True
    assert should_skip_speaker("背景噪音") is True
    assert should_skip_speaker("背景音: 电子提示音") is True
    assert should_skip_speaker("视频背景音") is True


def test_should_skip_speaker_environment():
    assert should_skip_speaker("环境音") is True
    assert should_skip_speaker("路人/环境背景音/背景人声/表演者") is True


def test_should_skip_speaker_passerby():
    assert should_skip_speaker("路人/背景人声") is True
    assert should_skip_speaker("陌生人/路人/背景人声") is True


def test_should_skip_speaker_irrelevant():
    assert should_skip_speaker("无关人员/环境音来源/未知人员") is True


def test_should_skip_speaker_normal():
    assert should_skip_speaker("unified_001") is False
    assert should_skip_speaker("user_main") is False
    assert should_skip_speaker("Speaker A") is False


# --- GCF builder tests ---


def _make_turns(n, speaker="A", base_epoch=1000000):
    """Helper: generate n dummy turns."""
    return [
        {"speaker_label": speaker, "content": f"msg {i}", "offset_seconds": i, "absolute_epoch": base_epoch + i}
        for i in range(n)
    ]


def test_build_gcf_single_group_no_split():
    """Event with few fragments -> single GCF group."""
    fragments = [
        {"title": "Topic", "types": ["career"], "base_epoch": 1000000, "end_epoch": 1000300, "turns": _make_turns(5)},
    ]
    groups = build_gcf_groups(
        event_id="evt-001",
        event_start_epoch=1000000,
        fragments=fragments,
        split_frag_threshold=8,
        split_turn_threshold=100,
    )
    assert len(groups) == 1
    gcf = groups[0]
    assert gcf["version"] == "1.0.0"
    assert gcf["conversation_meta"]["group_id"] == "evt-001"
    assert gcf["conversation_meta"]["name"] == "Topic"
    assert gcf["conversation_meta"]["tags"] == ["career"]
    assert gcf["conversation_meta"]["scene"] == "group_chat"
    assert len(gcf["conversation_list"]) == 5
    msg = gcf["conversation_list"][0]
    assert "message_id" in msg
    assert msg["type"] == "text"
    assert msg["role"] == "user"
    assert "refer_list" in msg


def test_build_gcf_splits_many_fragments():
    """Event with >threshold fragments -> split by fragment."""
    fragments = [
        {"title": f"Topic {i}", "types": ["social"], "base_epoch": 1000000 + i * 300, "end_epoch": 1000000 + (i+1) * 300, "turns": _make_turns(3, base_epoch=1000000 + i * 300)}
        for i in range(10)
    ]
    groups = build_gcf_groups(
        event_id="evt-002",
        event_start_epoch=1000000,
        fragments=fragments,
        split_frag_threshold=8,
        split_turn_threshold=100,
    )
    assert len(groups) == 10
    assert groups[0]["conversation_meta"]["group_id"] == "evt-002_part0"
    assert groups[9]["conversation_meta"]["group_id"] == "evt-002_part9"
    assert groups[0]["conversation_meta"]["name"] == "Topic 0"
    assert groups[5]["conversation_meta"]["name"] == "Topic 5"


def test_build_gcf_splits_many_turns():
    """Event with >threshold total turns -> split by fragment."""
    fragments = [
        {"title": "Big1", "types": ["career"], "base_epoch": 1000000, "end_epoch": 1000300, "turns": _make_turns(60)},
        {"title": "Big2", "types": ["career"], "base_epoch": 1000300, "end_epoch": 1000600, "turns": _make_turns(60, base_epoch=1000300)},
    ]
    groups = build_gcf_groups(
        event_id="evt-003",
        event_start_epoch=1000000,
        fragments=fragments,
        split_frag_threshold=8,
        split_turn_threshold=100,
    )
    assert len(groups) == 2  # 120 turns > 100 threshold -> split


def test_build_gcf_single_fragment_large_turns_windowed():
    """Single fragment with >200 turns -> split by 100-turn windows."""
    fragments = [
        {"title": "Long Chat", "types": ["social"], "base_epoch": 1000000, "end_epoch": 1000600, "turns": _make_turns(250)},
    ]
    groups = build_gcf_groups(
        event_id="evt-004",
        event_start_epoch=1000000,
        fragments=fragments,
        split_frag_threshold=8,
        split_turn_threshold=100,
    )
    assert len(groups) == 3  # 250 turns -> windows of 100, 100, 50
    assert groups[0]["conversation_meta"]["group_id"] == "evt-004_part0"
    assert len(groups[0]["conversation_list"]) == 100
    assert len(groups[2]["conversation_list"]) == 50


def test_build_gcf_speaker_normalization():
    """user/用户/User speakers are normalized to user_main in output."""
    turns = [
        {"speaker_label": "user", "content": "hi", "offset_seconds": 0, "absolute_epoch": 1000000},
        {"speaker_label": "用户", "content": "hello", "offset_seconds": 1, "absolute_epoch": 1000001},
    ]
    fragments = [{"title": "Test", "types": [], "base_epoch": 1000000, "end_epoch": 1000300, "turns": turns}]
    groups = build_gcf_groups("evt-005", 1000000, fragments, 8, 100)
    msgs = groups[0]["conversation_list"]
    assert msgs[0]["sender"] == "user_main"
    assert msgs[0]["sender_name"] == "user"
    assert msgs[1]["sender"] == "user_main"
    assert msgs[1]["sender_name"] == "用户"


def test_build_gcf_filters_background_speakers():
    """Turns from background/environment speakers are excluded."""
    turns = [
        {"speaker_label": "unified_001", "content": "real", "offset_seconds": 0, "absolute_epoch": 1000000},
        {"speaker_label": "背景音", "content": "noise", "offset_seconds": 1, "absolute_epoch": 1000001},
        {"speaker_label": "环境音", "content": "ambient", "offset_seconds": 2, "absolute_epoch": 1000002},
    ]
    fragments = [{"title": "Test", "types": [], "base_epoch": 1000000, "end_epoch": 1000300, "turns": turns}]
    groups = build_gcf_groups("evt-006", 1000000, fragments, 8, 100)
    msgs = groups[0]["conversation_list"]
    assert len(msgs) == 1
    assert msgs[0]["sender"] == "unified_001"


def test_build_gcf_user_details():
    """user_details includes all normalized speakers with correct structure."""
    turns = [
        {"speaker_label": "user", "content": "hi", "offset_seconds": 0, "absolute_epoch": 1000000},
        {"speaker_label": "unified_001", "content": "hey", "offset_seconds": 1, "absolute_epoch": 1000001},
    ]
    fragments = [{"title": "T", "types": [], "base_epoch": 1000000, "end_epoch": 1000300, "turns": turns}]
    groups = build_gcf_groups("evt-007", 1000000, fragments, 8, 100)
    ud = groups[0]["conversation_meta"]["user_details"]
    assert "user_main" in ud
    assert ud["user_main"]["full_name"] == "主用户"
    assert ud["user_main"]["custom_role"] == "记录者"
    assert "unified_001" in ud
    assert ud["unified_001"]["role"] == "user"


def test_build_gcf_message_id_format():
    """Message IDs use correct format for non-split events."""
    fragments = [{"title": "T", "types": [], "base_epoch": 1000000, "end_epoch": 1000300, "turns": _make_turns(2)}]
    groups = build_gcf_groups("evt-008", 1000000, fragments, 8, 100)
    assert groups[0]["conversation_list"][0]["message_id"] == "evt-008_0"
    assert groups[0]["conversation_list"][1]["message_id"] == "evt-008_1"


# --- Integration tests ---


def test_convert_event_full_pipeline():
    """Integration test: raw event dict -> list of GCF dicts."""
    event = {
        "meta": {
            "user_id": "79ef7f17",
            "basic_event_id": "test-event-001",
            "basic_start_time": 1000000,
            "basic_end_time": 1000600,
        },
        "object": {
            "basic_transcript": """[Fragment 1: 1000000 - 1000300]
标题: Morning Chat
类型: social

[00:00][user]: 早上好
[00:05][unified_001]: 你好啊
[00:10][背景音]: 鸟叫声

[Fragment 2: 1000300 - 1000600]
标题: Work Discussion
类型: career

[00:00][User]: 今天的任务是什么
[00:05][unified_001]: 写代码""",
        },
    }
    groups = convert_event(event, split_frag_threshold=8, split_turn_threshold=100)
    assert len(groups) == 1  # 2 frags < 8, 4 valid turns < 100
    gcf = groups[0]
    assert gcf["conversation_meta"]["group_id"] == "test-event-001"
    assert gcf["conversation_meta"]["tags"] == ["social"]  # from first fragment
    # Background speaker filtered out
    assert len(gcf["conversation_list"]) == 4
    # user and User both normalized
    senders = [m["sender"] for m in gcf["conversation_list"]]
    assert senders.count("user_main") == 2
    assert senders.count("unified_001") == 2


def test_convert_event_empty_transcript():
    """Events with empty transcripts return empty list."""
    event = {
        "meta": {"user_id": "x", "basic_event_id": "empty-001", "basic_start_time": 0, "basic_end_time": 0},
        "object": {"basic_transcript": ""},
    }
    groups = convert_event(event)
    assert groups == []


def test_convert_event_passive_only():
    """Events with only passive media fragments return empty list."""
    event = {
        "meta": {"user_id": "x", "basic_event_id": "passive-001", "basic_start_time": 0, "basic_end_time": 0},
        "object": {"basic_transcript": """[Fragment 1: 1000000 - 1000300]
标题: 收听播客
类型: interest

(被动媒体，转录内容已略过)"""},
    }
    groups = convert_event(event)
    assert groups == []
