# 🔗 Integration: OpenKeywords → Blog-Writer Pipeline

## Current Workflow (Manual, Disconnected)

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Generate Keywords (OpenKeywords)               │
├─────────────────────────────────────────────────────────┤
│ $ openkeywords generate --company "Acme" --count 50    │
│ Output: keywords.csv (50 keywords)                      │
└─────────────────────────────────────────────────────────┘
                         ↓ MANUAL
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Manual Research (Writer)                       │
├─────────────────────────────────────────────────────────┤
│ - Read keywords.csv                                     │
│ - Research each keyword manually (45-60 min each)      │
│ - Create content brief in Google Docs                  │
│ - Submit brief for approval                            │
└─────────────────────────────────────────────────────────┘
                         ↓ MANUAL
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Upload to SCAILE System                        │
├─────────────────────────────────────────────────────────┤
│ - Manually enter keyword into Google Sheet             │
│ - Copy brief details                                   │
│ - Trigger blog-writer service                          │
└─────────────────────────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────┐
│ STEP 4: Blog Generation (blog-writer)                  │
├─────────────────────────────────────────────────────────┤
│ - Blog-writer receives minimal input:                  │
│   * primary_keyword                                    │
│   * company_name                                       │
│   * internal_links (manual)                            │
│ - NO research context                                  │
│ - NO content angle                                     │
│ - NO SERP intelligence                                 │
└─────────────────────────────────────────────────────────┘

Time per keyword: 60-90 minutes (mostly manual research)
Quality: Dependent on writer's research depth
Scalability: Low (manual bottleneck)
```

---

## Proposed Workflow (Automated, Integrated)

```
┌─────────────────────────────────────────────────────────┐
│ STEP 1: Generate Keywords WITH Content Briefs          │
├─────────────────────────────────────────────────────────┤
│ $ openkeywords generate \                              │
│     --company "Acme Software" \                        │
│     --industry "B2B SaaS" \                            │
│     --with-research \         # Reddit, Quora quotes   │
│     --with-serp \             # SERP intelligence      │
│     --with-content-brief \    # Full content briefs    │
│     --count 50 \                                       │
│     --output keywords_with_briefs.json                 │
│                                                        │
│ Output: Rich JSON with EVERYTHING blog-writer needs    │
└─────────────────────────────────────────────────────────┘
                         ↓ AUTOMATED
┌─────────────────────────────────────────────────────────┐
│ STEP 2: Import to SCAILE System (API/Script)           │
├─────────────────────────────────────────────────────────┤
│ Script: import_keywords_to_scaile.py                   │
│                                                        │
│ For each keyword in keywords_with_briefs.json:         │
│   1. Insert into `keywords` table                     │
│   2. Store content brief in JSONB column              │
│   3. Link to client project                           │
│   4. Set status: "ready_for_generation"               │
│                                                        │
│ Time: < 5 seconds for 50 keywords                     │
└─────────────────────────────────────────────────────────┘
                         ↓ AUTOMATED
