# BabelDOC WebUI

基于 [BabelDOC](https://github.com/funstory-ai/BabelDOC) 的 PDF 翻译 Web 界面，保留原文排版，支持双语对照。

## 功能

- 拖拽上传 PDF，支持批量翻译
- 双语版 / 单语版输出
- 水印版 / 无水印 / 两者都输出
- 支持多引擎：DeepSeek、Google Gemini、DeepL
- 自动提取术语表
- 玻璃拟态桌面风格界面
- 设置自动保存到浏览器

## 快速开始

### 1. 克隆

```bash
git clone https://github.com/dmxynts/BabelDOC-WebUI.git
cd BabelDOC-WebUI
```

### 2. 安装依赖

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 3. 配置

```bash
cp .env.example .env
```

编辑 `.env`，填入对应 API Key（至少配置一个引擎）。

### 4. 运行

```bash
python app.py
```

浏览器打开 `http://127.0.0.1:7860`。

## 配置项

| 环境变量 | 说明 |
|---|---|
| `DEEPSEEK_API_KEY` | DeepSeek API Key |
| `DEEPSEEK_MODEL` | DeepSeek 模型名，默认 `deepseek-chat` |
| `GOOGLE_API_KEY` | Google Gemini API Key |
| `GOOGLE_MODEL` | Gemini 模型名，默认 `gemini-2.0-flash` |
| `DEEPL_API_KEY` | DeepL API Key |
| `SOURCE_LANG` | 默认源语言，默认 `en-US` |
| `TARGET_LANG` | 默认目标语言，默认 `zh-CN` |
| `QPS` | 每秒请求数，默认 `4` |

配置也可在页面右侧面板中填写，会保存到浏览器本地。

## 技术栈

- **后端**: Python / FastAPI
- **前端**: Jinja2 / Tailwind CSS
- **翻译引擎**: BabelDOC
