# Chatterbox TTS HTTP API 接口文档

## 1. 服务概述

Chatterbox TTS HTTP服务是基于多语言语音合成模型的语音生成服务接口，提供了文本转语音的功能，支持23种语言，并提供了丰富的任务管理接口。

## 2. 快速开始

### 2.1 安装依赖

```bash
pip install -r requirements.txt
```

### 2.2 启动服务

```bash
python server.py --host 0.0.0.0 --port 8001 --device cpu
```

### 2.3 主要参数说明

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| --host | str | 0.0.0.0 | 服务监听地址 |
| --port | int | 8001 | 服务监听端口 |
| --model_name | str | chatterbox-mtl | TTS模型名称 |
| --model_path | str | None | TTS模型路径 |
| --device | str | cuda | 设备类型（cuda/cpu） |
| --max_concurrent_tasks | int | 10 | 最大并发任务数 |
| --db_pool_size | int | 10 | 数据库连接池大小 |
| --tts_thread_pool_size | int | 4 | TTS处理线程池大小 |
| --temp_dir | str | temp_dir/ | 临时文件目录 |
| --output_dir | str | output_dir/ | 音频输出目录 |

## 3. 支持的语言

Chatterbox TTS支持以下23种语言：

| 语言代码 | 语言名称 |
|----------|----------|
| zh | 中文 |
| en | 英语 |
| es | 西班牙语 |
| fr | 法语 |
| de | 德语 |
| it | 意大利语 |
| pt | 葡萄牙语 |
| ja | 日语 |
| ko | 韩语 |
| hi | 印地语 |
| ar | 阿拉伯语 |
| ru | 俄语 |
| tr | 土耳其语 |
| nl | 荷兰语 |
| sv | 瑞典语 |
| da | 丹麦语 |
| no | 挪威语 |
| fi | 芬兰语 |
| pl | 波兰语 |
| el | 希腊语 |
| he | 希伯来语 |
| ms | 马来语 |
| sw | 斯瓦希里语 |

## 4. API接口列表

### 4.1 单任务提交接口

#### 4.1.1 文本转语音任务提交

**接口地址**：`POST /submit_tts_task`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| text | string | 是 | 要合成的文本内容 |
| language_id | string | 否 | 语言代码，默认zh |
| audio_prompt | file | 否 | 参考音频文件 |
| audio_prompt_path | string | 否 | 参考音频文件路径 |
| exaggeration | float | 否 | 语音表达度控制 (0.25-2.0，默认0.5) |
| temperature | float | 否 | 生成随机性控制 (0.05-5.0，默认0.8) |
| cfg_weight | float | 否 | CFG权重控制 (0.2-1.0，默认0.5) |
| seed_num | int | 否 | 随机种子 (0为随机，默认0) |
| callback_url | string | 否 | 任务完成后回调URL |
| app_id | string | 否 | 应用ID |
| biz_type | string | 否 | 业务类型 |
| biz_unique_id | string | 否 | 业务唯一ID |
| audio_format | string | 否 | 音频格式，默认wav |
| sample_rate | int | 否 | 采样率，默认22050 |

**返回结果**：

```json
{
  "code": 0,
  "msg": "任务提交成功",
  "task_id": "task_id_value",
  "output_url": "/output/task_id_value.wav"
}
```

#### 4.1.2 使用预定义参考音频提交任务

**接口地址**：`POST /submit_tts_task_with_predefined_audio`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| text | string | 是 | 要合成的文本内容 |
| language_id | string | 否 | 语言代码，默认zh |
| predefined_audio_filename | string | 是 | 预定义参考音频文件名 |
| exaggeration | float | 否 | 语音表达度控制 (0.25-2.0，默认0.5) |
| temperature | float | 否 | 生成随机性控制 (0.05-5.0，默认0.8) |
| cfg_weight | float | 否 | CFG权重控制 (0.2-1.0，默认0.5) |
| seed_num | int | 否 | 随机种子 (0为随机，默认0) |
| callback_url | string | 否 | 任务完成后回调URL |
| app_id | string | 否 | 应用ID |
| biz_type | string | 否 | 业务类型 |
| biz_unique_id | string | 否 | 业务唯一ID |

**返回结果**：

```json
{
  "code": 0,
  "msg": "任务提交成功",
  "task_id": "task_id_value",
  "output_url": "/output/task_id_value.wav",
  "predefined_audio_used": "path/to/audio.wav"
}
```

### 4.2 任务查询接口

#### 4.2.1 查询任务状态

**接口地址**：`GET /get_tts_status`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| task_id | string | 是 | 任务ID |

**返回结果**：

```json
{
  "code": 0,
  "task_id": "task_id_value",
  "status": "processing",
  "progress": 0.5,
  "updated_time": 1620000000,
  "callback_status": "pending",
  "error_msg": null
}
```

#### 4.2.2 查询任务结果

**接口地址**：`GET /get_tts_result`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| task_id | string | 是 | 任务ID |

