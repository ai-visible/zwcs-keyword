# 🎯 Content Brief Enhancement for OpenKeywords

## Problem
Current output gives **keywords** but not the **content intelligence** writers need:
- ❌ No actual research quotes/snippets
- ❌ No SERP context (what's ranking, what's missing)
- ❌ No angle/approach suggestions
- ❌ No specific questions to answer
- ❌ No target audience pain points

Writers get a keyword list but have to research everything themselves → defeats the purpose of deep research!

---

## 📊 Proposed New Columns

### 1. Research Context (`research_context`)
**Type:** `Optional[str]`  
**Purpose:** Actual quotes/snippets from Reddit, Quora, forums

**Examples:**
```python
{
  "keyword": "why does Google ignore my structured data",
  "research_context": "Reddit user: 'I added schema markup 3 months ago and Google still isn't showing rich results. Tested in schema validator, all valid. What am I missing?'"
}

{
  "keyword": "AEO vs SEO difference",
  "research_context": "Quora: 'Traditional SEO focuses on rankings, but AEO is about being the answer AI assistants cite. Different optimization strategies.'"
}
```

**CSV Export:** Truncate to 500 chars, preserve key insights

---

### 2. Content Angle (`content_angle`)
**Type:** `Optional[str]`  
**Purpose:** AI-suggested approach/angle for the article

**Examples:**
```python
{
  "keyword": "best project management software for small teams",
  "content_angle": "Comparison guide with decision matrix - focus on affordability, ease of use, and team size scalability"
}

{
  "keyword": "how to improve team collaboration remotely",
  "content_angle": "Tactical how-to guide with 7 actionable strategies, emphasizing async communication and tool integration"
}
```

**Generation:** Single Gemini prompt batch-scores keywords AND suggests angles

---

### 3. Target Questions (`target_questions`)
**Type:** `list[str]` (stored as JSON array or comma-separated)  
**Purpose:** Specific questions the article should answer

**Examples:**
```python
{
  "keyword": "what is AEO optimization",
  "target_questions": [
    "What is the difference between AEO and SEO?",
    "How do AI answer engines like Perplexity work?",
    "What are the key AEO ranking factors?",
    "How do I optimize my content for AI citations?"
  ]
}
```

**Sources:**
- PAA questions from SERP analysis
- Related questions from research (Reddit/Quora)
- AI-generated questions based on intent

---

### 4. Top Ranking Content (`top_ranking_content`)
**Type:** `Optional[str]`  
**Purpose:** Summary of what's currently ranking (from SERP analysis)

**Examples:**
```python
{
  "keyword": "best SEO tools 2025",
  "top_ranking_content": "Mostly listicles (10-20 tools). Top 3: comprehensive comparisons with pricing tables. Featured snippet: comparison chart. Missing: AEO-specific tools, AI-powered solutions."
}
```

**Generation:** From DataForSEO organic results + featured snippet analysis

---

### 5. Content Gap (`content_gap`)
**Type:** `Optional[str]`  
**Purpose:** What's missing from current SERP results (opportunity)

**Examples:**
```python
{
  "keyword": "SEO for SaaS startups",
  "content_gap": "No content addressing early-stage (pre-PMF) SEO. Most focus on scaling, not foundation-building. No mention of AEO strategies."
}

{
  "keyword": "Google structured data not working",
  "content_gap": "Articles show HOW to add schema but don't explain WHY Google ignores valid markup (crawl budget, trust, content quality)."
}
```

**Generation:** AI analyzes top ranking content + research context → identifies gaps

---

### 6. Target Audience Pain Point (`audience_pain_point`)
**Type:** `Optional[str]`  
**Purpose:** Specific pain point this keyword addresses

**Examples:**
```python
{
  "keyword": "why won't Google index my new pages",
  "audience_pain_point": "Website owners frustrated that new content isn't appearing in search despite submitting sitemap and requesting indexing."
}
```

**Sources:**
- Reddit/Quora research context
- AI inference from keyword intent
- Common themes from PAA questions

---

### 7. Recommended Word Count (`recommended_word_count`)
**Type:** `Optional[int]`  
**Purpose:** Suggested article length based on SERP competition

**Examples:**
```python
{
  "keyword": "what is SEO",  # High competition, definitive guide needed
  "recommended_word_count": 2500
}

{
  "keyword": "how to add meta description in WordPress",  # Simple how-to
  "recommended_word_count": 800
}
```

