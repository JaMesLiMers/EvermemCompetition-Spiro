"""Replace generic speaker IDs with mock Chinese names in basic_events JSON.

V2: Global role consistency + per-event generic ID randomization + edge case handling.

Rules:
- Family roles (丈夫/妻子/母亲 etc.) → globally consistent names
- Colleague roles → hash-based consistent name per specific role
- unified_XXX, SPEAKER_XX, unknown → per-event unique names (hash-based)
- user/用户/User → keep as-is (main user)
- Already named speakers → keep as-is
- Media/background labels → keep as-is
"""

import hashlib
import json
import re
import sys
from pathlib import Path

# ── Name pools ──────────────────────────────────────────────────────────────

MALE_NAMES = [
    "林浩",
    "陈志远",
    "赵建国",
    "周文博",
    "孙大伟",
    "马俊杰",
    "朱海涛",
    "胡晓明",
    "郭子轩",
    "何天宇",
    "罗永强",
    "梁家豪",
    "宋明辉",
    "唐国庆",
    "韩文杰",
    "冯志豪",
    "董建华",
    "程国强",
    "曹明阳",
    "邓世杰",
    "许振华",
    "彭志刚",
    "曾繁荣",
    "肖俊德",
    "田宇翔",
    "潘伟杰",
    "袁正刚",
    "蔡恒远",
    "蒋鑫磊",
    "余振宇",
    "于泽宇",
    "叶浩然",
    "夏培宇",
    "钟天瑞",
    "汪海波",
    "邹立诚",
    "石正轩",
    "任长风",
    "姜远帆",
    "段文昊",
    "雷鸣远",
    "龚奕辰",
    "史可为",
    "贺天成",
    "顾明哲",
    "毛凯旋",
    "薛博远",
    "侯振飞",
    "邵宏达",
    "孟繁星",
    "龙腾飞",
    "万里鹏",
    "江泽民",
    "严振邦",
]

FEMALE_NAMES = [
    "苏蕊",
    "王秀兰",
    "张丽萍",
    "赵婉如",
    "刘雅琴",
    "杨秋月",
    "黄雨薇",
    "周晓蝶",
    "吴雪莲",
    "徐芷若",
    "孙紫涵",
    "马怡然",
    "朱雨晴",
    "胡晓晨",
    "郭彩虹",
    "何清怡",
    "罗诗涵",
    "梁婉婷",
    "宋慧琳",
    "唐瑶瑶",
    "韩梦洁",
    "冯紫萱",
    "董晓薇",
    "程思雅",
    "曹雨欣",
    "邓雅芳",
    "许清蓉",
    "彭薇薇",
    "曾柔嘉",
    "肖蓉蓉",
    "田蜜儿",
    "潘若曦",
    "袁诗圆",
    "蔡欣怡",
    "蒋玲珑",
    "余思怡",
    "于雨萌",
    "叶婷婷",
    "夏荷韵",
    "钟灵秀",
    "汪洁雅",
    "邹若萱",
    "石慧敏",
    "任晓月",
    "姜月华",
    "段瑛瑛",
    "雷洁琼",
    "龚莹莹",
    "史佳怡",
    "贺兰芝",
    "顾雅君",
    "毛芸菲",
    "薛雯雯",
    "侯琳娜",
]

NEUTRAL_NAMES = [
    "陈宇轩",
    "林安然",
    "沈逸然",
    "方正舟",
    "钱远程",
    "顾一白",
    "苏晨风",
    "温以良",
    "卫清风",
    "季安然",
    "秦若越",
    "楚风歌",
    "项子阳",
    "慕清远",
    "柏长舟",
    "云天翼",
    "齐清风",
    "祁致远",
    "景澄明",
    "明远志",
    "凤鸣歌",
    "清泉石",
    "天明朗",
    "晨曦阳",
    "安若辰",
    "白若愚",
    "池云起",
    "邸和风",
]

# ── Fixed global mappings for family/recurring roles ────────────────────────

# The user's core recurring people get FIXED names across all events.
# Key insight: many different role labels refer to the same person.

# Husband/male partner of the user
_HUSBAND_KEYWORDS = [
    "丈夫",
    "男性伴侣",
    "男伴",
    "准爸爸",
    "男朋友",
    "男性同伴",
    "男主人",
    "家庭男主人",
]
HUSBAND_NAME = "林浩"  # Fixed across all events

# Wife/female partner of the user
_WIFE_KEYWORDS = [
    "妻子",
    "女性伴侣",
    "女伴",
    "准妈妈",
    "女朋友",
    "女性同伴",
    "女主人",
    "家庭女主人",
    "孩子母亲",
]
WIFE_NAME = "苏蕊"  # Fixed across all events

