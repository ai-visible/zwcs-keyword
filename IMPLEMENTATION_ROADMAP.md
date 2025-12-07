# 🚀 Quick Start: Implementing Content Briefs in OpenKeywords

## TL;DR
Add 10 columns to transform OpenKeywords from a keyword tool into a content intelligence platform that saves writers 60-80 minutes per article.

---

## 📋 Implementation Checklist

### Week 1: Data Model & Collection
- [ ] **Update `models.py`** - Add content brief fields to `Keyword` model
- [ ] **Enhance `researcher.py`** - Capture actual quotes/URLs from research
- [ ] **Enhance `serp_analyzer.py`** - Extract SERP context and summaries
- [ ] **Create `content_intelligence.py`** - New module for brief generation

### Week 2: Generation Logic
- [ ] **Write content angle generator** - AI suggests article approach
- [ ] **Write gap analyzer** - Compare research vs SERP to find opportunities
- [ ] **Write pain point extractor** - Analyze research for user frustrations
- [ ] **Write question aggregator** - Combine PAA + research questions
- [ ] **Write word count recommender** - Based on SERP competition

### Week 3: Integration & Export
- [ ] **Update `generator.py`** - Add content brief enrichment step
- [ ] **Add CLI flag** - `--with-content-brief`
- [ ] **Update `GenerationConfig`** - Add brief configuration options
- [ ] **Update CSV export** - Include all new columns
- [ ] **Update JSON export** - Nested brief structure

### Week 4: Testing & Documentation
- [ ] **Test with 10 real keywords** - Validate brief quality
- [ ] **Human evaluation** - Writers rate brief usefulness (1-10)
- [ ] **Update README.md** - Document new features
- [ ] **Create examples** - Show before/after comparison

---

## 🔧 Key Code Changes

### 1. Data Model (`openkeywords/models.py`)

```python
class Keyword(BaseModel):
    """A single keyword with metadata"""
    
    # Existing fields
    keyword: str
    intent: str
    score: int
    cluster_name: Optional[str]
    volume: int
    difficulty: int
    source: str
    aeo_opportunity: int
    has_featured_snippet: bool
    has_paa: bool
    
    # NEW: Content brief fields
    content_angle: Optional[str] = Field(
        default=None,
        description="AI-suggested approach/angle for the article"
    )
    research_context: Optional[str] = Field(
        default=None,
        description="Actual quotes/snippets from Reddit, Quora, forums"
    )
    target_questions: list[str] = Field(
        default_factory=list,
        description="Specific questions the article should answer (from PAA + research)"
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
        description="Suggested article length based on SERP competition"
    )
    top_ranking_content: Optional[str] = Field(
        default=None,
        description="Summary of what's currently ranking on SERP"
    )
    fs_opportunity_type: Optional[str] = Field(
        default=None,
        description="Featured snippet type to target: paragraph, list, table, video"
    )
    internal_links: list[str] = Field(
        default_factory=list,
        description="Related keywords to link to (from same cluster)"
    )
    expert_quotes: Optional[str] = Field(
        default=None,
        description="Expert quotes or stats from research"
    )
```

### 2. Enhanced Research (`openkeywords/researcher.py`)

```python
# In _parse_keywords_response()
valid_keywords.append({
    "keyword": keyword_text,
    "intent": kw.get("intent", "informational"),
    "source": kw.get("source", "research"),
    "is_question": is_question,
    "score": 0,
    
    # NEW: Capture research context
    "research_context": kw.get("quote", ""),  # Actual quote from discussion
    "research_url": kw.get("url", ""),  # Where found
    "pain_point_hint": kw.get("pain_point", ""),  # User frustration mentioned
})
```

**Modify research prompts to extract:**
```python
prompt = f"""Search Reddit for discussions about {industry}.

Find {target_count} keywords and for EACH one, include:
- keyword: the exact phrase
- intent: question|commercial|informational|transactional|comparison
- source: reddit|quora|forum
- quote: EXACT quote from discussion (50-100 words)
- url: where you found it (if available)
- pain_point: what problem/frustration is mentioned

Output JSON:
{{"keywords": [
  {{
    "keyword": "why won't Google index my new pages",
    "intent": "question",
    "source": "reddit",
    "quote": "Posted my new content 2 weeks ago, submitted sitemap, still not indexed. Google Search Console says 'discovered not indexed'. Super frustrating!",
    "url": "reddit.com/r/SEO/...",
    "pain_point": "New content not getting indexed despite following best practices"
  }}
]}}
"""
```

### 3. Content Intelligence Module (NEW: `openkeywords/content_intelligence.py`)

