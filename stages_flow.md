# OpenKeyword Pipeline Analysis

## Stage 1: Company Analysis (公司分析)

**目标**: 对目标公司进行全面分析，建立深度的上下文理解，为后续关键词生成提供精准依据。

**流程**:
1.  **输入**: 公司网址 (URL), 公司名称 (可选), 目标语言, 目标地区。
2.  **核心逻辑**:
    *   利用 Gemini AI 结合 Google Search Grounding 能力。
    *   执行针对性的搜索策略：
        *   产品与服务 (`URL products services`)
        *   客户评价与反馈 (`URL customers reviews`)
        *   竞争对手对比 (`URL vs competitors`)
    *   **信息提取**: 从搜索结果中提取六大维度的结构化数据：
        1.  **基本信息**: 公司名、简介、所属行业 (具体到细分领域，如 B2B SaaS)。
        2.  **产品服务**: 具体销售的产品名称、提供的服务内容。
        3.  **客户洞察**: 目标客户群体、客户痛点、解决的问题、实际应用场景。
        4.  **价值主张**: 核心卖点、差异化优势、关键功能特性。
        5.  **市场定位**: 主要竞争对手 (3-5个)、主要覆盖区域。
        6.  **品牌调性**: 品牌声音风格 (正式/随意/技术向等)、产品类别。
3.  **输出**: `CompanyContext` 对象，包含上述所有结构化分析结果。

---

## Stage 2: Deep Research (深度调研 - 可选)

**目标**: 挖掘 Reddit, Quora 及各类论坛中的长尾关键词、用户真实提问和痛点描述。

**流程**:
1.  **输入**: Stage 1 输出的 `CompanyContext`, 目标关键词数量。
2.  **核心逻辑**:
    *   **并行执行**两个调研任务：
        *   **Reddit 调研**:
            *   搜索策略: `site:reddit.com` 结合行业词、"help", "recommendation", "vs" 等。
            *   Prompt 示例（英文，实际由代码注入行业与服务）:

                ```text
                Today's date: {当前日期}

                Search Reddit for discussions about: {company.industry}
                Related services: {services_str}

                Find {target_count} unique long-tail keywords and questions.

                Search queries to use:
                - site:reddit.com "{company.industry} help"
                - site:reddit.com "{company.industry} recommendation"
                - site:reddit.com "{company.industry} vs"
                - site:reddit.com "{services_str} question"

                Extract:
                1. Real questions people ask
                2. Problem descriptions (pain points)
                3. Specific terminology used
                4. Comparison phrases
                5. "How to" queries

                For EACH keyword, capture:
                - The exact keyword/phrase
                - Full URL to the Reddit thread
                - Actual quote from the discussion
                - Thread title
                - Subreddit name
                - Upvote count if visible

                Return JSON with array of keywords.
                ```

            *   提取内容: 真实用户问题、痛点描述、特定术语、比较级短语。
            *   元数据: 捕获原帖 URL、subreddit、点赞数、原句引用。
        *   **Quora/Forum 调研**:
            *   搜索策略: `site:quora.com`, "forum discussion", "people also ask"。
            *   Prompt 示例（英文，实际由代码注入行业与服务）:

                ```text
                Today's date: {当前日期}

                Search for questions about: {company.industry}
                Related services: {services_str}

                Find {target_count} unique questions and long-tail keywords.

                Search queries:
                - site:quora.com "{company.industry}"
                - "{company.industry}" people also ask
                - "{services_str}" how to
                - "{company.industry}" forum discussion

                Extract:
                1. Actual questions people ask
                2. "How to" queries
                3. "Best way to" phrases
                4. Comparison questions
                5. Specific pain points

                For EACH keyword, capture:
                - The exact question/keyword
                - Source URL
                - Source type (quora, forum, paa)

                Return JSON with array of keywords.
                ```

            *   提取内容: "How to"查询、"Best way to"短语、对比类问题。
    *   **去重**: 对收集到的原始关键词进行初步去重。
3.  **输出**: `Stage2Output`，包含带有来源元数据 (URL, Quote, Source Type) 的关键词列表。

---

## Stage 3: AI Keyword Generation (AI 关键词生成)

**目标**: 基于公司深层上下文，利用 AI 生成覆盖不同搜索意图的高质量 SEO 关键词。