┌─────────────────────────────────────────────────────────┐
│ STEP 3: Blog Generation (Enhanced blog-writer)         │
├─────────────────────────────────────────────────────────┤
│ blog-writer receives RICH input:                       │
│   ✅ primary_keyword                                   │
│   ✅ company_name                                      │
│   ✅ internal_links (auto from cluster)               │
│   ✅ content_angle                                     │
│   ✅ research_context (Reddit/Quora quotes)           │
│   ✅ target_questions (PAA + research)                │
│   ✅ content_gap (what's missing from SERP)           │
│   ✅ audience_pain_point                              │
│   ✅ recommended_word_count                           │
│   ✅ fs_opportunity_type (featured snippet target)    │
│   ✅ top_ranking_content (SERP summary)               │
│                                                        │
│ AI generates article with:                             │
│   - Specific angle already defined                    │
│   - Real quotes from research                         │
│   - Questions to answer (from PAA)                    │
│   - Gaps to fill                                      │
│   - Optimal structure for featured snippet            │
└─────────────────────────────────────────────────────────┘

Time per keyword: 5-10 minutes (generation only)
Quality: Consistently high (grounded in research)
Scalability: High (fully automated pipeline)
```

---

## 📊 Data Flow Schema

### OpenKeywords Output → SCAILE Database

```json
{
  "keyword": "best project management software for small teams",
  "intent": "commercial",
  "score": 92,
  "cluster_name": "Product Comparison",
  "volume": 1200,
  "difficulty": 45,
  
  "content_brief": {
    "content_angle": "Comparison guide with decision matrix focusing on team size, budget, and key features",
    "research_context": "Reddit r/startups: 'We tried 5 PM tools as a 10-person startup. Asana was overkill...'",
    "target_questions": [
      "What is the best project management software for small teams?",
      "How much does project management software cost?",
      "What features should I look for?"
    ],
    "content_gap": "Most reviews cover enterprise tools. Missing: detailed comparison for 5-15 person teams with limited budget.",
    "audience_pain_point": "Small team leads overwhelmed by complex enterprise tools",
    "recommended_word_count": 1800,
    "top_ranking_content": "Top 5 results are listicles. Forbes Advisor: broad comparison. Capterra: feature-heavy...",
    "fs_opportunity_type": "table",
    "internal_links": ["project management for startups", "free project management tools"]
  }
}
```

### SCAILE Database Schema

```sql
-- Add content_brief column to keywords table
ALTER TABLE keywords 
ADD COLUMN content_brief JSONB DEFAULT NULL;

-- Index for fast retrieval
CREATE INDEX idx_keywords_content_brief ON keywords USING gin(content_brief);

-- Example insert
INSERT INTO keywords (
  keyword, 
  intent, 
  score, 
  cluster_name, 
  volume, 
  difficulty,
  project_id,
  content_brief,
  status
) VALUES (
  'best project management software for small teams',
  'commercial',
  92,
  'Product Comparison',
  1200,
  45,
  'proj_123',
  '{
    "content_angle": "...",
    "research_context": "...",
    "target_questions": [...],
    ...
  }'::jsonb,
  'ready_for_generation'
);
```

### Blog-Writer Input (Enhanced)

```python
# Current blog-writer input (minimal)
blog_input_old = {
    "primary_keyword": "best project management software",
    "company_name": "Acme Software",
    "internal_links": "project management, remote teams",
}

# NEW blog-writer input (rich)
blog_input_new = {
    # Core fields (unchanged)
    "primary_keyword": "best project management software for small teams",
    "company_name": "Acme Software",
    "company_info": {...},
    "language": "en",
    "country": "US",
    
    # NEW: Content brief fields
    "content_brief": {
        "content_angle": "Comparison guide with decision matrix...",
        "research_quotes": [
            "Reddit r/startups: 'We tried 5 PM tools...'",
            "Quora: 'Small teams need something between...'"
        ],
        "target_questions": [
            "What is the best project management software for small teams?",
            "How much does project management software cost?",
            "What features should I look for?"
        ],
        "content_gap": "Missing: detailed comparison for 5-15 person teams with budget constraints",
        "audience_pain_point": "Small team leads overwhelmed by complex enterprise tools",
        "recommended_word_count": 1800,
        "serp_context": {
            "top_ranking_types": ["listicle", "comparison"],
            "featured_snippet_type": "table",
            "avg_word_count": 1850,
            "common_weaknesses": ["enterprise-focused", "too generic"]
        }
    },
    
    # Auto-generated from cluster
    "internal_links": "project management for startups, free project management tools, agile project management",
}
```

---

## 🔧 Implementation: Enhanced Blog-Writer Prompt

### Current Prompt (Generic)

```python
# blog-writer/pipeline/prompts/main_article.py
prompt = f"""Write a comprehensive blog article about {primary_keyword}.

Target audience: {target_audience}
Word count: 2000-2500 words
Include: lists, statistics, examples

Write in {language} for {country} market."""
```

### Enhanced Prompt (With Brief)

```python
# blog-writer/pipeline/prompts/main_article.py (ENHANCED)

