# 舆情监测工具

监测固定词条的舆情动态，支持多源采集、情感分析（正面/负面）、可视化看板。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 生成演示数据 + 查看看板（最快体验）

```bash
python main.py demo        # 生成模拟数据
python main.py dashboard   # 启动看板
```

浏览器打开 http://127.0.0.1:5000 即可看到看板。

### 3. 真实采集

```bash
python main.py crawl       # 执行一轮采集
python main.py all         # 采集 + 启动看板
```

## 配置说明

所有配置在 `config.yaml` 中：

### 监测词条

支持分组（方便银行间对比）：

```yaml
keywords:
  工商银行:
    - 工商银行
    - 工行
    - ICBC
  建设银行:
    - 建设银行
    - 建行
    - CCB
  通用词条:
    - 借记卡
    - 工银信使
    - 盗刷
    - 电诈
    - 收费贵
    # ... 更多词条
```

### 数据源

| 数据源 | 状态 | 配置方式 |
|--------|------|----------|
| DuckDuckGo 搜索 | 开箱即用 | 默认启用，通过搜索引擎采集微博内容 |
| 微博 | 需要 Cookie | 填入登录 Cookie 后启用 |
| 小红书 | 需要 Cookie + 签名 | 填入 Cookie 后启用（可能需 xhs 库） |
| 抖音 | 需要 Cookie + 签名 | 填入 Cookie 后启用 |

#### 微博 Cookie 获取方式

1. 浏览器打开 m.weibo.cn 并登录
2. F12 打开开发者工具 -> Application -> Cookies
3. 复制所有 Cookie 值，填入 config.yaml:

```yaml
sources:
  weibo:
    enabled: true
    cookie: "SUB=xxx; SUBP=xxx; ..."
```

#### 小红书 / 抖音 Cookie 获取方式

1. 浏览器登录对应平台
2. F12 -> Network -> 搜索任意关键词
3. 找到搜索请求 -> Request Headers -> 复制 cookie 值

## 项目结构

```
opinion_monitor/
├── config.yaml              # 配置文件（词条、数据源、情感词典）
├── requirements.txt         # Python 依赖
├── main.py                  # 主程序入口
├── demo_data.py             # 演示数据生成器
├── crawlers/
│   ├── base.py              # 爬虫基类
│   ├── weibo.py             # 微博采集器（访客认证 + Cookie 模式）
│   ├── xiaohongshu.py       # 小红书采集器（需 Cookie + 签名）
│   ├── douyin.py            # 抖音采集器（需 Cookie + 签名）
│   └── duckduckgo.py        # DuckDuckGo 搜索采集器（开箱即用）
├── analyzer/
│   └── sentiment.py         # 情感分析（金融关键词 + SnowNLP）
├── storage/
│   └── db.py                # SQLite 存储
├── dashboard/
│   ├── app.py               # Flask 看板服务
│   └── templates/
│       └── index.html       # 看板页面（Chart.js 可视化）
└── data/
    └── opinion.db           # SQLite 数据库（自动生成）
```

## 看板功能

- **统计概览**: 监测总量、正面/负面数量
- **趋势图**: 按日期展示正负面舆情走势
- **情感分布**: 正面/负面占比饼图
- **来源分布**: 微博/小红书/抖音数据量对比
- **词条热度**: 各词条的正负面堆叠排行
- **明细表格**: 支持按词条/来源/情感筛选，每条数据带原文链接

## 情感分析原理

采用双层策略：

1. **金融领域关键词匹配**（高精度）
   - 负面词: 盗刷、电诈、收费贵、强制、捆绑、投诉、差评...
   - 正面词: 好评、推荐、满意、方便、优惠、福利...
   
2. **SnowNLP 通用中文情感分析**（兜底）
   - 对未命中关键词的文本使用通用模型判定

## 定时采集

可用系统定时任务实现自动采集：

**Linux/Mac (crontab):**
```bash
0 * * * * cd /path/to/opinion_monitor && python main.py crawl
```

**Windows (任务计划程序):**
创建基本任务 -> 每小时执行 -> 启动程序填 python.exe -> 参数填 main.py crawl