```python
"""
Content Intelligence Generator

Enriches keywords with content briefs using AI analysis of:
- Research data (Reddit, Quora quotes)
- SERP data (featured snippets, top ranking content)
- Clustering data (related keywords)
"""

import asyncio
from typing import List, Dict, Optional
import google.generativeai as genai

class ContentIntelligenceGenerator:
    """Generate content briefs for keywords."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
    
    async def enrich_keywords(
        self,
        keywords: List[Dict],
        research_data: Dict,
        serp_data: Dict,
        cluster_data: Dict,
    ) -> List[Dict]:
        """
        Enrich keywords with content briefs.
        
        Args:
            keywords: List of keyword dicts
            research_data: Research results from researcher.py
            serp_data: SERP analysis from serp_analyzer.py
            cluster_data: Clustering results from generator.py
            
        Returns:
            Keywords enriched with content brief fields
        """
        # Process in batches of 10
        batch_size = 10
        enriched = []
        
        for i in range(0, len(keywords), batch_size):
            batch = keywords[i:i+batch_size]
            batch_enriched = await self._enrich_batch(batch, research_data, serp_data, cluster_data)
            enriched.extend(batch_enriched)
        
        return enriched
    
    async def _enrich_batch(self, batch, research_data, serp_data, cluster_data):
        """Enrich a batch of keywords with content briefs."""
        
        prompt = self._build_enrichment_prompt(batch, research_data, serp_data, cluster_data)
        
        response = await asyncio.to_thread(
            self.model.generate_content,
            prompt,
            generation_config={
                "temperature": 0.7,
                "response_mime_type": "application/json"
            }
        )
        
        briefs = json.loads(response.text)
        
        # Merge briefs with keywords
        for kw, brief in zip(batch, briefs.get("briefs", [])):
            kw.update({
                "content_angle": brief.get("content_angle"),
                "target_questions": brief.get("target_questions", []),
                "content_gap": brief.get("content_gap"),
                "audience_pain_point": brief.get("audience_pain_point"),
                "recommended_word_count": brief.get("recommended_word_count"),
                "top_ranking_content": brief.get("top_ranking_content"),
            })
        
        return batch
    
    def _build_enrichment_prompt(self, batch, research_data, serp_data, cluster_data):
        """Build prompt for batch content brief generation."""
        
        keywords_context = "\n".join([
            f"- {kw['keyword']} (intent: {kw['intent']}, research: {kw.get('research_context', 'N/A')[:100]}...)"
            for kw in batch
        ])
        
        return f"""You are a content strategist. For each keyword below, generate a content brief.

KEYWORDS:
{keywords_context}

For EACH keyword, provide:

1. content_angle: Specific approach for the article (50-100 words)
   - What type of article? (guide, comparison, how-to, listicle)
   - What angle/unique perspective?
   - What structure/format?

2. target_questions: List of 5-7 specific questions to answer
   - From PAA (if available)
   - From research context
   - Inferred from intent

3. content_gap: What's missing from current content (50-100 words)
   - Based on SERP analysis
   - Based on research pain points
   - What unique value can we add?

4. audience_pain_point: Specific problem this addresses (30-50 words)
   - From research context if available
   - Inferred from keyword intent

5. recommended_word_count: Integer (600-3000)
   - Based on intent type
   - Based on competition (if SERP data available)

6. top_ranking_content: Summary of SERP (if data available, 50-100 words)
   - What types of content rank?
   - Common strengths/weaknesses?

Output JSON:
{{
  "briefs": [
    {{
      "keyword": "keyword text",
      "content_angle": "...",
      "target_questions": ["...", "..."],
      "content_gap": "...",
      "audience_pain_point": "...",
      "recommended_word_count": 1800,
      "top_ranking_content": "..."
    }}
  ]
}}
"""
```

### 4. Update Generator Pipeline (`openkeywords/generator.py`)

```python
async def generate(self, company: CompanyInfo, config: GenerationConfig):
    """Generate keywords with optional content briefs."""
    
    # Existing steps...
    keywords = await self._generate_keywords(...)
    keywords = await self._deduplicate(keywords)
    keywords = await self._score_keywords(keywords)
    keywords = await self._cluster_keywords(keywords)
    
    # NEW STEP: Enrich with content briefs
    if config.enable_content_brief:
        logger.info("Generating content briefs...")
        from .content_intelligence import ContentIntelligenceGenerator
        
        brief_gen = ContentIntelligenceGenerator(api_key=self.api_key)
        keywords = await brief_gen.enrich_keywords(
            keywords=keywords,
            research_data=research_results,
            serp_data=serp_analyses,
            cluster_data=cluster_assignments,
        )
        logger.info("Content briefs generated")
    
    # Return results
    return GenerationResult(keywords=keywords, ...)
```

### 5. CLI Flag (`openkeywords/cli.py`)