**Logic:**
- Simple how-to (transactional): 600-1000 words
- Commercial comparison: 1500-2000 words
- Question/informational: 1200-1800 words
- Competitive commercial: 2000-3000 words
- Based on average word count of top 5 results

---

### 8. Internal Linking Opportunities (`internal_links`)
**Type:** `list[str]` (related keywords from same cluster)  
**Purpose:** Suggest related articles to link to

**Examples:**
```python
{
  "keyword": "best project management software",
  "internal_links": [
    "project management for remote teams",
    "agile project management tools",
    "project management software pricing"
  ]
}
```

**Generation:** From semantic clustering + same cluster keywords

---

### 9. Featured Snippet Opportunity (`fs_opportunity_type`)
**Type:** `Optional[str]`  
**Purpose:** What type of featured snippet to target

**Values:**
- `"paragraph"` - Definition/explanation
- `"list"` - Steps/tips (numbered or bulleted)
- `"table"` - Comparison/data
- `"none"` - No featured snippet on SERP
- `"video"` - Video result (consider video content)

**Examples:**
```python
{
  "keyword": "how to optimize for AEO",
  "fs_opportunity_type": "list",
  "target_questions": ["What are the steps to optimize for AEO?"]
}
```

---

### 10. Quotes for Social Proof (`expert_quotes`)
**Type:** `Optional[str]`  
**Purpose:** Expert quotes or stats from research to include

**Examples:**
```python
{
  "keyword": "AEO statistics 2025",
  "expert_quotes": "Gartner predicts 30% of searches will be zero-click by 2026. Source: Reddit r/SEO discussion citing Gartner report."
}
```

---

## 🏗️ Implementation Strategy

### Phase 1: Data Collection Enhancement

#### A. Enhance `researcher.py` - Capture Research Context
```python
# In _parse_keywords_response()
valid_keywords.append({
    "keyword": keyword_text,
    "intent": kw.get("intent", "informational"),
    "source": kw.get("source", "research"),
    "context": kw.get("context", ""),  # ✅ Already exists!
    # NEW: Store actual quote/snippet
    "research_snippet": kw.get("snippet", ""),
    "research_url": kw.get("url", ""),
})
```

**Modify research prompts to extract:**
- Direct quotes from discussions
- URLs where found
- Specific pain points mentioned

#### B. Enhance `serp_analyzer.py` - Capture SERP Intelligence
```python
@dataclass
class SerpFeatures:
    # ... existing fields ...
    
    # NEW FIELDS
    top_ranking_summaries: list[str] = field(default_factory=list)
    avg_word_count: int = 0
    common_content_types: list[str] = field(default_factory=list)  # ["listicle", "how-to", "comparison"]
    content_gap_notes: str = ""
```

**Extract from DataForSEO organic results:**
- Meta descriptions → summarize what's ranking
- URL patterns → identify content types
- Title patterns → common angles

#### C. Add Content Intelligence Generator
```python
# New file: openkeywords/content_intelligence.py

class ContentIntelligenceGenerator:
    """
    Generate content briefs with angles, questions, and gaps.
    
    Takes keywords + research + SERP data → produces actionable content brief.
    """
    
    async def enrich_keywords(
        self, 
        keywords: list[Keyword],
        research_data: dict,
        serp_data: dict,
    ) -> list[EnrichedKeyword]:
        """
        Batch process keywords to add content intelligence.
        
        Uses single Gemini prompt to generate:
        - Content angle
        - Target questions (from PAA + research)
        - Content gaps
        - Pain points
        - Recommended word count
        """
```

### Phase 2: Update Data Model

```python
# openkeywords/models.py

class Keyword(BaseModel):
    # ... existing fields ...
    
    # CONTENT BRIEF FIELDS
    research_context: Optional[str] = Field(
        default=None, 
        description="Actual quote/snippet from research (Reddit, Quora, etc.)"
    )
    content_angle: Optional[str] = Field(
        default=None,
        description="Suggested approach/angle for the article"
    )
    target_questions: list[str] = Field(
        default_factory=list,
        description="Specific questions the article should answer"
    )
    top_ranking_content: Optional[str] = Field(
        default=None,
        description="Summary of what's currently ranking on SERP"
    )
    content_gap: Optional[str] = Field(
        default=None,
        description="What's missing from current SERP results"
    )
    audience_pain_point: Optional[str] = Field(
        default=None,
        description="Specific pain point this keyword addresses"
    )
    recommended_word_count: Optional[int] = Field(
        default=None,
        description="Suggested article length based on competition"
    )
    internal_links: list[str] = Field(
        default_factory=list,
        description="Related keywords to link to (from same cluster)"
    )
    fs_opportunity_type: Optional[str] = Field(
        default=None,
        description="Featured snippet type to target: paragraph, list, table, video"
    )
    expert_quotes: Optional[str] = Field(
        default=None,
        description="Expert quotes or stats from research"
    )
```