def get_main_article_prompt(
    primary_keyword: str,
    company_name: str,
    company_info: Optional[Dict] = None,
    content_brief: Optional[Dict] = None,  # NEW
    language: str = "en",
    country: str = "US",
    internal_links: str = "",
):
    """Generate article prompt with optional content brief enhancement."""
    
    # Base prompt (existing logic)
    base_prompt = f"""Write a comprehensive blog article about: {primary_keyword}
    
Target audience: {target_audience}
Word count target: 2000-2500 words
Language: {language}
Market: {country}"""
    
    # ENHANCEMENT: Add content brief context if available
    if content_brief:
        brief_section = f"""

## CONTENT BRIEF (Research Intelligence)

### Recommended Angle
{content_brief.get('content_angle', 'N/A')}

### Target Audience Pain Point
{content_brief.get('audience_pain_point', 'N/A')}

### Questions to Answer (from PAA + Research)
{chr(10).join(f"- {q}" for q in content_brief.get('target_questions', []))}

### Research Context (Real User Quotes)
{content_brief.get('research_context', 'N/A')}

### Content Gap (What's Missing from SERP)
{content_brief.get('content_gap', 'N/A')}

### SERP Context
- Top ranking content types: {', '.join(content_brief.get('serp_context', {}).get('top_ranking_types', []))}
- Featured snippet opportunity: {content_brief.get('serp_context', {}).get('featured_snippet_type', 'none')}
- Recommended word count: {content_brief.get('recommended_word_count', 2000)} words

### Optimization Instructions
1. Structure article to target featured snippet type: {content_brief.get('fs_opportunity_type', 'paragraph')}
2. Address the content gap explicitly: {content_brief.get('content_gap', 'N/A')}
3. Include direct quotes from research to build authenticity
4. Answer all PAA questions within the article
5. Write from the perspective of someone who understands the pain point"""
        
        base_prompt += brief_section
    
    # Add rest of standard instructions
    base_prompt += f"""

## STRUCTURE REQUIREMENTS
- Start with comparison table (if commercial intent)
- Include {UNIVERSAL_STANDARDS['list_count']} lists
- {UNIVERSAL_STANDARDS['citation_count']} authoritative citations
- Internal links: {internal_links}

## QUALITY STANDARDS
- Research depth: {UNIVERSAL_STANDARDS['data_points_min']} statistics
- Examples: {UNIVERSAL_STANDARDS['examples_min']} specific examples
- Case studies: {UNIVERSAL_STANDARDS['case_studies_min']} concrete cases"""
    
    return base_prompt
```

---

## 🔄 Full Integration Script

```python
#!/usr/bin/env python3
"""
Import OpenKeywords output to SCAILE system and trigger blog generation.

Usage:
    python import_keywords_to_scaile.py \
        --keywords keywords_with_briefs.json \
        --project-id abc123 \
        --auto-generate
"""

import asyncio
import json
from supabase import create_client
from datetime import datetime

async def import_keywords_with_briefs(
    keywords_file: str,
    project_id: str,
    auto_generate: bool = False
):
    """Import keywords with content briefs to SCAILE system."""
    
    # Load keywords
    with open(keywords_file) as f:
        data = json.load(f)
    
    keywords = data.get('keywords', [])
    print(f"📥 Importing {len(keywords)} keywords with content briefs...")
    
    # Connect to Supabase
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_SERVICE_ROLE_KEY')
    )
    
    imported = []
    for kw in keywords:
        # Prepare content brief JSONB
        content_brief = {
            'content_angle': kw.get('content_angle'),
            'research_context': kw.get('research_context'),
            'target_questions': kw.get('target_questions', []),
            'content_gap': kw.get('content_gap'),
            'audience_pain_point': kw.get('audience_pain_point'),
            'recommended_word_count': kw.get('recommended_word_count'),
            'top_ranking_content': kw.get('top_ranking_content'),
            'fs_opportunity_type': kw.get('fs_opportunity_type'),
            'internal_links': kw.get('internal_links', []),
            'serp_context': {
                'has_featured_snippet': kw.get('has_featured_snippet'),
                'has_paa': kw.get('has_paa'),
                'aeo_opportunity': kw.get('aeo_opportunity'),
            }
        }
        
        # Insert into database
        result = supabase.table('keywords').insert({
            'project_id': project_id,
            'keyword': kw['keyword'],
            'intent': kw.get('intent', 'informational'),
            'score': kw.get('score', 0),
            'cluster_name': kw.get('cluster_name'),
            'volume': kw.get('volume', 0),
            'difficulty': kw.get('difficulty', 50),
            'source': kw.get('source', 'openkeywords'),
            'content_brief': content_brief,
            'status': 'ready_for_generation' if auto_generate else 'imported',
            'created_at': datetime.utcnow().isoformat(),
        }).execute()
        
        imported.append(result.data[0]['id'])
        print(f"✅ Imported: {kw['keyword']}")
    
    print(f"\n🎉 Successfully imported {len(imported)} keywords!")
    
    # Optionally trigger blog generation
    if auto_generate:
        print(f"\n🚀 Triggering blog generation for {len(imported)} keywords...")
        
        for keyword_id in imported:
            # Call s5-generate-blogs Edge Function
            response = await supabase.functions.invoke(
                's5-generate-blogs',
                invoke_options={
                    'body': {
                        'keyword_id': keyword_id,
                        'use_content_brief': True,  # NEW flag
                    }
                }
            )
            print(f"   → Triggered generation for keyword {keyword_id}")
    
    return imported

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('--keywords', required=True, help='Path to keywords JSON')
    parser.add_argument('--project-id', required=True, help='SCAILE project ID')
    parser.add_argument('--auto-generate', action='store_true', help='Auto-trigger blog generation')
    
    args = parser.parse_args()
    
    asyncio.run(import_keywords_with_briefs(
        args.keywords,
        args.project_id,
        args.auto_generate
    ))