# Generic "伴侣" (ambiguous gender) - could be either
_PARTNER_KEYWORDS_EXACT = [
    "伴侣",
    "用户伴侣",
    "配偶",
]

# Mother / female elder
_MOTHER_KEYWORDS = ["母亲", "外婆", "祖母", "外祖母", "奶奶"]
MOTHER_NAME = "王秀兰"

# Father / male elder
_FATHER_KEYWORDS = ["父亲", "外公", "祖父", "岳父"]
FATHER_NAME = "赵建国"

# ── Skip / user / named detection ───────────────────────────────────────────

MAIN_USER_ALIASES = {"user", "用户", "User"}

SKIP_KEYWORDS = frozenset(
    [
        "背景",
        "环境",
        "Media",
        "音效",
        "音频",
        "Device",
        "GPS",
        "Music",
        "Background",
        "END",
        "ALL",
        "N/A",
        "Doubao",
        "被动媒体",
        "视频背景",
        "AI助手",
        "AI旁白",
        "AI语音",
        "车辆系统",
        "导航",
        "环境音",
        "背景音",
        "广播",
        "门禁",
        "反派",
    ]
)

NAMED_SPEAKERS = frozenset(
    [
        "Bella",
        "Li Jingchen",
        "Li_Jincan",
        "Li_Yiming",
        "Little Liu",
        "Marine",
        "Pang_Ge",
        "Child",
        "Elder",
        "Grandma",
        "Husband",
        "Mother",
        "Male",
        "Colleague",
        "Colleague_Female",
        "Product Manager",
        "Drew",
        "Lucy",
        "Gru",
        "Balthazar",
        "zhang_san",
    ]
)