### Phase 3: Update CSV/JSON Export

```python
# Update to_csv() in GenerationResult
def to_csv(self, filepath: str) -> None:
    """Export keywords with full content brief to CSV"""
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            # Core fields
            "keyword", "intent", "score", "cluster", "volume", "difficulty",
            # Content brief fields
            "content_angle", "research_context", "target_questions", 
            "content_gap", "audience_pain_point", "recommended_word_count",
            "top_ranking_content", "fs_opportunity_type", "internal_links",
            # Metadata
            "source", "aeo_opportunity", "has_featured_snippet", "has_paa"
        ])
        
        for kw in self.keywords:
            writer.writerow([
                kw.keyword,
                kw.intent,
                kw.score,
                kw.cluster_name or "",
                kw.volume,
                kw.difficulty,
                # Brief fields
                kw.content_angle or "",
                (kw.research_context or "")[:500],  # Truncate for CSV
                "; ".join(kw.target_questions),
                kw.content_gap or "",
                kw.audience_pain_point or "",
                kw.recommended_word_count or "",
                (kw.top_ranking_content or "")[:300],
                kw.fs_opportunity_type or "",
                "; ".join(kw.internal_links[:5]),
                # Metadata
                kw.source,
                kw.aeo_opportunity,
                kw.has_featured_snippet,
                kw.has_paa,
            ])
```

### Phase 4: Update Generation Pipeline

```python
# In generator.py, after clustering:

# NEW STEP: Enrich with content intelligence
if config.enable_content_brief:  # New flag
    logger.info("Generating content briefs...")
    from .content_intelligence import ContentIntelligenceGenerator
    
    brief_generator = ContentIntelligenceGenerator(api_key=self.api_key)
    enriched_keywords = await brief_generator.enrich_keywords(
        keywords=filtered_keywords,
        research_data=research_results,  # From earlier step
        serp_data=serp_analyses,  # From earlier step
    )
    
    filtered_keywords = enriched_keywords
```

---

## 🎨 Example Output

### Current Output (Basic)
```csv
keyword,intent,score,cluster,volume,difficulty
"best project management software",commercial,92,Product Comparison,1200,45
"how to improve team collaboration",question,85,How-To Guides,890,32
```

### Enhanced Output (With Content Brief)
```csv
keyword,intent,score,cluster,volume,difficulty,content_angle,research_context,target_questions,content_gap,audience_pain_point,recommended_word_count,fs_opportunity_type,internal_links

"best project management software",commercial,92,Product Comparison,1200,45,"Comparison guide with decision matrix focusing on team size, budget, and key features","Reddit r/startups: 'We tried 5 PM tools as a 10-person startup. Asana was overkill, Trello too simple. Ended up with ClickUp - perfect middle ground.'","What is the best project management software for small teams?; How much does project management software cost?; What features should I look for?","Most reviews cover enterprise tools. Missing: detailed comparison for 5-15 person teams with limited budget.","Small team leads overwhelmed by complex tools designed for enterprises, need simple but powerful solution.",1800,table,"project management for startups; free project management tools; agile project management"

"how to improve team collaboration",question,85,How-To Guides,890,32,"Tactical how-to guide with 7 actionable strategies for remote teams","Quora: 'Our remote team feels disconnected. Slack messages get lost, no one knows what others are working on. Need practical advice not theory.'","How can remote teams collaborate better?; What tools improve team collaboration?; How to keep remote teams aligned?","Existing content is theory-heavy. Missing: specific async communication workflows, tool integration examples.","Remote team managers struggling with disconnection and information silos, need concrete processes.",1200,list,"remote team management; async communication tools; team collaboration software"
```

---

## 🚀 CLI Usage