**流程**:
1.  **输入**: `CompanyContext`, Stage 2 调研得到的关键词, 目标总数, 地区, 语言。
2.  **核心逻辑**:
    *   **计算生成量**: 结合目标总数与 Stage 2 已有调研词数：
        *   已有调研词数 = `len(research_keywords)`
        *   AI 生成目标数 = `max(目标总数 - 已有调研词数, 目标总数 / 3)`
    *   **构建 Prompt（核心字段与规则）**:
        *   注入 Stage 1 的核心信息：
            *   COMPANY: `company.company_name`
            *   INDUSTRY: `company.industry`
            *   PRODUCTS: 前 5 个产品名称
            *   SERVICES: 前 5 个服务条目
            *   PAIN POINTS: 前 5 个痛点
            *   DIFFERENTIATORS: 前 3 个差异化优势
            *   TARGET REGION / LANGUAGE: 目标地区与语言
        *   设定生成要求（与代码中 Prompt 对齐）:
            *   **多样化意图**:
                *   transactional（购买 / 价格 / demo）
                *   commercial（对比 / 替代方案 / vs）
                *   informational（教程 / 原理 / 指南）
                *   question（真实问题）
                *   comparison（X vs Y）
            *   **关键词类型**:
                *   长尾词（3–5 个词）
                *   问题类（"how to...", "what is..."）
                *   对比类（"X vs Y", "alternatives to"）
                *   产品 / 方案特定关键词
                *   解决问题导向的关键词
            *   **避坑指南**:
                *   避免过于通用的行业大词
                *   避免单词关键词
                *   避免简单变体 / 重复
    *   **Prompt 示例（英文，实际由代码注入具体字段）**:

        ```text
        Generate {ai_target} SEO keywords for this company:

        COMPANY: {company.company_name}
        INDUSTRY: {company.industry}
        PRODUCTS: {products}
        SERVICES: {services}
        PAIN POINTS: {pain_points}
        DIFFERENTIATORS: {differentiators}
        TARGET REGION: {region}
        LANGUAGE: {language}

        REQUIREMENTS:
        1. Generate DIVERSE keywords across these intents:
           - transactional (buy, pricing, demo)
           - commercial (comparison, alternatives, vs)
           - informational (how to, what is, guide)
           - question (actual questions users ask)

        2. Include:
           - Long-tail keywords (3-5 words)
           - Question keywords ("how to...", "what is...")
           - Comparison keywords ("X vs Y", "alternatives to")
           - Product-specific keywords
           - Problem-solving keywords

        3. AVOID:
           - Generic industry terms
           - Single-word keywords
           - Duplicate variations

        Return JSON with array of keywords, each with:
        - keyword: the keyword text
        - intent: one of [transactional, commercial, informational, question, comparison]
        - is_question: true if it's a question
        ```

    *   **AI 生成**: 调用 Gemini，使用 JSON Schema (`KEYWORD_SCHEMA`) 约束返回结构，将结果映射为 `GeneratedKeyword` 列表。
3.  **输出**: `Stage3Output`，包含生成的关键词及其意图分类 (`intent`) 和是否为问题 (`is_question`) 标记。

---

## Stage 4: Scoring & Deduplication (评分与去重)

**目标**: 清洗数据，移除重复项，并根据“公司匹配度”对关键词进行评分筛选。

**流程**:
1.  **输入**: `CompanyContext`, 所有关键词 (Stage 2 + Stage 3), 最低分阈值 (`min_score`, 默认 40), 最小词长 (`min_word_count`, 默认 2)。
2.  **核心逻辑**:
    *   **快速去重 (Fast Deduplication)**:
        *   **精确匹配**: 完全相同的字符串去重。
        *   **Token 签名 (Token Signature)**: 将关键词拆分为单词并排序，生成签名（如 "seo tool" 和 "tool seo" 视为相同），解决语序重复问题。
    *   **智能评分 (AI Scoring)**:
        *   **批量处理**: 将关键词按 50 个一组分批传给 Gemini。
        *   **上下文注入**:
            *   COMPANY / INDUSTRY
            *   PRODUCTS (Top 5)
            *   SERVICES (Top 5)
            *   PAIN POINTS (Top 3)
        *   **评分标准 (0-100)**:
            *   **80-100**: 直接提及公司产品/服务/解决方案。
            *   **60-79**: 高度相关，涉及核心痛点和价值主张。
            *   **40-59**: 行业相关，较为宽泛。
            *   **20-39**: 弱相关，可能带来少量流量。
            *   **0-19**: 不相关或过于通用。
    *   **过滤 (Filter)**:
        *   移除分数 < `min_score` 的词。
        *   移除单词数 < `min_word_count` 的短词。
3.  **Prompt 示例**:

    ```text
    Score these keywords for company-fit (0-100):

    COMPANY: {company.company_name}
    INDUSTRY: {company.industry}
    PRODUCTS: {products}
    SERVICES: {services}
    PAIN POINTS: {pain_points}

    SCORING CRITERIA:
    - 80-100: Directly mentions company products/services/solutions
    - 60-79: Highly relevant to company's pain points and value props
    - 40-59: Generally relevant to industry/niche
    - 20-39: Loosely related, might attract some relevant traffic
    - 0-19: Not relevant, too generic, or wrong audience

    KEYWORDS TO SCORE:
    [
      "keyword 1",
      "keyword 2",
      ...
    ]

    Return JSON with array of {keyword, score} for each.
    ```