**返回结果**：

```json
{
  "code": 0,
  "status": "completed",
  "task_id": "task_id_value",
  "callback_status": "success",
  "progress": 1.0,
  "result": {
    "output_path": "/app/output_dir/task_id_value.wav",
    "output_url": "/output/task_id_value.wav",
    "audio_format": "wav",
    "sample_rate": 22050,
    "text_content": "测试文本",
    "language_id": "zh"
  }
}
```

#### 4.2.3 根据业务ID查询任务

**接口地址**：`GET /get_tts_by_biz_id`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| biz_unique_id | string | 否 | 业务唯一ID |
| app_id | string | 否 | 应用ID |
| biz_type | string | 否 | 业务类型 |

**注意：** 至少需要提供 `biz_unique_id` 或 `app_id` 中的一个参数

**返回结果**：

```json
{
  "code": 0,
  "msg": "查询任务详情成功",
  "task": {
    "task_id": "task_id_value",
    "text_content": "测试文本",
    "language_id": "zh",
    "status": "completed",
    "progress": 1.0,
    "created_time": 1620000000,
    "updated_time": 1620000000,
    "callback_status": "success",
    "app_id": "my_app",
    "biz_type": "speech_synthesis",
    "biz_unique_id": "request_001"
  }
}
```

### 4.3 任务操作接口

#### 4.3.1 取消任务

**接口地址**：`POST /cancel_tts_task`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| task_id | string | 是 | 任务ID |

**返回结果**：

```json
{
  "code": 0,
  "msg": "任务取消成功"
}
```

#### 4.3.2 删除任务

**接口地址**：`DELETE /delete_tts_task`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| task_id | string | 是 | 任务ID |

**返回结果**：

```json
{
  "code": 0,
  "msg": "任务删除成功"
}
```

### 4.4 音频下载接口

#### 4.4.1 下载生成的音频

**接口地址**：`GET /download_tts_audio`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| task_id | string | 是 | 任务ID |

**返回结果**：

直接返回生成的音频文件

### 4.5 任务列表接口

#### 4.5.1 查询任务列表

**接口地址**：`GET /list_tts_tasks`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页数量，默认10，最大100 |
| status | string | 否 | 任务状态过滤 |
| app_id | string | 否 | 应用ID过滤 |
| biz_type | string | 否 | 业务类型过滤 |
| language_id | string | 否 | 语言过滤 |

**返回结果**：

```json
{
  "code": 0,
  "msg": "查询任务列表成功",
  "tasks": [
    {
      "task_id": "task_id_value",
      "text_content": "测试文本...",
      "language_id": "zh",
      "status": "completed",
      "progress": 1.0,
      "created_time": 1620000000,
      "updated_time": 1620000000,
      "callback_status": "success"
    },
    ...
  ],
  "total": 100,
  "page": 1,
  "limit": 10
}
```

### 4.6 系统接口

#### 4.6.1 健康检查

**接口地址**：`GET /health`

**返回结果**：

```json
{
  "status": "healthy",
  "service": "TTS",
  "version": "1.0.0"
}
```

#### 4.6.2 获取支持的语言

**接口地址**：`GET /supported_languages`

**返回结果**：

```json
{
  "code": 0,
  "languages": ["zh", "en", "es", ...],
  "total": 23
}
```

#### 4.6.3 列出预定义音频文件

**接口地址**：`GET /list_predefined_audios`

**返回结果**：

```json
{
  "code": 0,
  "msg": "获取预定义音频列表成功",
  "audios": [
    {
      "filename": "sample.wav",
      "file_path": "/app/data/sample.wav",
      "size": 1024000
    },
    ...
  ]
}
```

### 4.7 高级功能接口

#### 4.7.1 批量操作接口

**接口地址**：`POST /batch_tts_operation`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| operation | string | 是 | 操作类型：submit/cancel/delete |
| text_list | string | 否 | 文本列表，JSON格式：[{"text":"xxx","language_id":"zh"}] |
| task_ids | string | 否 | 任务ID列表，逗号分隔 |
| callback_url | string | 否 | 任务完成后回调URL |
| app_id | string | 否 | 应用ID |
| biz_type | string | 否 | 业务类型 |

**返回结果**：

```json
{
  "code": 0,
  "msg": "批量操作成功",
  "results": [
    {
      "code": 0,
      "task_id": "task_id_value"
    },
    ...
  ]
}
```

#### 4.7.2 批量查询任务状态

**接口地址**：`POST /batch_get_tts_status`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| task_ids | string | 是 | 任务ID列表，逗号分隔 |

**返回结果**：

```json
{
  "code": 0,
  "msg": "批量查询任务状态完成",
  "results": [
    {
      "code": 0,
      "task_id": "task_id_value",
      "status": "completed",
      "progress": 1.0,
      "updated_time": 1620000000,
      "callback_status": "success"
    },
    ...
  ]
}
```

#### 4.7.3 批量查询任务结果