```bash
# Enable content briefs
openkeywords generate \
  --company "Acme Software" \
  --industry "B2B SaaS" \
  --with-research \
  --with-serp \
  --with-content-brief \  # NEW FLAG
  --output keywords_with_briefs.csv

# The CSV now has everything a writer needs!
```

---

## 💡 Benefits for Content Writers

### Before (Current)
```
Writer receives: "best project management software"
Writer must:
1. Research what's ranking ✅
2. Analyze SERP gaps ✅
3. Find user pain points ✅
4. Determine article angle ✅
5. Identify questions to answer ✅
6. Research word count ✅
7. Find quotes/stats ✅

Time: 45-60 minutes of research per article
```

### After (With Briefs)
```
Writer receives full brief:
- Keyword: "best project management software"
- Angle: "Comparison for 5-15 person teams with budget constraints"
- Pain point: "Overwhelmed by enterprise tools"
- Questions to answer: [list of 4 specific questions]
- Gap: "No detailed SMB comparison"
- Word count: 1800 words
- Type: Comparison table + narrative
- Research: [actual Reddit quotes]
- Internal links: [3 related topics]

Time: 10 minutes to review brief, straight to writing

Time saved: 35-50 minutes per article
```

---

## 🎯 Implementation Priority

### P0 (Must Have)
1. ✅ `research_context` - Capture actual research quotes
2. ✅ `content_angle` - AI-generated angle/approach
3. ✅ `target_questions` - From PAA + research
4. ✅ `content_gap` - What's missing from SERP

### P1 (High Value)
5. ✅ `audience_pain_point` - From research analysis
6. ✅ `recommended_word_count` - Based on competition
7. ✅ `top_ranking_content` - SERP summary
8. ✅ `fs_opportunity_type` - Featured snippet targeting

### P2 (Nice to Have)
9. ⚠️ `internal_links` - From clustering (low effort)
10. ⚠️ `expert_quotes` - Requires deeper extraction

---

## 🔧 Technical Considerations

### Cost Impact
- **Current:** ~$0.02 per 50 keywords (generation + scoring)
- **With briefs:** ~$0.05 per 50 keywords (+ 1 batch enrichment call)
- **Net:** +150% cost, but saves 40+ min of manual research per article

### Token Usage
- Enrichment prompt: ~500 tokens per keyword
- Batch 10 keywords per prompt: ~5,000 tokens per batch
- For 50 keywords: ~25,000 tokens = ~$0.03

### Performance
- Enrichment can run in parallel with clustering
- Add ~10-15 seconds to total pipeline time
- Acceptable tradeoff for content team value

---

## 📦 Configuration

```python
class GenerationConfig(BaseModel):
    # ... existing fields ...
    
    # NEW
    enable_content_brief: bool = Field(
        default=False,
        description="Generate full content briefs with angles, questions, gaps"
    )
    brief_detail_level: str = Field(
        default="standard",
        description="Brief detail: minimal, standard, detailed"
    )
```

---

## 🎬 Next Steps

1. **Enhance research data capture** - Modify `researcher.py` to extract quotes/URLs
2. **Enhance SERP data capture** - Modify `serp_analyzer.py` to summarize top content
3. **Create content intelligence module** - New `content_intelligence.py` with enrichment logic
4. **Update data models** - Add new fields to `Keyword` model
5. **Update export functions** - CSV/JSON with new columns
6. **Add CLI flag** - `--with-content-brief`
7. **Test end-to-end** - Generate keywords with full briefs
8. **Document usage** - Update README with examples

---

## 🤔 Discussion Points

1. **Should we use separate columns or nested JSON?**
   - CSV: Flatten everything (easier for Google Sheets import)
   - JSON: Nested objects (cleaner but harder for non-devs)
   - **Recommendation:** Both - flatten for CSV, nest for JSON

2. **How much research context to store?**
   - Full quotes: Can be 500+ chars
   - Truncate to 300 chars for CSV?
   - Store full in JSON?
   - **Recommendation:** Store full, truncate on CSV export

3. **Should content briefs be opt-in or default?**
   - Default: Better UX but higher cost
   - Opt-in: Cheaper but users might not know about it
   - **Recommendation:** Opt-in with clear documentation

4. **Integration with blog-writer pipeline?**
   - Should `openkeywords` output feed directly into `blog-writer`?
   - Would eliminate manual keyword brief creation
   - **Recommendation:** Yes - next phase integration

---

**This transforms openkeywords from a keyword tool into a content intelligence platform.** 🚀

