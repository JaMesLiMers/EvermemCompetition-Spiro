# 基础事件数据（Basic Events）

## 数据格式

数据文件为 JSON 数组，共 832 条记录，每条包含 `meta`（元信息）和 `object`（事件内容）两部分：

```json
{
  "meta": {
    "user_id":          "用户 ID",
    "basic_event_id":   "事件唯一标识",
    "basic_start_time": "事件开始时间（epoch 秒）",
    "basic_end_time":   "事件结束时间（epoch 秒）"
  },
  "object": {
    "basic_transcript": "规范化后的转录文本"
  }
}
```

## 字段说明

### meta

| 字段 | 类型 | 说明 |
|------|------|------|
| `user_id` | string | 用户唯一标识（UUID） |
| `basic_event_id` | string | 事件唯一标识（UUID） |
| `basic_start_time` | number | 事件开始时间，Unix epoch 秒 |
| `basic_end_time` | number | 事件结束时间，Unix epoch 秒 |

### object

| 字段 | 类型 | 说明 |
|------|------|------|
| `basic_transcript` | string | 规范化后的转录文本（见下方格式说明） |

## 转录文本格式 (basic_transcript)

经过 `scripts/normalize_speakers.py` 规范化后，转录文本统一为以下格式：

### Fragment 结构

```
[Fragment N: YYYY-MM-DD HH:MM - YYYY-MM-DD HH:MM]
标题: 对话标题
类型: career, social, home, ...

[说话人1]: 说话内容
[用户]: 说话内容
[同事/朋友]: 说话内容
```

### 说话人标签

| 标签类型 | 格式 | 说明 |
|----------|------|------|
| 主用户 | `[用户]` | 录音设备持有者 |
| 通用说话人 | `[说话人1]`, `[说话人2]`, ... | 按出场顺序编号，每个事件独立编号 |
| 通用说话人+性别 | `[说话人1/男]`, `[说话人2/女]` | 带性别标注 |
| 有意义角色 | `[同事/朋友]`, `[伴侣]`, `[访谈主持人]` 等 | 保留原始角色描述 |

### 对话行格式

所有对话行统一为 Format B（无时间戳）：

```
[说话人标签]: 说话内容
```

### 非对话行

转录文本中可能包含以下非对话行（pipeline 解析时自动跳过）：

- Fragment 头: `[Fragment N: ...]`
- 标题/类型: `标题: ...` / `类型: ...`
- 元数据: `【完整转录与总结】` 等
- 环境描述: `[安静环境] [音质清晰]` 等
- 被动媒体: `被动媒体，转录内容已略过`

## 规范化脚本

```bash
python scripts/normalize_speakers.py data/basic_events_79ef7f17.json
```

详见 `scripts/normalize_speakers.py` 注释。
