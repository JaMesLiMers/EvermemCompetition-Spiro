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
    "basic_transcript": "原始转录文本"
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
| `basic_transcript` | string | 原始转录文本，按 fragment 分隔，含时间戳和说话人标注 |