4.  **输出**: `Stage4Output`
    *   `keywords`: 评分后的 `ScoredKeyword` 列表 (包含 `score`, `intent`, `is_question` 等)。
    *   `duplicates_removed`: 去重数量。
    *   `low_score_removed`: 低分过滤数量。


---

## Stage 5: Clustering (聚类)

**目标**: 将散乱的关键词按语义及主题分组，形成结构化的内容簇。

**流程**:
1.  **输入**: `Stage5Input`
    *   `company_context`: 来自 Stage 1 的公司画像。
    *   `keywords`: 已评分的关键词列表 (`ScoredKeyword`)，来自 Stage 4。
    *   `cluster_count`: 目标聚类数量 (例如 5、8 等)。
    *   `enable_clustering`: 是否启用聚类，关闭时直接跳过 AI 调用。
2.  **核心逻辑**:
    *   **降级路径 (无聚类模式)**:
        *   若 `enable_clustering = False` 或 `keywords` 为空:
            *   不调用 AI，直接返回 `cluster_name = None` 的关键词列表。
            *   `clusters = []`, `ai_calls = 0`。
    *   **构建 Prompt 并调用 Gemini**:
        *   提取所有关键词文本，形成 `keyword_list`。
        *   注入上下文:
            *   `company.company_name`
            *   `company.industry` (无则 "N/A")
        *   关键规则:
            *   要求创建 **精确数量** 的簇: `{cluster_count}`。
            *   每个簇有一个 **2–4 个词的简短描述性名称**。
            *   按 **语义相似性** 与 **主题相关性** 分组。
            *   每个关键词 **必须且只能属于一个簇**。
            *   尽量 **平衡簇大小**，避免所有词集中在单一簇。
        *   示例簇名（与代码保持一致）:
            *   "Pricing & Plans"
            *   "How-To Guides"
            *   "Competitor Comparisons"
            *   "Product Features"
            *   "Industry Solutions"
        *   使用 `CLUSTERING_SCHEMA` 作为 JSON Schema 约束返回结构:
            *   `clusters`: 数组，每项包含 `name` 与 `keywords` (字符串数组)。
    *   **解析与映射**:
        *   解析 Gemini 返回的 JSON (支持 ```json fenced code``` 包裹的情况)。
        *   构建 `keyword -> cluster_name` 映射 (统一转为小写匹配)。
        *   将每个原始关键词包装为 `ClusteredKeyword`:
            *   保留 `keyword`, `intent`, `score`, `source`, `is_question`。
            *   设置 `cluster_name`，若未命中则标记为 `"Uncategorized"`。
        *   同时构建 `Cluster` 列表 (簇名称 + 其下所有关键词)。
    *   **错误处理**:
        *   若 AI 调用或解析失败:
            *   记录错误日志。
            *   返回所有关键词，`cluster_name` 统一为 `"Uncategorized"`。
            *   `clusters = []`, `ai_calls = 1` (仍计一次调用尝试)。
3.  **Prompt 示例（英文，实际由代码注入字段）**:

    ```text
    Group these keywords into {cluster_count} semantic clusters for {company.company_name}:

    INDUSTRY: {company.industry or "N/A"}

    KEYWORDS:
    {json.dumps(keyword_list, indent=2)}

    CLUSTERING RULES:
    1. Create exactly {cluster_count} clusters
    2. Each cluster should have a short, descriptive name (2-4 words)
    3. Group by semantic similarity and topic
    4. Every keyword must belong to exactly one cluster
    5. Balance cluster sizes (avoid putting everything in one cluster)

    Example cluster names:
    - "Pricing & Plans"
    - "How-To Guides"
    - "Competitor Comparisons"
    - "Product Features"
    - "Industry Solutions"

    Return JSON with clusters array, each containing:
    - name: cluster name
    - keywords: array of keyword strings
    ```

4.  **输出**: `Stage5Output`
    *   `keywords`: `ClusteredKeyword` 列表，每个关键词带有 `cluster_name`。
    *   `clusters`: `Cluster` 列表，包含簇名称及其关键词。
    *   `ai_calls`: 本阶段共进行的 AI 调用次数 (0 或 1)。

---

## 总结 (Summary)

OpenKeywords Pipeline 通过 **"分析 -> 调研 -> 生成 -> 评分 -> 聚类"** 的五步漏斗模型，确保生成的关键词不仅数量达标，且具备以下特征：
1.  **高度定制**: 基于 Stage 1 的深度公司画像，而非简单的行业词库。
2.  **真实有效**: 引入 Reddit/Quora 真实用户语料 (Stage 2)。
3.  **质量可控**: 通过 AI 评分机制过滤低相关性词汇 (Stage 4)。
4.  **结构清晰**: 最终输出按主题聚类，便于 SEO 内容规划 (Stage 5)。