# Generic ID patterns (all variations)
GENERIC_ID_RE = re.compile(
    r"^(unified_\d+|SPEAKER_\d+)"
    r"(?:\s*\([^)]*\))?"  # optional (annotation)
    r"(?:/[男女未知]+)?"  # optional /男 /女 /未知
    r"(?:/男孩)?"  # /男孩
    r"$"
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _hash_to_idx(key: str, pool_size: int) -> int:
    """Deterministic hash → index into a name pool."""
    h = int(hashlib.md5(key.encode()).hexdigest(), 16)
    return h % pool_size


# Names reserved for family — must NOT appear in generic/role pools
_RESERVED_NAMES = frozenset(
    [
        HUSBAND_NAME,
        WIFE_NAME,
        MOTHER_NAME,
        FATHER_NAME,
        "张丽萍",
        "林小禾",
    ]
)


def _pick_by_hash(key: str, gender: str) -> str:
    """Pick a name deterministically based on key + gender, excluding reserved names."""
    if gender == "male":
        pool = [n for n in MALE_NAMES if n not in _RESERVED_NAMES]
    elif gender == "female":
        pool = [n for n in FEMALE_NAMES if n not in _RESERVED_NAMES]
    else:
        pool = [n for n in NEUTRAL_NAMES if n not in _RESERVED_NAMES]
    return pool[_hash_to_idx(key, len(pool))]


def is_skip_label(label: str) -> bool:
    # "被动媒体内容" prefix always skipped regardless of suffix
    if label.startswith("被动媒体内容"):
        return True
    return any(kw in label for kw in SKIP_KEYWORDS)


def is_main_user(label: str) -> bool:
    return label in MAIN_USER_ALIASES


def is_named_speaker(label: str) -> bool:
    return label in NAMED_SPEAKERS


def is_generic_id(label: str) -> bool:
    return bool(GENERIC_ID_RE.match(label)) or label.lower() == "unknown"


def get_gender_from_label(label: str) -> str:
    if "/男" in label or "(男" in label or "/男性" in label or "男孩" in label:
        return "male"
    if "/女" in label or "(女" in label or "/女性" in label:
        return "female"
    for kw in _HUSBAND_KEYWORDS + _FATHER_KEYWORDS:
        if kw in label:
            return "male"
    for kw in _WIFE_KEYWORDS + _MOTHER_KEYWORDS:
        if kw in label:
            return "female"
    return "unknown"


def _contains_any(label: str, keywords: list[str]) -> bool:
    return any(kw in label for kw in keywords)


def _classify_family_role(label: str) -> str | None:
    """Return a fixed family role key, or None if not a family label."""
    # Check wife/husband FIRST since labels like "家庭成员（妻子/伴侣）/孩子母亲"
    # contain "母亲" but actually refer to the wife/partner.
    has_wife_kw = _contains_any(label, _WIFE_KEYWORDS)
    has_husband_kw = _contains_any(label, _HUSBAND_KEYWORDS)
    has_mother_kw = _contains_any(label, _MOTHER_KEYWORDS)
    has_father_kw = _contains_any(label, _FATHER_KEYWORDS)

    # If label has both partner AND parent keywords, partner takes priority
    if has_wife_kw or has_husband_kw:
        if has_wife_kw and has_husband_kw:
            # Ambiguous, use gender
            gender = get_gender_from_label(label)
            return "wife" if gender == "female" else "husband"
        if has_wife_kw:
            return "wife"
        return "husband"

    # Pure parent references (no partner keywords mixed in)
    if has_mother_kw:
        return "mother"
    if has_father_kw:
        return "father"

    # Generic "伴侣" - determine gender from context
    for kw in _PARTNER_KEYWORDS_EXACT:
        if kw in label:
            gender = get_gender_from_label(label)
            if gender == "male":
                return "husband"
            elif gender == "female":
                return "wife"
            return "partner_ambiguous"

    # Check for generic family labels
    if _contains_any(label, ["长辈", "家庭长辈"]):
        gender = get_gender_from_label(label)
        if gender == "female":
            return "mother"
        elif gender == "male":
            return "father"
        return "elder"

    if _contains_any(label, ["家庭成员", "家人", "亲属", "亲友"]):
        gender = get_gender_from_label(label)
        if gender == "male":
            return "family_male"
        elif gender == "female":
            return "family_female"
        return "family_neutral"

    # Children
    if _contains_any(label, ["孩子", "儿童", "学龄", "婴儿"]):
        return "child"

    return None


# Fixed family name mapping — simple, fixed relationship tag
FAMILY_NAME_MAP = {
    "husband": (HUSBAND_NAME, "丈夫"),
    "wife": (WIFE_NAME, "妻子"),
    "mother": (MOTHER_NAME, "母亲"),
    "father": (FATHER_NAME, "父亲"),
    "partner_ambiguous": (HUSBAND_NAME, "丈夫"),
    "elder": (MOTHER_NAME, "母亲"),
    "family_male": (FATHER_NAME, "家人"),
    "family_female": ("张丽萍", "家人"),
    "family_neutral": ("张丽萍", "家人"),
    "child": ("林小禾", "孩子"),
}


def _clean_role_text(role: str) -> str:
    """Clean up role description: deduplicate, remove gender-only parts, trim."""
    parts = role.split("/")
    # Remove gender-only parts
    parts = [p.strip() for p in parts if p.strip() not in ("男", "女", "男性", "女性", "未知")]
    # Deduplicate while preserving order
    seen = set()
    deduped = []
    for p in parts:
        if p not in seen:
            seen.add(p)
            deduped.append(p)
    # Limit to 3 most meaningful parts
    if len(deduped) > 3:
        deduped = deduped[:3]
    return "/".join(deduped) if deduped else role


def _extract_embedded_name(label: str) -> str | None:
    """Check if the label contains an embedded English name like (gru), (drew)."""
    m = re.search(r"\((\w+)\)", label)
    if m:
        name = m.group(1)
        # Known character names
        name_map = {
            "gru": "Gru",
            "drew": "Drew",
            "lu_si": "Lucy",
        }
        return name_map.get(name.lower())
    return None


# ── Role keywords for detection ─────────────────────────────────────────────

ROLE_KEYWORDS = frozenset(
    [
        "同事",
        "朋友",
        "配偶",
        "丈夫",
        "妻子",
        "长辈",
        "陌生人",
        "家人",
        "母亲",
        "父亲",
        "奶奶",
        "爷爷",
        "姐姐",
        "哥哥",
        "弟弟",
        "妹妹",
        "老板",
        "店员",
        "服务员",
        "乘客",
        "司机",
        "路人",
        "游客",
        "顾客",
        "受访",
        "访谈",
        "产品经理",
        "设计师",
        "工程师",
        "研究员",
        "负责人",
        "创始人",
        "团队",
        "上级",
        "导师",
        "助理",
        "运营",
        "面试",
        "雇主",
        "甲方",
        "驾驶员",
        "伴侣",
        "家庭成员",
        "家庭",
        "被拍摄",
        "被摄录",
        "被观察",
        "被记录",
        "被访谈",
        "Spiro",
        "Prompt",
        "UI",
        "AI产品",
        "AI研发",
        "AI技术",
        "软件",
        "雷达",
        "视觉",
        "创业",
        "合伙",
        "特警",
        "宠物",
        "摄影",
        "亲友",
        "亲属",
        "亲密",
        "核心朋友",
        "联合创始人",
        "合作伙伴",
        "技术合伙人",
        "测试",
        "前端",
        "算法",
        "QA",
        "HR",
        "行政",
        "CEO",
        # Additional roles found in edge case scan
        "顾问",
        "主创",
        "讨论者",
        "规划者",
        "维修",
        "技术员",
        "服务人员",
        "领队",
        "倾听者",
        "倾诉者",
        "送行者",
        "猫主人",
        "安保",
        "巡逻",
        "嘉宾",
        "综艺",
        "孩子",
        "儿童",
        "学龄",
        "同伴",
        "熟人",
        "开发",
        "说话人",
        "参与者",
    ]
)


def is_role_description(label: str) -> bool:
    return any(kw in label for kw in ROLE_KEYWORDS)


# ── Main processing ─────────────────────────────────────────────────────────


def _map_speaker(label: str, event_id: str, per_event_counter: dict) -> str | None:
    """Map a single speaker label to a new label. Returns None to keep as-is."""
    if is_main_user(label):
        return "用户" if label != "用户" else None
    if is_skip_label(label):
        return None
    if is_named_speaker(label):
        return None

    # Bare gender markers like "/男" "/女" - treat as generic
    if label in ("/男", "/女", "男", "女"):
        gender = "male" if "男" in label else "female"
        hash_key = f"{event_id}::bare_gender::{label}"
        return _pick_by_hash(hash_key, gender)

    # Check for embedded English name in generic IDs like "unified_000 (gru)"
    embedded = _extract_embedded_name(label)
    if embedded:
        return embedded

    # Generic IDs: per-event unique name via hash
    if is_generic_id(label):
        gender = get_gender_from_label(label)
        # Use event_id + label as hash key for uniqueness across events
        hash_key = f"{event_id}::{label}"
        name = _pick_by_hash(hash_key, gender)
        # Avoid collisions within same event
        used = per_event_counter.setdefault("_used_names", set())
        attempt = 0
        while name in used and attempt < 20:
            hash_key = f"{event_id}::{label}::retry{attempt}"
            name = _pick_by_hash(hash_key, gender)
            attempt += 1
        used.add(name)
        return name

    # Family roles: globally consistent name + fixed simple relationship
    family_key = _classify_family_role(label)
    if family_key:
        name, fixed_role = FAMILY_NAME_MAP[family_key]
        return f"{name}/{fixed_role}"

    # Professional/other role descriptions: hash-based consistent name
    if is_role_description(label):
        gender = get_gender_from_label(label)
        # Use role label itself as hash key → same role globally = same name
        hash_key = f"role::{label}"
        name = _pick_by_hash(hash_key, gender)
        role = _clean_role_text(label)
        return f"{name}/{role}"

    # Fallback: keep as-is
    return None


def process_event_transcript(transcript: str, event_id: str) -> str:
    """Process a single event's transcript, replacing speaker labels."""
    # Collect all unique speakers
    # Pattern 1: [HH:MM][Speaker]: content
    # Pattern 2: [Speaker]: content (no timestamp, at line start)
    ts_pattern = re.compile(r"\[\d{2}:\d{2}\]\[([^\]]+)\]:")
    no_ts_pattern = re.compile(r"^\[([^\]\d][^\]]*)\]:", re.MULTILINE)

    all_speakers = set()
    for m in ts_pattern.finditer(transcript):
        all_speakers.add(m.group(1))
    for m in no_ts_pattern.finditer(transcript):
        all_speakers.add(m.group(1))

    if not all_speakers:
        return transcript

    # Build mapping
    per_event_counter = {}
    mapping = {}
    for speaker in sorted(all_speakers):
        new_label = _map_speaker(speaker, event_id, per_event_counter)
        if new_label:
            mapping[speaker] = new_label

    if not mapping:
        return transcript

    # Apply replacements (sort by length desc to avoid partial matches)
    result = transcript
    for old_label, new_label in sorted(mapping.items(), key=lambda x: -len(x[0])):
        escaped = re.escape(old_label)
        result = re.sub(rf"\[{escaped}\]:", f"[{new_label}]:", result)

    return result


def main():
    input_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data/basic_events_79ef7f17.json")
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path

    print(f"Reading {input_path}...")
    with open(input_path, encoding="utf-8") as f:
        events = json.load(f)

    print(f"Processing {len(events)} events...")
    modified_count = 0
    for i, event in enumerate(events):
        transcript = event["object"].get("basic_transcript", "")
        if not transcript:
            continue

        event_id = event["meta"]["basic_event_id"]
        new_transcript = process_event_transcript(transcript, event_id)
        if new_transcript != transcript:
            event["object"]["basic_transcript"] = new_transcript
            modified_count += 1

        if (i + 1) % 100 == 0:
            print(f"  [{i + 1}/{len(events)}] processed...")

    print(f"\nModified {modified_count}/{len(events)} events")
    print(f"Writing to {output_path}...")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(events, f, ensure_ascii=False, indent=2)
    print("Done!")


if __name__ == "__main__":
    main()
