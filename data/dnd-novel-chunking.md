# SAO Progressive 小说分块入库 ChromaDB

## Context

本项目是 AI 驱动的 DND 游戏（基于刀剑神域/SAO），需要将 8 本 SAO Progressive 小说向量化存入 ChromaDB，为后续 RAG（检索增强生成）提供知识库。当前项目没有任何向量数据库相关代码。

小说文本（TXT）已在 `asset/sao/` 目录下，由 `convert_epub.py` 从 EPUB 转换而来。EPUB 文件在 `asset/` 目录但未被 git 追踪，TXT 文件也未被追踪。

## 关键决策

- 脚本位置：`gameserver/scripts/`
- Embedding 模型：`BAAI/bge-small-zh-v1.5`（中文优化，~90MB）
- ChromaDB 持久化路径：`gameserver/data/chromadb/`
- Collection 名：`sao_progressive_novels`
- Chunk 大小：500-1000 中文字符，段落边界优先，50-100 字符重叠

## 实施步骤

### 步骤 1：修改 .gitignore

文件：`/.gitignore`

追加：
```
# EPUB files (large binary)
*.epub

# ChromaDB local data
gameserver/data/
```

### 步骤 2：添加 Python 依赖

文件：`/gameserver/pyproject.toml`

在 dependencies 中添加：
```
"chromadb>=1.0.0",
"sentence-transformers>=3.0.0",
```

### 步骤 3：配置国内镜像源并安装依赖

创建文件：`/gameserver/uv.toml`
```toml
[[index]]
url = "https://pypi.tuna.tsinghua.edu.cn/simple"
```

执行：`cd gameserver && uv sync`

### 步骤 4：创建 novel_parser.py

文件：`/gameserver/scripts/novel_parser.py`

核心逻辑：
1. **读取 TXT 文件**，识别并跳过元数据头部（制作信息、简介、目录区域）
2. **识别故事边界**：使用预定义故事标题列表匹配（8个故事标题）
3. **识别小节边界**：
   - 模式A（大多数卷）：独立数字行 `^\d{1,2}$`，通过行间距（>5行）区分正文分节vs目录数字
   - 模式B（卷2）：`^黑白协奏曲 \d+$` 格式
4. **识别并排除后记**：独立行 `后记` 到文件末尾
5. **提取游戏世界标注**：从故事开头识别 `艾恩葛朗特第X层` 和 `二〇二X年X月` 模式，提取层数和游戏内时间
6. **返回结构化数据**：`List[Section]`，每个 Section 包含 volume、story_title、section_number、text、aincrad_layer、in_game_date

已知故事标题映射（硬编码配置）：
- 卷1：无星夜的咏叹调（第1层）+ 幻眬剑之回旋曲（第2层）
- 卷2：黑白协奏曲（第3层，特殊分节格式）
- 卷3：泡影的船歌（第4层）
- 卷4：阴沉薄暮的诙谐曲（第5层）
- 卷5：黄金定律的卡农（上）（第6层）
- 卷6：黄金定律的卡农（下）（第6层）
- 卷7：赤色焦热的狂想曲（上）（第7层）
- 卷8：赤色焦热的狂想曲（下）（第7层）

游戏世界标注提取规则：
- 层数：正则 `艾恩葛朗特第(.+?)层` → 中文数字转int
- 时间：正则 `(二〇二[二三]年.+?月)` → 保留原始中文字符串
- 这些标记出现在每个故事正文的开头，同一故事的所有 section/chunk 继承该值

### 步骤 5：创建 text_chunker.py

文件：`/gameserver/scripts/text_chunker.py`

`chunk_section(text, max_chars=800, overlap=100)` 函数：
1. 文本 < max_chars → 直接返回单个 chunk
2. 按段落边界（`\n\n`）拆分
3. 贪心合并段落至接近 max_chars
4. 段落过长时按句号/问号/感叹号分割
5. chunk 间保留 overlap 字符重叠
6. 最小 chunk 不小于 200 字符

### 步骤 6：创建 ingest_novels.py

文件：`/gameserver/scripts/ingest_novels.py`