```python
@click.command()
@click.option("--with-content-brief", is_flag=True, help="Generate full content briefs")
def generate(..., with_content_brief):
    """Generate keywords with optional content briefs."""
    
    config = GenerationConfig(
        target_count=count,
        enable_research=with_research,
        enable_serp_analysis=with_serp,
        enable_content_brief=with_content_brief,  # NEW
    )
    
    result = await generator.generate(company, config)
```

---

## 🧪 Testing Checklist

### Manual Testing
- [ ] Generate 5 commercial keywords → Check brief quality
- [ ] Generate 5 question keywords → Check PAA integration
- [ ] Generate 5 informational keywords → Check research depth
- [ ] Test with/without research → Verify fallback behavior
- [ ] Test with/without SERP → Verify optional features

### Quality Checks
- [ ] Content angles are specific and actionable (not generic)
- [ ] Research context includes real quotes (not invented)
- [ ] Target questions are relevant and comprehensive
- [ ] Content gaps identify real opportunities
- [ ] Word count recommendations are reasonable (600-3000)

### Performance Testing
- [ ] 50 keywords with briefs: < 60 seconds total
- [ ] Memory usage acceptable (< 500MB)
- [ ] Cost per keyword: < $0.001

---

## 📊 Success Metrics

### Quality Metrics (Target)
- [ ] Brief completeness: >90% (all fields populated)
- [ ] Writer satisfaction: 8/10+ rating
- [ ] Time saved: 60+ min per article

### Technical Metrics (Target)
- [ ] Generation time: <60s for 50 keywords
- [ ] Cost per keyword: <$0.001
- [ ] Error rate: <5%

---

## 🎯 Priority Order

### P0 (Must Have) - Week 1-2
1. ✅ Data model updates (`models.py`)
2. ✅ Content angle generation
3. ✅ Research context capture
4. ✅ Target questions aggregation

### P1 (High Value) - Week 3
5. ✅ Content gap analysis
6. ✅ Pain point extraction
7. ✅ Word count recommendation
8. ✅ SERP context summary

### P2 (Nice to Have) - Week 4
9. ⚠️ Internal links suggestion (easy - from clustering)
10. ⚠️ Expert quotes extraction (harder - requires deeper parsing)

---

## 💡 Quick Wins

These can be implemented FAST with high impact:

### 1. Internal Links (5 minutes)
```python
# In generator.py after clustering
for kw in keywords:
    cluster = kw.get("cluster_name")
    related = [k["keyword"] for k in keywords if k["cluster_name"] == cluster][:5]
    kw["internal_links"] = [r for r in related if r != kw["keyword"]]
```

### 2. Word Count Recommendation (10 minutes)
```python
def recommend_word_count(intent: str, has_serp: bool, competition: int) -> int:
    """Quick word count recommendation."""
    if intent == "transactional":
        return 800  # Simple how-to
    elif intent == "commercial":
        return 1800 if competition > 50 else 1200
    elif intent == "question":
        return 1500
    else:
        return 1200  # Default informational
```

### 3. Featured Snippet Type (10 minutes)
```python
def infer_fs_type(keyword: str, intent: str) -> str:
    """Infer featured snippet target type."""
    if intent == "commercial" and "best" in keyword.lower():
        return "table"
    elif keyword.lower().startswith(("how to", "how do")):
        return "list"
    elif keyword.lower().startswith(("what is", "what are")):
        return "paragraph"
    else:
        return "paragraph"  # Default
```

---

## 📚 Resources

### Documentation to Update
- [ ] `README.md` - Add content brief section
- [ ] `examples/with_content_brief.py` - New example
- [ ] `CONTENT_BRIEF_ENHANCEMENT.md` - Full spec (already created ✅)
- [ ] `INTEGRATION_WITH_BLOG_WRITER.md` - Integration guide (already created ✅)

### External References
- [Featured Snippet Types (Ahrefs)](https://ahrefs.com/blog/featured-snippets/)
- [Content Brief Templates](https://www.semrush.com/blog/content-brief/)
- [SERP Analysis Guide](https://moz.com/learn/seo/serp-features)

---

## 🤝 Next Steps

1. **Review this plan** - Confirm approach
2. **Prioritize features** - What's P0 vs P1?
3. **Allocate time** - When to implement?
4. **Test with real keywords** - Validate assumptions
5. **Iterate** - Refine based on writer feedback

---

## ❓ Questions to Resolve

1. Should briefs be regenerated if SERP changes? (Recommendation: Manual for now)
2. How to handle brief quality for low-research keywords? (Recommendation: Mark as "limited_data")
3. Should we expose brief quality score to users? (Recommendation: Internal only)
4. Integration timeline with SCAILE system? (Recommendation: After OpenKeywords testing)

---

**Ready to transform OpenKeywords into a content intelligence platform!** 🚀

