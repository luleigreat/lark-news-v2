# Lark News V2

云端定时抓取 **AI Agent Payment** 和 **Web3 卡/U 卡** 领域资讯，AI 筛选翻译后通过 Lark Webhook 推送到群聊。

## 架构

```
每日任务:
  搜索 → 日期过滤 → AI 筛选 → Lark 推送 → 缓存到 .cache/daily/

每周任务:
  恢复每日缓存 + 搜索上周新闻 → 合并去重 → AI 重筛 Top 10 → Lark 推送 → 清理上周缓存
```

GitHub Actions 通过 `actions/cache` 在运行间持久化 `.cache/daily/` 目录。

## 推送计划

| 任务 | 定时触发 (北京时间) | 预期送达 | 每方向条数 |
|------|---------------------|----------|------------|
| 每日推送 | 每天 4:00 | ~9:00 前 | 最多 5 条 |
| 每周简报 | 周一 4:00 | ~9:00 前 | 最多 10 条 + 趋势 |

> GitHub Actions 免费 runner 常有数小时排队延迟，故 cron 设为凌晨 4 点。

## 快速开始

### 1. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入实际值
```

| 变量 | 说明 | 必填 |
|------|------|------|
| `LARK_WEBHOOK_URL` | Lark 机器人 Webhook | ✅ |
| `OPENAI_API_KEY` | AI 筛选/翻译/摘要 | ✅ |
| `OPENAI_BASE_URL` | 兼容 API 地址 | 可选 |
| `OPENAI_MODEL` | 模型名 | 可选 |
| `NEWSAPI_KEY` | NewsAPI Key | 可选 |

### 2. 本地运行

```bash
#创建虚拟环境并激活
python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
python daily.py    # 每日推送
python weekly.py   # 周报推送
```

### 3. 部署到 GitHub Actions

将 Secrets 配置到仓库后推送代码，Actions 将按 cron 自动运行。也可在 Actions 页面手动 `workflow_dispatch` 触发。

## 项目结构

```
lark-news-v2/
├── src/
│   ├── config.py           # 关键词、RSS 源、环境变量
│   ├── models.py           # Article 数据模型
│   ├── pipeline.py         # 主编排
│   ├── sources/            # 搜索层
│   │   ├── google_news.py  # Google News RSS (zh + en)
│   │   ├── newsapi.py      # NewsAPI (zh + en)
│   │   ├── rss_feeds.py    # 垂直 RSS 源
│   │   └── aggregator.py   # 多源聚合
│   ├── filters/
│   │   ├── dedup.py        # URL 去重
│   │   └── date_filter.py  # 昨天 / 上周过滤
│   ├── ai/
│   │   ├── filter.py       # 筛选 + 翻译 + 摘要
│   │   └── trend.py        # 周报趋势
│   └── lark/
│       └── cards.py        # 卡片构建 + 发送
├── daily.py
├── weekly.py
└── .github/workflows/
```

## 搜索源

每个方向（AI Agent Payment / Web3 卡）均并行使用三层搜索：

| 层级 | 来源 | 方式 | 说明 |
|------|------|------|------|
| 1 | Google News | 按关键词，zh-CN + en-US | 覆盖面最广，免费 |
| 2 | NewsAPI | 按关键词，zh + en | 需 API Key，主流媒体 |
| 3 | RSS_FEEDS | 垂直站点 feed + 关键词过滤 | 行业媒体补充 |

`RSS_FEEDS` 配置在 `src/config.py`，当前包含 CoinDesk、Cointelegraph、The Block、PYMNTS、PANews、律动、Odaily、链捕手、36氪、机器之心、钛媒体等 13 个源。可按需增删。

## 降级策略

| 组件 | 正常 | 降级 |
|------|------|------|
| 搜索 | 多源并行 | 跳过失败的源 |
| 筛选 | AI 智能筛选 | 按时间排序取 Top N |
| 推送 | Lark 卡片 | 日志报错 |