主入口脚本：
1. 初始化 ChromaDB persistent client（路径 `gameserver/data/chromadb/`）
2. 使用 `SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-small-zh-v1.5")` 创建 embedding 函数
3. 创建/重置 collection `sao_progressive_novels`（幂等：每次运行先删除旧 collection）
4. 遍历 `asset/sao/` 下 8 个 TXT 文件
5. 调用 parser → chunker → 批量写入 ChromaDB
6. 每个 chunk 的 metadata 分两个维度：
   - **基础结构标注**：`volume`(int)、`story_title`(str)、`section_number`(int)、`chunk_index`(int)、`total_chunks_in_section`(int)、`source_file`(str)
   - **游戏世界标注**：`aincrad_layer`(int, 艾恩葛朗特层数)、`in_game_date`(str, 如"二〇二二年十一月")
   - 游戏世界标注从每个故事开头的层级标记提取（如 `艾恩葛朗特第三层 二〇二二年十一月`），同一故事下所有 chunk 继承该标注
7. ID 格式：`vol{N}_s{section}_c{chunk}`
8. 打印统计信息

需要 `gameserver/scripts/__init__.py` 空文件。

### 步骤 7：创建 verify_vectordb.py

文件：`/gameserver/scripts/verify_vectordb.py`

验证脚本：
1. 连接 ChromaDB，打印总文档数
2. 按 volume 统计
3. 执行示例语义查询（如"桐人和亚丝娜"），打印 TOP-3 结果

### 步骤 8：更新 Makefile

文件：`/Makefile`

新增 target：
```makefile
ingest-novels: ## Ingest SAO novels into ChromaDB
	cd gameserver && uv run python -m scripts.ingest_novels

verify-vectordb: ## Verify ChromaDB ingestion results
	cd gameserver && uv run python -m scripts.verify_vectordb
```

### 步骤 9：更新 README.md

文件：`/README.md`

在技术栈表格中新增一行：`| 知识库 | ChromaDB + BGE-small-zh |`

在「项目结构」中更新 asset 描述：
```
├── asset/              # 游戏资源
│   └── sao/            # SAO Progressive 小说文本 (1-8卷)
```

在「环境要求」后新增「小说知识库」章节：
- 数据源说明（8本小说TXT）
- 分块策略（两级拆分）
- 向量数据库配置（ChromaDB + BGE-small-zh）
- 构建命令（`make ingest-novels` / `make verify-vectordb`）

在「更新日志」中新增 v0.200 条目：
- SAO Progressive 小说向量化知识库（ChromaDB + BGE-small-zh）
- 小说文本按章节+语义两级分块入库
- 新增 Makefile target: ingest-novels / verify-vectordb

更新版本号为 v0.200，在更新日志中新增 v0.200 条目记录本次变更。

### 步骤 10：更新版本号

文件：`/VERSION`

内容改为 `v0.200`

### 步骤 11：保存计划文档到项目 data 目录

将本计划文档保存到 `/data/dnd-novel-chunking.md`，作为项目技术文档的一部分。

### 步骤 12：Git 追踪 TXT 文件

- `git add asset/sao/*.txt` — 将小说文本加入版本控制
- 确认 `*.epub` 已被 .gitignore 排除
- 不执行 commit（等用户指示）

## 涉及文件

| 文件 | 操作 |
|------|------|
| `.gitignore` | 修改：追加 epub 和 data 排除规则 |
| `gameserver/pyproject.toml` | 修改：添加 chromadb、sentence-transformers 依赖 |
| `gameserver/uv.toml` | 新建：配置清华 PyPI 镜像源 |
| `gameserver/scripts/__init__.py` | 新建：空文件 |
| `gameserver/scripts/novel_parser.py` | 新建：小说解析模块 |
| `gameserver/scripts/text_chunker.py` | 新建：文本二次分块模块 |
| `gameserver/scripts/ingest_novels.py` | 新建：主入口脚本 |
| `gameserver/scripts/verify_vectordb.py` | 新建：验证脚本 |
| `Makefile` | 修改：添加 ingest-novels 和 verify-vectordb target |
| `README.md` | 修改：新增知识库章节，更新技术栈、项目结构、版本日志 |
| `VERSION` | 修改：v0.100 → v0.200 |
| `data/dnd-novel-chunking.md` | 新建：本计划文档 |

## 验证方案

1. `cd gameserver && uv sync` — 依赖安装成功
2. `make ingest-novels` — 脚本运行无报错，打印各卷统计（section 数、chunk 数）
3. `make verify-vectordb` — 输出总文档数（预估 400-800）、按卷统计、语义查询返回相关结果
4. `git status` — 确认 TXT 文件在暂存区、EPUB 文件被忽略、chromadb data 被忽略