```

---

## 📈 Impact Analysis

### Time Savings Per Keyword

| Task | Current (Manual) | With Integration | Savings |
|------|------------------|------------------|---------|
| Keyword research | 15 min | 0 min (automated) | **15 min** |
| SERP analysis | 20 min | 0 min (automated) | **20 min** |
| Reddit/Quora research | 25 min | 0 min (automated) | **25 min** |
| Content brief creation | 15 min | 0 min (automated) | **15 min** |
| Manual data entry | 5 min | 0 min (scripted) | **5 min** |
| **Total per keyword** | **80 min** | **0 min** | **80 min** |

### Scale Impact (50 keywords/month)

- **Manual workflow:** 80 min × 50 = **4,000 minutes = 66 hours/month**
- **Automated workflow:** 0 min × 50 = **0 hours/month**
- **Time saved:** **66 hours/month = 8+ working days**

### Cost Analysis

| Item | Cost |
|------|------|
| OpenKeywords generation (50 keywords with briefs) | $0.05 |
| Writer time saved (66 hours @ $50/hour) | **$3,300** |
| **ROI** | **66,000x** |

---

## 🚀 Rollout Plan

### Phase 1: Data Model (Week 1)
- [ ] Add `content_brief` JSONB column to `keywords` table
- [ ] Create indexes for fast retrieval
- [ ] Update TypeScript types in Edge Functions

### Phase 2: OpenKeywords Enhancement (Week 2)
- [ ] Implement content brief generation in OpenKeywords
- [ ] Add `--with-content-brief` CLI flag
- [ ] Test output quality with real keywords

### Phase 3: Import Script (Week 3)
- [ ] Create `import_keywords_to_scaile.py` script
- [ ] Test import with sample keywords
- [ ] Add validation and error handling

### Phase 4: Blog-Writer Enhancement (Week 4)
- [ ] Modify `get_main_article_prompt()` to accept content brief
- [ ] Update `s5-generate-blogs` to pass content brief to blog-writer
- [ ] Add `use_content_brief` flag to blog generation API

### Phase 5: Testing & Validation (Week 5)
- [ ] Generate 10 test keywords with full briefs
- [ ] Import to SCAILE system
- [ ] Generate blogs with vs without briefs
- [ ] Compare quality scores (human evaluation)

### Phase 6: Production Rollout (Week 6)
- [ ] Document new workflow in `ARCHITECTURE.md`
- [ ] Update client onboarding to use new flow
- [ ] Train team on new system
- [ ] Monitor quality metrics

---

## 🎯 Success Metrics

### Quality Metrics
- [ ] Content brief completeness: >90% (all fields populated)
- [ ] Blog quality score: 9.0/10+ (current baseline: 8.5/10)
- [ ] Featured snippet win rate: +20% (with FS optimization)
- [ ] Time on page: +30% (better content targeting)

### Efficiency Metrics
- [ ] Time per keyword: 80 min → 5 min (**94% reduction**)
- [ ] Keywords processed/month: 50 → 200 (**4x scale**)
- [ ] Writer satisfaction: Survey before/after

### Business Metrics
- [ ] Client satisfaction (content relevance)
- [ ] Content approval rate (first submission)
- [ ] Revision requests: -50% (better initial quality)

---

## 🤔 Open Questions

1. **Should content briefs be editable in SCAILE UI?**
   - Option A: Read-only (regenerate if changes needed)
   - Option B: Editable JSONB in admin panel
   - **Recommendation:** Start read-only, add editing later if needed

2. **How to handle brief updates when SERP changes?**
   - Option A: Manual re-generation
   - Option B: Automated monthly refresh
   - **Recommendation:** Manual for now, scheduled later

3. **Should we show brief quality score to clients?**
   - Pros: Transparency, trust
   - Cons: May over-focus on metric vs content quality
   - **Recommendation:** Internal metric only

4. **Integration with existing keywords (no briefs)?**
   - Option A: Batch generate briefs for existing keywords
   - Option B: Only new keywords get briefs
   - **Recommendation:** Batch generate for high-priority keywords

---

**This integration transforms openkeywords from a standalone tool into the intelligence engine powering SCAILE's entire content production pipeline.** 🚀

