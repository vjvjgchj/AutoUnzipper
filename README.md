# 自动解压工具：AutoUnzipper

## 项目概述

**AutoUnzipper** 是一个自动解压工具，用于监控指定的目录并解压其中的压缩文件。支持多种压缩文件格式，具备解压模式切换功能（平铺解压或分层解压），并通过钉钉通知解压结果。

---

## 功能特点

- **多种压缩格式支持**：支持 `.zip`、`.tar`、`.tar.gz`、`.tgz` 和 `.rar` 文件。
- **解压模式切换**：
  - **平铺解压（direct）**：将文件解压至其所在目录的上层目录。
  - **分层解压（nested）**：在上层目录创建与压缩文件同名的文件夹并解压。
- **自动删除原文件**：解压完成后自动删除原始压缩文件。
- **实时目录监控**：支持多个目录的实时监控。
- **钉钉通知**：解压完成后，通过钉钉 Webhook 发送通知，包含产品线、文件名、解压模式和解压状态等信息。

---



## 配置文件说明

配置文件 `config.yaml` 定义了需要监控的目录及其相关信息，示例如下：

```yaml
product_lines:
  - name: 产品线A
    watch_directories:
      - path: /path/to/monitor1
        extract_mode: direct
      - path: /path/to/monitor2
        extract_mode: nested
    notification:
      dingtalk:
        webhook_url: https://oapi.dingtalk.com/robot/send?access_token=YOUR_ACCESS_TOKEN
  - name: 产品线B
    watch_directories:
      - path: /path/to/monitor3
        extract_mode: nested
    notification:
      dingtalk:
        webhook_url: https://oapi.dingtalk.com/robot/send?access_token=ANOTHER_ACCESS_TOKEN
```

### 配置项说明

- `name`：产品线名称，用于钉钉通知显示。
- `watch_directories`：需要监控的目录列表，每个目录包含：
  - `path`：目录路径。
  - `extract_mode`：解压模式，可选 `direct` 或 `nested`。
- `notification`：
  - `dingtalk.webhook_url`：钉钉 Webhook 地址，用于发送解压通知。

---

## 使用方法

### 安装依赖

确保安装了所需的 Python 包，运行以下命令：

```bash
pip install -r requirements.txt
```

### 启动工具

直接运行主程序：

```bash
python auto_unzipper.py
```

---

## 代码功能解析

### 核心类：`AutoUnzipper`

#### 初始化方法 `__init__`

- **功能**：加载配置文件，初始化日志和支持的压缩格式。
- **主要逻辑**：
  - 加载 `config.yaml` 配置文件。
  - 定义支持的压缩文件扩展名与对应解压方法。

---

#### 文件处理：`process_file`

- **功能**：根据文件扩展名解压压缩文件并删除原文件。
- **主要逻辑**：
  1. 检查文件是否支持解压且未被标记为 `noextract`。
  2. 根据解压模式选择目标解压目录。
  3. 解压文件并删除原文件。
  4. 发送解压结果至钉钉。

---

#### 解压方法

| 方法              | 描述                          |
|-------------------|-------------------------------|
| `_unzip_file`     | 解压 `.zip` 文件              |
| `_untar_file`     | 解压 `.tar`、`.tar.gz`、`.tgz` 文件 |
| `_unrar_file`     | 解压 `.rar` 文件              |

---

#### 目录监控：`monitor_directories`

- **功能**：实时监控配置中指定的目录，当有新文件写入时触发解压。
- **实现**：
  - 使用 `inotify` 监听目录事件。
  - 对新文件进行解压处理。

---

#### 钉钉通知：`_send_dingtalk_message`

- **功能**：发送解压结果通知。
- **实现**：
  - 使用 `MarkdownTableWriter` 生成表格格式消息。
  - 调用钉钉 Webhook API 发送通知。

---

## 钉钉通知示例

成功示例：

| **产品线** | **文件名** | **解压模式** | **解压状态** |
|------------|------------|--------------|--------------|
| 产品线A    | example.zip | 平铺解压      | 成功         |

失败示例：

| **产品线** | **文件名** | **解压模式** | **解压状态** |
|------------|------------|--------------|--------------|
| 产品线A    | example.rar | 分层解压      | 失败: 错误信息|

---

## 日志示例

```plaintext
2024-12-06 10:00:00 - INFO: 正在监控目录: /path/to/monitor1 (产品线: 产品线A, 模式: direct)
2024-12-06 10:00:00 - INFO: 成功解压 /path/to/monitor1/example.zip
2024-12-06 10:00:00 - INFO: 删除原文件 /path/to/monitor1/example.zip
2024-12-06 10:00:00 - INFO: 钉钉通知: 200, 内容: {"errcode":0,"errmsg":"ok"}
2024-12-06 10:00:00 - ERROR: 解压 /path/to/monitor2/example.rar 失败: 文件损坏
```