**接口地址**：`POST /batch_get_tts_result`

**请求参数**：

| 参数名 | 类型 | 是否必填 | 说明 |
|--------|------|----------|------|
| task_ids | string | 是 | 任务ID列表，逗号分隔 |

**返回结果**：

```json
{
  "code": 0,
  "msg": "批量查询任务结果完成",
  "results": [
    {
      "code": 0,
      "task_id": "task_id_value",
      "status": "completed",
      "callback_status": "success",
      "result": {
        "output_url": "/output/task_id_value.wav"
      }
    },
    ...
  ]
}
```

## 5. 任务状态说明

| 状态值 | 说明 |
|--------|------|
| pending | 任务待处理 |
| processing | 任务处理中 |
| completed | 任务处理完成 |
| failed | 任务处理失败 |
| canceled | 任务已取消 |

## 6. 错误码说明

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1 | 参数错误 |
| 2 | 任务处理失败 |
| 3 | 任务已取消 |
| 4 | 任务不存在 |
| 5 | 系统错误 |

## 7. 使用示例

### 7.1 单任务提交示例

**使用curl提交TTS任务：**
```bash
curl -X POST "http://localhost:8001/submit_tts_task" \
  -F "text=测试文本内容" \
  -F "language_id=zh"
```

**响应示例：**
```json
{
  "code": 0,
  "msg": "任务提交成功",
  "task_id": "c7f3a5b9-1234-5678-90ab-cdef12345678",
  "output_url": "/output/c7f3a5b9-1234-5678-90ab-cdef12345678.wav"
}
```

### 7.2 查询任务状态示例

**使用curl查询任务状态：**
```bash
curl -X GET "http://localhost:8001/get_tts_status?task_id=c7f3a5b9-1234-5678-90ab-cdef12345678"
```

**响应示例：**
```json
{
  "code": 0,
  "task_id": "c7f3a5b9-1234-5678-90ab-cdef12345678",
  "status": "processing",
  "progress": 0.3,
  "updated_time": 1704441600,
  "callback_status": "pending",
  "error_msg": null
}
```

### 7.3 下载生成的音频示例

**使用curl下载音频：**
```bash
curl -O "http://localhost:8001/download_tts_audio?task_id=c7f3a5b9-1234-5678-90ab-cdef12345678"
```

### 7.4 批量提交任务示例

**使用curl批量提交任务：**
```bash
curl -X POST "http://localhost:8001/batch_tts_operation" \
  -F "operation=submit" \
  -F "text_list=[{\"text\":\"测试文本1\",\"language_id\":\"zh\"},{\"text\":\"测试文本2\",\"language_id\":\"en\"}]"
```

**响应示例：**
```json
{
  "code": 0,
  "msg": "批量操作成功",
  "results": [
    {
      "code": 0,
      "task_id": "task_001"
    },
    {
      "code": 0,
      "task_id": "task_002"
    }
  ]
}
```

## 8. 最佳实践

1. **合理设置并发数**：根据服务器配置调整 `max_concurrent_tasks` 参数
2. **使用回调机制**：对于批量任务或长时间处理的任务，建议使用回调URL获取结果
3. **文本长度控制**：单条文本建议不超过300个字符
4. **使用业务唯一ID**：为每个任务设置唯一的业务ID，便于后续查询和管理
5. **监控任务状态**：定期查询任务状态，及时处理失败任务
6. **使用批量接口**：批量操作比单次操作效率更高
7. **合理设置模型参数**：根据需求调整exaggeration、temperature等参数
8. **使用支持的语言**：确保使用支持的语言代码，避免无效请求

## 9. 常见问题

### 9.1 任务处理失败怎么办？
- 检查输入文本是否超过最大长度限制
- 检查语言代码是否正确
- 查看错误信息，根据错误提示调整参数
- 检查服务器资源是否充足

### 9.2 如何提高合成质量？
- 调整exaggeration参数控制语音表达力
- 调整temperature参数控制生成随机性
- 调整cfg_weight参数控制生成引导强度
- 使用合适的参考音频

### 9.3 如何提高处理速度？
- 减少并发任务数
- 使用GPU加速
- 减少单条文本长度
- 使用批量接口

### 9.4 支持哪些音频格式？
目前主要支持wav格式，其他格式将在后续版本支持

## 10. 版本历史

| 版本 | 日期 | 主要变更 |
|------|------|----------|
| 1.0.0 | 2026-01-05 | 初始版本，支持基本TTS功能和API |
| 1.1.0 | 2026-01-10 | 增加批量操作功能，支持回调机制 |
| 1.2.0 | 2026-01-15 | 增加业务ID查询，完善API文档 |

## 11. 联系方式

如遇问题，请联系技术支持：
- 邮箱：support@chatterbox-tts.com
- 文档：https://docs.chatterbox-tts.com
- GitHub：https://github.com/chatterbox-tts/chatterbox-tts

## 12. 许可证

本项目使用Apache License 2.0许可证
