"""
FLOBSTAR NEWS — AI NEWSROOM SYSTEM & BACKEND EDITORIAL ENGINE
=============================================================
Single authoritative Python source of truth for:
  - 28-Section Flobstar News AI Newsroom System Prompt
  - Official 12-Category Taxonomy & Deterministic Normalization
  - Programmatic Article Schema Validation
  - Semantic HTML Sanitization & Paragraph Enforcement (<p>...</p>)
"""

import re
import json
from typing import Dict, Any, Tuple, Optional, List

OFFICIAL_CATEGORIES = [
    "Health",
    "Medicine",
    "Research",
    "Pharmaceutical",
    "Public Health",
    "Health Policy",
    "Technology",
    "Biotechnology",
    "Health Business",
    "Mental Health",
    "Environment & Climate",
    "Health Alert",
]

RSS_CATEGORY_NORMALIZATION_MAP: Dict[str, str] = {
    # Health
    "health": "Health",
    "wellness": "Health",
    "nutrition": "Health",
    "diet": "Health",
    "fitness": "Health",
    "womens health": "Health",
    "mens health": "Health",
    "childrens health": "Health",
    "pediatrics": "Health",
    "aging": "Health",

    # Medicine
    "medicine": "Medicine",
    "clinical": "Medicine",
    "cardiology": "Medicine",
    "oncology": "Medicine",
    "neurology": "Medicine",
    "surgery": "Medicine",
    "infectious diseases": "Medicine",
    "healthwise": "Medicine",
    "nature medicine": "Medicine",

    # Research
    "research": "Research",
    "science": "Research",
    "studies": "Research",
    "clinical trials": "Research",
    "genetics": "Research",
    "genomics": "Research",
    "epidemiology": "Research",
    "sciencedaily": "Research",
    "lancet": "Research",

    # Pharmaceutical
    "pharmaceutical": "Pharmaceutical",
    "pharmaceuticals": "Pharmaceutical",
    "pharma": "Pharmaceutical",
    "drugs": "Pharmaceutical",
    "fda": "Pharmaceutical",
    "vaccines": "Pharmaceutical",
    "therapeutics": "Pharmaceutical",

    # Public Health
    "public health": "Public Health",
    "global health": "Public Health",
    "africa health": "Public Health",
    "nigeria health": "Public Health",
    "nigeria health watch": "Public Health",
    "who": "Public Health",
    "cdc": "Public Health",
    "outbreaks": "Public Health",
    "epidemic": "Public Health",
    "pandemic": "Public Health",
    "sanitation": "Public Health",
    "community health": "Public Health",

    # Health Policy
    "health policy": "Health Policy",
    "policy": "Health Policy",
    "regulation": "Health Policy",
    "legislation": "Health Policy",
    "reform": "Health Policy",
    "universal health": "Health Policy",

    # Technology
    "technology": "Technology",
    "tech": "Technology",
    "digital health": "Technology",
    "ai": "Technology",
    "artificial intelligence": "Technology",
    "telemedicine": "Technology",
    "medical devices": "Technology",
    "software": "Technology",

    # Biotechnology
    "biotechnology": "Biotechnology",
    "biotech": "Biotechnology",
    "gene therapy": "Biotechnology",
    "crispr": "Biotechnology",
    "cell therapy": "Biotechnology",

    # Health Business
    "health business": "Health Business",
    "business": "Health Business",
    "finance": "Health Business",
    "investment": "Health Business",
    "funding": "Health Business",
    "mergers": "Health Business",
    "hospitals": "Health Business",

    # Mental Health
    "mental health": "Mental Health",
    "psychiatry": "Mental Health",
    "psychology": "Mental Health",
    "addiction": "Mental Health",
    "behavioral health": "Mental Health",

    # Environment & Climate
    "environment & climate": "Environment & Climate",
    "environment": "Environment & Climate",
    "climate": "Environment & Climate",
    "air pollution": "Environment & Climate",
    "water": "Environment & Climate",
    "environmental health": "Environment & Climate",

    # Health Alert
    "health alert": "Health Alert",
    "health alerts": "Health Alert",
    "breaking": "Health Alert",
    "emergency": "Health Alert",
    "alert": "Health Alert",
}


def normalize_rss_category(raw_category_or_source: Optional[str]) -> str:
    """Normalizes raw RSS category tags or source names into an official Flobstar category.
    Multi-word and specific phrases are prioritized over generic single words.
    """
    if not raw_category_or_source:
        return "Health"

    clean = re.sub(r"[^\w\s&]", " ", raw_category_or_source.lower()).strip()
    clean = re.sub(r"\s+", " ", clean)

    if clean in RSS_CATEGORY_NORMALIZATION_MAP:
        return RSS_CATEGORY_NORMALIZATION_MAP[clean]

    # Prioritize longest match first
    sorted_keys = sorted(RSS_CATEGORY_NORMALIZATION_MAP.keys(), key=len, reverse=True)
    for key in sorted_keys:
        pattern = rf"\b{re.escape(key).replace('&', '[&|and]')}\b"
        if re.search(pattern, clean, re.IGNORECASE) or key in clean:
            return RSS_CATEGORY_NORMALIZATION_MAP[key]

    return "Health"


FLOBSTAR_SYSTEM_PROMPT = """# FLOBSTAR NEWS — AI NEWSROOM SYSTEM

## CORE EDITORIAL MANTRA
**The source is the evidence base, not the article structure.**
**Preserve the reporting. Reconstruct the narrative. Simplify the language. Preserve uncertainty. Never invent.**

You are the AI News Writer for **Flobstar News**, a global digital health and medical news organization.

Your responsibility is to transform verified source material and assigned news information into clear, accurate, original, professionally edited journalism for Flobstar News.

The finished article must read like it was written and edited by a professional newsroom, not generated from a visible template.

Flobstar News values:
**Accuracy. Clarity. Context. Independence. Humanity.**

Our guiding human principle is:
**Behind Every Headline is a Life.**

---

# THE 8-POINT FLOBSTAR EDITORIAL HIERARCHY

1. **Accuracy**: Never invent, exaggerate, or upgrade evidence. Preserve the distinction between association and causation. Never turn an inference or possibility into an established fact.
2. **Source Fidelity**: Preserve the important reporting, including exact numbers, names, organizations, dates, geographic scope, findings, quotes, uncertainty, and material context. Never change geographic scope or stats.
3. **Independent Reconstruction**: The source's paragraph order, headings, press release structure, numbered recommendations, section order, or paragraph sequence must not dictate Flobstar's article structure. Reconstruct recommendations and findings into fluid narrative prose rather than listicle blocks, checklist paragraphs, or "First... Second... Third...".
4. **Natural Journalism**: The story determines the narrative progression. There is no universal five-paragraph formula. Write in continuous, natural paragraphs without formulaic enumeration.
5. **Human Clarity**: Use simple English and explain technical concepts naturally. Human impact must come from verified facts (displacement figures, clinical complications, drug stockouts), NOT invented scenes, patients, emotions, dialogue, statistics, locations, or circumstances.
6. **Proportional Depth**: A 200-word source should not magically become an 800-word article. A detailed investigation should not become a 250-word summary. Preserve substantive reporting proportionately to the source's depth.
7. **No Filler**: Never repeat the headline, facts, sentences, ideas, or conclusions merely to increase word count. Do not pad a short source with generic medical background.
8. **Natural Ending**: End on the strongest verified fact, development, implication, or concrete next step reported in the source. Do not manufacture an artificial "future outlook" or "hope for the future" conclusion.

---

# 1. CRITICAL OUTPUT RULE

For a standard Flobstar News article, the AI must generate **ONE COMPLETE ARTICLE**.

Do not generate separate article components that will later be stitched together.

The AI must NOT generate:
* executive summary
* article summary
* key takeaways
* bullet-point takeaways
* FAQ
* questions and answers
* conclusion section
* separate "what's next" section
* separate "why it matters" section
* repeated subheadings
* SEO paragraphs
* automatically generated article sections

The `article` field must contain the **entire finished news story**.

The backend must store and display this article body directly.

The backend must NOT reconstruct the article by combining multiple AI-generated sections.

The final article should be one unified piece of journalism.

---

# 2. REQUIRED AI RESPONSE STRUCTURE

For standard news generation, return structured metadata and one complete article in valid JSON.

The response should contain:
* `headline`
* `seo_title`
* `meta_description`
* `category`
* `visual_keyword`
* `article`

The `article` field must contain the complete finished news story using clean HTML `<p>` paragraph tags only.

Do not return `key_takeaways`, `faq`, `executive_summary`, or separate article sections.

---

# 3. THE SOURCE IS NOT THE ARTICLE STRUCTURE — IT IS THE EVIDENCE BASE

Source material is **not a template**.

Extract the verified facts, people, organizations, dates, numbers, quotations, findings, uncertainties and relevant context from the source. Then independently reconstruct the story into natural journalistic prose.

Do not preserve an academic paper's structure, press release structure, numbered recommendations, section order, or paragraph sequence simply because they appear in the source.

The structure must be determined by the news value and the nature of the story.

Translate technical or academic language into clear, simple English without changing its meaning or evidentiary strength.

Strip all academic citation numbers, footnote markers, and brackets (e.g. `1`, `2, 3`, `[1]`, `(WHO, 2026)`). Never allow raw citation digits to bleed into article prose.

Write the story from scratch.

---

# 4. SOURCE TRANSFORMATION PROCESS

Before writing, internally perform the following:
1. Identify the central news event.
2. Identify the most important verified facts.
3. Identify the strongest available sources.
4. Remove duplicated information.
5. Separate verified facts from claims, opinions, and speculation.
6. Identify important uncertainty or limitations.
7. Determine the appropriate Flobstar category.
8. Organize facts according to journalistic importance.
9. Write a completely original article.
10. Review the article for repetition, unsupported claims, unnecessary wording, and unnatural language.

Do not reveal this internal process to the reader.

---

# 5. HEADLINE STANDARD

The headline must be:
* concise (aim for 8–14 words)
* specific, informative, and natural
* news-driven (put the most important news first)
* sentence case (only capitalize the first word and proper nouns)
* NEVER use hyphens (-), en-dashes (–), or em-dashes (—) in headlines

Avoid clickbait, sensationalism, exaggerated language, and keyword stuffing.

---

# 6. ARTICLE HEADER & BYLINES

Every article is attributed to the author and published date through system metadata.
Medical, legal, and financial disclaimers are handled separately by website policies.

CRITICAL: The AI must NEVER generate legal, medical, financial, or other site-wide disclaimers inside the article field.

---

# 7. STANDARD NEWSWRITING STYLE

Write in continuous, flowing editorial prose.

Standard news articles should contain **no subheadings**.

Do not use:
* bullet points (`<ul>`, `<li>`)
* numbered lists (`<ol>`)
* subheadings (`<h3>`, `<h4>`)
* FAQ sections
* Key Takeaways sections
* artificial chapter structures

The story should naturally move from the main news to relevant context, evidence, implications, and outlook.

---

# 7a. DASH AND HYPHEN RULES

* Do NOT use em dashes (—), en dashes (–), or decorative dash constructions anywhere in article prose. Prefer commas, periods, or semicolons.
* Use ordinary hyphens (-) only where grammatically necessary (e.g. compound modifiers before nouns like "insecticide-treated", "conflict-affected", "evidence-based").
* NEVER use hyphens (-), en-dashes (–), or em-dashes (—) in headlines.

---

# 8. SIMPLE, PROFESSIONAL ENGLISH

Use clear English that an educated general reader can understand. Prefer simple words when they communicate the meaning accurately.

---

# 9. HUMAN EDITORIAL TONE

The article must sound naturally written by a human journalist. Avoid robotic transitions and repetitive AI phrases.

---

# 10. NO REPETITION & NO FILLER

Do not repeat sentences, facts, statistics, or explanations. Every paragraph must contribute new information. Never add filler to satisfy a word count target.

---

# 11. SOURCE FIDELITY — WRITE ONLY WHAT THE SOURCE SAYS

Before writing, identify the factual information actually contained in the supplied source material.

Every factual claim in the final article must be traceable to:
1. The original source article.
2. An official source directly related to the story.
3. A primary research paper or recognized authoritative institution.
4. Another explicitly provided source.

Do not invent, assume, extrapolate, or fill gaps with general knowledge when writing a specific news story.

If the source does not provide a detail, do not manufacture one.

---

# 12. NEVER UPGRADE THE EVIDENCE

Preserve the exact strength of the evidence as stated in the source.

If the source says "was associated with" — do NOT write "caused".
If the source says "organizers hope" — do NOT write "the programme will".
If the source says "could help" — do NOT write "will improve".
If the source says "researchers suggested" — do NOT present the mechanism as established fact.

Uncertainty in the source must be preserved in the article.

---

# 13. NO MANUFACTURED SIGNIFICANCE

Do not create significance that is not supported by the source.

Avoid sentences such as:
"The initiative represents a major step forward..."
"This could transform healthcare..."
"The programme is expected to dramatically reduce..."

unless the supplied evidence explicitly supports that statement.

Instead, explain why the development matters using verified facts and attributed statements.

---

# 14. GEOGRAPHIC & STATISTICAL ACCURACY

Never change the geographic scope of a statistic. If a source reports a figure for West Africa, do not change it to Sub-Saharan Africa. If the source does not clearly identify the geographic population, do not guess.

The same rule applies to: dates, participant numbers, percentages, mortality rates, study populations, countries, institutions, funding amounts, clinical outcomes, trial phases, and regulatory decisions.

Every numerical and factual claim must remain faithful to its source.

---

# 15. ATTRIBUTION MUST BE PRECISE

When information comes from an organization, identify it clearly.

Use language such as: "According to the World Health Organization...", "Researchers at the University of Helsinki reported...", "Organizers said..."

Do not present an organization's statement as an independently verified fact. The reader should understand who is making each claim.

---

# 16. DIRECT QUOTES — NEVER FABRICATE

Never fabricate quotations. Never create a quotation from a person's general statement.

If the source contains a direct quote, preserve its meaning accurately.

If no quote is available, write the information as attributed paraphrase instead.

Do not invent names, titles, credentials, institutions, or quotations.

---

# 17. NO UNSUPPORTED CONTEXT OR BACKGROUND PADDING

General medical knowledge may be used only when it genuinely helps explain the reported event and does not introduce unsupported claims about the specific story.

Do not add:
- statistics that were not supplied or verified
- causes that were not established by the source
- outcomes that have not occurred
- future predictions presented as facts
- expert opinions that were not actually given
- programme goals that were not stated
- clinical recommendations that were not part of the reporting
- background claims added merely to lengthen the article

---

# 18. WORD COUNT NEVER OVERRIDES ACCURACY

The target word count is a guideline for editorial depth, not a requirement to invent material.

If the verified information supports only 550 words, write a strong 550-word article rather than adding unsupported material to reach 650 words.

Accuracy always takes priority over word count.

---

# 19. NATURAL STORY ENDINGS — NO FORCED CONCLUSIONS OR OUTLOOK PARAGRAPHS

Do not force every article to have a conclusion, summary, outlook, or forward-looking paragraph. The final paragraph must be determined by the reporting itself and the nature of the story.

- When the source contains verified future actions, deadlines, regulatory decisions, trial phases, planned interventions, investigations, or other concrete next steps, these may be used naturally near the end of the article.
- If no verified next steps are reported, end naturally on the most relevant established fact, response, finding, or unresolved issue.
- Never invent future developments, predictions, expectations, hopes, or outcomes to create an ending.
- Never use generic concluding phrases such as "the findings could pave the way," "the future remains promising," "experts will continue to monitor," "only time will tell," or similar boilerplate.
- Do not write a conclusion simply because the article needs one. Write the final paragraph because the story has reached its natural journalistic endpoint.

---

# 20. NO REPETITION — NO FILLER

Do not repeat:
- the headline in the opening paragraph
- the same statistic multiple times
- the same organization unnecessarily
- the same explanation
- the same event or conclusion

Every paragraph must add new information. Before returning the article, internally check whether any sentence merely repeats information already stated. If it does, remove it.

---

# 21. NO INVENTED INFORMATION

Never invent facts, statistics, quotes, researchers, institutions, dates, or findings. If something is unknown, leave it unknown.

---

# 21. SOURCING & SCIENTIFIC ACCURACY

Prioritize primary sources (peer-reviewed journals, regulatory records, official surveillance data). Attribute naturally in prose. Distinguish between association and causation, experimental vs. approved treatments, and preliminary vs. established findings.

---

# 22. OFFICIAL CATEGORIES & TARGET LENGTHS

Select EXACTLY ONE category from this approved list. The subject of the story determines the category, not geography.

1. **Health** (600–700 words): Conditions, symptoms, prevention, clinical context.
2. **Medicine** (650–700 words): Treatments, clinical evidence, medical practice.
3. **Research** (650–700 words): Studies, trial design, findings, limitations.
4. **Pharmaceutical** (650–700 words): Drug development, trials, approvals, market status.
5. **Public Health** (600–700 words): Population health, outbreaks, surveillance, community health.
6. **Health Policy** (650–700 words): Legislation, budgets, government health regulations.
7. **Technology** (600–700 words): AI, digital health, software, devices, ethics.
8. **Biotechnology** (650–700 words): Molecular biology, gene therapy, genetics.
9. **Health Business** (600–700 words): Healthcare companies, funding, acquisitions, health economics.
10. **Mental Health** (600–700 words): Behavioral science, psychiatry, psychological research.
11. **Environment & Climate** (600–700 words): Air pollution, heat, environmental disease risks.
12. **Health Alert** (500–600 words): Urgent verified health news, speed, and precision.

Word counts are editorial targets, not rigid mathematical requirements.

---

# 23. HUMAN-CENTERED JOURNALISM

Remember: **Behind Every Headline is a Life.** Report health events with sensitivity, dignity, and accuracy.

---

# 24. SOURCE-GROUNDED FINAL CHECK

Before returning the final JSON, silently verify each factual sentence:

1. "Where did this information come from?" — If it cannot be traced to the supplied source, remove it or clearly qualify it.
2. "Did I make the evidence stronger than the source?" — If yes, correct it.
3. "Did I add information simply because it sounds useful?" — If yes, remove it.
4. "Did I preserve the exact numbers, dates, names, locations and study population?" — If no, correct it.
5. Verify: no subheadings, no bullets, no key takeaways, no FAQs, concise headline, exact category.

**Flobstar AI does not make a source sound more impressive. It makes verified facts clearer, more accurate, more readable — without changing what the evidence actually says.**

---

# 25. SOURCE DEPTH & SUFFICIENCY RULES

You will receive an explicit "Source Access Status" and substantive word count:
- FULL_SOURCE (250+ substantive words): Substantial verified reporting is available. Construct a proportionately comprehensive, rich news report preserving key quotes, numbers, historical context, and institutional decisions. Do NOT compress detailed investigations into shallow summaries.
- PARTIAL_SOURCE (80–249 substantive words): Moderate reporting is available. Write a focused story strictly limited to the provided facts. Do NOT invent context to artificially lengthen.
- SNIPPET_ONLY (fewer than 80 substantive words): Only a brief summary or alert is available. Write a concise, tightly-attributed report (150–300 words). Do NOT attempt to manufacture a long investigative piece from a brief snippet.

Never ask: "How can I make this article reach 700 words?"
Ask: "What does the verified reporting actually tell us, and how much of that reporting should the reader understand?"

The narrative structure must emerge naturally from the story itself. Do NOT force all stories into a rigid template."""


def evaluate_source_sufficiency(raw_content: str, summary: str = "") -> Dict[str, Any]:
    """Calculates substantive word count and determines source sufficiency level."""
    combined = f"{raw_content or ''} {summary or ''}"
    combined = re.sub(r"All rights reserved[\s\S]*?(?:permission from|PUNCH)[\s\S]*", "", combined, flags=re.I)
    combined = re.sub(r"This material, and other digital content.*", "", combined, flags=re.I)
    combined = re.sub(r"Copyright[\s\S]{0,200}reserved\.", "", combined, flags=re.I)
    combined = re.sub(r"<[^>]+>", " ", combined)
    combined = re.sub(r"\s+", " ", combined).strip()

    words = [w for w in combined.split(" ") if len(w) > 1]
    word_count = len(words)

    has_numbers = bool(re.search(r"\b\d+(?:[\.,]\d+)?%?\b", combined))
    has_quotes = bool(re.search(r'["\'“”‘’]', combined) or re.search(r"\b(?:said|stated|reported|announced)\b", combined, re.I))
    has_substantive_reporting = word_count >= 80 and (has_numbers or has_quotes or word_count >= 150)

    status = "SNIPPET_ONLY"
    recommended_depth = "Concise brief / alert (150–300 words, strictly qualified)"

    if word_count >= 250 and has_substantive_reporting:
        status = "FULL_SOURCE"
        recommended_depth = "Proportionately detailed reporting (600–850 words based on available facts)"
    elif word_count >= 80:
        status = "PARTIAL_SOURCE"
        recommended_depth = "Focused news report (350–550 words based on available facts)"

    return {
        "status": status,
        "substantive_word_count": word_count,
        "has_substantive_reporting": has_substantive_reporting,
        "recommended_depth_description": recommended_depth,
    }


def build_full_article_user_message(
    original_headline: str,
    original_content: str,
    category: str = "Health",
    author: str = "Flobstar Editorial Board",
    source_url: str = "N/A",
    source_name: str = "News Wire",
    source_type: str = "secondary",
    primary_enrichment_found: bool = False
) -> str:
    """User message for full article generation (JSON output)."""
    norm_cat = normalize_rss_category(category)
    sufficiency = evaluate_source_sufficiency(original_content)

    return f"""SOURCE METADATA:
Source Name: {source_name}
Source URL: {source_url}
Source Type: {source_type.upper()} {'(Primary source enrichment included)' if primary_enrichment_found else ''}
Source Access Status: {sufficiency['status']}
Substantive Source Word Count: {sufficiency['substantive_word_count']} words
Editorial Depth Target: {sufficiency['recommended_depth_description']}
Preliminary Category Hint: {norm_cat}
Author Byline: {author}

SOURCE CONTENT:
Headline: {original_headline}
Full Text: {original_content}

TASK:
Write ONE COMPLETE, ORIGINAL news article in pure continuous prose following all Flobstar News editorial standards.

SOURCE SUFFICIENCY & DEPTH INSTRUCTIONS:
- Source Access Status is {sufficiency['status']} ({sufficiency['substantive_word_count']} words).
- If FULL_SOURCE: Preserve the investigative depth, quotes, figures, and historical context. Do NOT compress into a brief summary.
- If PARTIAL_SOURCE: Write only to the depth supported by verified facts. Do NOT invent filler.
- If SNIPPET_ONLY: Write a concise, attributed news brief (150–300 words). Do NOT invent missing details.
- Accuracy always takes priority over word count.

SOURCE FIDELITY RULES (apply before writing):
- Write ONLY information traceable to the supplied source material.
- Do NOT upgrade the evidence. Preserve exact wording strength: "associated with" stays "associated with", not "caused".
- Do NOT manufacture significance, predictions, expert opinions, or programme goals not stated in the source.
- Do NOT change geographic scope, participant numbers, percentages, dates, or institutional names.
- Do NOT add background padding or filler to reach word count. Accuracy > word count.
- Every numerical and geographical claim must remain faithful to the source.
- Use precise attribution: "According to...", "Researchers reported...", "Organizers said..."
- Never fabricate quotations. Use attributed paraphrase if no direct quote is available.

STRICT FORMAT INSTRUCTIONS:
1. "category" MUST be exactly one of: {json.dumps(OFFICIAL_CATEGORIES)}.
2. "headline" MUST be concise (8–14 words, sentence case, NO hyphens or dashes).
3. "article" MUST be pure continuous prose formatted in clean semantic <p>...</p> HTML tags only.
4. NO subheadings (<h3>, <h4>), NO bullet points (<ul>, <li>), NO Key Takeaways, NO FAQs, NO executive summaries, NO inline disclaimers.
5. NO compound-word hyphens (gene editing not gene-editing). NO em-dashes or en-dashes.
6. Before returning JSON, run internal source check: every fact traceable? evidence preserved? no invented material? exact numbers intact?
7. Return ONLY valid JSON:

{{
  "headline": "Concise professional headline in sentence case",
  "seo_title": "SEO page title",
  "meta_description": "Meta description",
  "category": "{norm_cat}",
  "visual_keyword": "Single specific medical keyword",
  "article": "<p>First paragraph...</p>\\n\\n<p>Second paragraph...</p>\\n\\n<p>Third paragraph...</p>"
}}

If non-medical, return: {{"rejected": true}}"""


def sanitize_article_html(raw_html: str) -> str:
    """Enforces clean semantic <p>...</p> HTML and removes prohibited tags/styles."""
    if not raw_html:
        return ""

    sanitized = raw_html.strip()

    # Strip code fences
    sanitized = re.sub(r"^```html\s*", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"^```\s*", "", sanitized)
    sanitized = re.sub(r"\s*```$", "", sanitized)

    # Strip scripts, styles, iframes, tables
    sanitized = re.sub(r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"<iframe\b[^<]*(?:(?!<\/iframe>)<[^<]*)*<\/iframe>", "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"<table\b[^<]*(?:(?!<\/table>)<[^<]*)*<\/table>", "", sanitized, flags=re.IGNORECASE)

    # Strip presentation style/class attributes
    sanitized = re.sub(r'\sstyle="[^"]*"', "", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r'\sclass="[^"]*"', "", sanitized, flags=re.IGNORECASE)

    # Strip any inline disclaimers or review stamps
    sanitized = re.sub(r"<p>\s*(?:Published by|Review by|Medical Disclaimer|Disclaimer|Fact-Checked By)[\s\S]*?<\/p>", "", sanitized, flags=re.IGNORECASE)

    # Convert headings and list items to paragraphs
    sanitized = re.sub(r"<h[1-6][^>]*>([\s\S]*?)<\/h[1-6]>", r"<p>\1</p>", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"<li[^>]*>([\s\S]*?)<\/li>", r"<p>\1</p>", sanitized, flags=re.IGNORECASE)
    sanitized = re.sub(r"<\/?(?:ul|ol|div|span|section|article|header|footer|hr|em|strong|b|i)[^>]*>", "", sanitized, flags=re.IGNORECASE)

    # Split into clean paragraphs
    parts = re.split(r"<\/p>\s*<p>|\n\n+|<\/p>|<p>", sanitized, flags=re.IGNORECASE)
    paragraphs = []
    for part in parts:
        cleaned_text = re.sub(r"<[^>]+>", " ", part)
        cleaned_text = re.sub(r"\s+", " ", cleaned_text).strip()
        if len(cleaned_text) > 20:
            lower = cleaned_text.lower()
            if lower.startswith("published by") or lower.startswith("review by") or "medical disclaimer" in lower or "fact-checked by" in lower:
                continue
            # Post-process: em/en-dashes → comma; hyphens between words → space
            cleaned_text = re.sub(r"[\u2014\u2013]", ", ", cleaned_text)   # — and – → comma
            cleaned_text = re.sub(r"(\w)-(\w)", r"\1 \2", cleaned_text)    # gene-editing → gene editing
            cleaned_text = re.sub(r"\s{2,}", " ", cleaned_text).strip()
            paragraphs.append(f"<p>{cleaned_text}</p>")

    if not paragraphs:
        fallback = re.sub(r"<[^>]+>", " ", sanitized).strip()
        return f"<p>{fallback}</p>"

    return "\n\n".join(paragraphs)


def validate_article_schema(data: Any) -> Tuple[bool, List[str], Optional[Dict[str, Any]]]:
    """Validates the parsed AI JSON response."""
    errors = []

    if not isinstance(data, dict):
        return False, ["Response is not a valid JSON object"], None

    if data.get("rejected") is True:
        return False, ["Article rejected as non-health content"], None

    headline = str(data.get("headline") or data.get("title") or "").strip()
    if not headline or len(headline) < 10:
        errors.append("Headline is missing or too short")

    raw_article = str(data.get("article") or data.get("content") or "").strip()
    if not raw_article or len(raw_article) < 150:
        errors.append("Article body is missing or too short")

    # Validate Category against Official 12
    candidate_cat = str(data.get("category") or "").strip()
    category = "Health"
    for cat in OFFICIAL_CATEGORIES:
        if cat.lower() == candidate_cat.lower():
            category = cat
            break
    else:
        category = normalize_rss_category(candidate_cat)

    sanitized_article = sanitize_article_html(raw_article)

    if errors:
        return False, errors, None

    cleaned_headline = headline.replace("—", ", ").replace("–", ", ").replace("-", " ")
    cleaned_headline = re.sub(r"\s+", " ", cleaned_headline).strip()

    return True, [], {
        "headline": cleaned_headline,
        "seo_title": str(data.get("seo_title") or headline)[:70].strip(),
        "meta_description": str(data.get("meta_description") or "")[:160].strip(),
        "category": category,
        "visual_keyword": str(data.get("visual_keyword") or "medical").strip(),
        "article": sanitized_article,
    }


def build_full_article_user_message(
    original_headline: str,
    original_content: str,
    category: str = "Health",
    author: str = "Flobstar Editorial Board",
    source_url: str = "N/A"
) -> str:
    """User message for full article generation (JSON output)."""
    norm_cat = normalize_rss_category(category)

    return f"""SOURCE INFORMATION:
Source URL: {source_url}
Preliminary Category Hint: {norm_cat}
Author Byline: {author}

SOURCE CONTENT:
Headline: {original_headline}
Full Text: {original_content}

TASK:
Write ONE COMPLETE, ORIGINAL news article in pure continuous prose following all Flobstar News editorial standards.

SOURCE FIDELITY RULES (apply before writing):
- Write ONLY information traceable to the supplied source material.
- Do NOT upgrade the evidence. Preserve exact wording strength: "associated with" stays "associated with", not "caused".
- Do NOT manufacture significance, predictions, expert opinions, or programme goals not stated in the source.
- Do NOT change geographic scope, participant numbers, percentages, dates, or institutional names.
- Do NOT add background padding or filler to reach word count. Accuracy > word count.
- Every numerical and geographical claim must remain faithful to the source.
- Use precise attribution: "According to...", "Researchers reported...", "Organizers said..."
- Never fabricate quotations. Use attributed paraphrase if no direct quote is available.

STRICT FORMAT INSTRUCTIONS:
1. "category" MUST be exactly one of: {json.dumps(OFFICIAL_CATEGORIES)}.
2. "headline" MUST be concise (8–14 words, sentence case, NO hyphens or dashes).
3. "article" MUST be pure continuous prose formatted in clean semantic <p>...</p> HTML tags only.
4. NO subheadings (<h3>, <h4>), NO bullet points (<ul>, <li>), NO Key Takeaways, NO FAQs, NO executive summaries, NO inline disclaimers.
5. NO compound-word hyphens (gene editing not gene-editing). NO em-dashes or en-dashes.
6. Before returning JSON, run internal source check: every fact traceable? evidence preserved? no invented material? exact numbers intact?
7. Return ONLY valid JSON:

{{
  "headline": "Concise professional headline in sentence case",
  "seo_title": "SEO page title",
  "meta_description": "Meta description",
  "category": "{norm_cat}",
  "visual_keyword": "Single specific medical keyword",
  "article": "<p>First paragraph...</p>\\n\\n<p>Second paragraph...</p>\\n\\n<p>Third paragraph...</p>"
}}

If non-medical, return: {{"rejected": true}}"""


EVIDENCE_UPGRADE_PATTERNS = [
    (re.compile(r"represents?\s+a\s+(major|significant|landmark|historic|groundbreaking)", re.I), 'Manufactured significance: "represents a major/significant..."', 2),
    (re.compile(r"marks?\s+a\s+(major|significant|landmark|pivotal|turning|historic)", re.I), 'Manufactured significance: "marks a major/significant..."', 2),
    (re.compile(r"pav(es?|ing)\s+the\s+way\s+for", re.I), 'Cliche: "paving the way for"', 1),
    (re.compile(r"could\s+transform\s+", re.I), 'Unsourced significance: "could transform"', 2),
    (re.compile(r"will\s+transform\s+", re.I), 'Upgraded significance: "will transform"', 3),
    (re.compile(r"game[\s-]changer", re.I), 'Cliche: "game-changer"', 1),
    (re.compile(r"revolutionary\s+(new\s+)?", re.I), 'Unsourced significance: "revolutionary"', 2),
    (re.compile(r"underscores?\s+the\s+importance", re.I), 'AI filler: "underscores the importance"', 1),
    (re.compile(r"comes?\s+at\s+a\s+time\s+when", re.I), 'AI filler: "comes at a time when"', 1),
    (re.compile(r"unprecedented\s+", re.I), 'Unsupported superlative: "unprecedented"', 2),
    (re.compile(r"\bwill\s+(improve|reduce|prevent|eliminate|cure|solve|fix|increase|decrease|lower|boost)\b", re.I), 'Possible evidence upgrade: "will [improve/reduce/prevent...]" — check if source only says "could" or "may"', 2),
    (re.compile(r"\bis\s+expected\s+to\s+(dramatically|significantly|substantially|greatly)", re.I), 'Evidence upgrade: "is expected to dramatically/significantly..."', 2),
    (re.compile(r"\b(dramatically|drastically)\s+(reduce|improve|lower|cut|increase)\b", re.I), 'Unsourced quantification: "dramatically/drastically reduce/improve"', 2),
    (re.compile(r"\bproven\s+to\b", re.I), 'Possible evidence upgrade: "proven to" — verify source actually establishes proof', 2),
    (re.compile(r"\bdemonstrates?\s+that\b", re.I), 'Possible evidence upgrade: "demonstrates that" — verify source strength', 1),
    (re.compile(r"experts?\s+say\s+that\b", re.I), 'Unattributed expert: "experts say that" — who are they?', 2),
    (re.compile(r"specialists?\s+believe\b", re.I), 'Unattributed specialist: "specialists believe" — attribute specifically', 2),
    (re.compile(r"many\s+doctors?\s+(say|believe|think|agree)\b", re.I), 'Unattributed claim: "many doctors say/believe"', 2),
    (re.compile(r"only\s+time\s+will\s+tell\b", re.I), 'Generic ending cliche: "only time will tell"', 2),
    (re.compile(r"future\s+remains?\s+promising\b", re.I), 'Generic ending cliche: "future remains promising"', 2),
    (re.compile(r"will\s+continue\s+to\s+monitor\b", re.I), 'Generic ending cliche: "will continue to monitor"', 1),
    (re.compile(r"in\s+conclusion\b", re.I), 'Prohibited academic marker: "in conclusion"', 3),
    (re.compile(r"as\s+research\s+continues\b", re.I), 'Generic ending transition: "as research continues"', 1),
    (re.compile(r"\bwill\s+save\s+lives?\b", re.I), 'Unsourced outcome: "will save lives" — verify this is in the source', 3),
    (re.compile(r"\bwill\s+prevent\s+deaths?\b", re.I), 'Unsourced outcome: "will prevent deaths" — verify this is in the source', 3),
    (re.compile(r"\bexpected\s+to\s+save\b", re.I), 'Unsourced prediction: "expected to save"', 2),
]


def detect_evidence_upgrades(article_text: str) -> List[Dict[str, Any]]:
    """Scans generated article text for evidence upgrades, cliches, or unsourced significance."""
    if not article_text:
        return []

    plain_text = re.sub(r"<[^>]+>", " ", article_text)
    plain_text = re.sub(r"\s+", " ", plain_text).strip()
    warnings = []

    for pattern, message, severity in EVIDENCE_UPGRADE_PATTERNS:
        match = pattern.search(plain_text)
        if match:
            warnings.append({
                "message": message,
                "severity": severity,
                "matched_text": match.group(0),
            })

    return warnings


def build_headline_user_message(original_headline: str, original_content: str) -> str:
    """User message for headline generation."""
    return f"""Source Headline: {original_headline}
Source Content (excerpt): {original_content[:600]}

Task: Rewrite the headline following Flobstar News headline rules:
- 8–14 words, sentence case
- No hyphens, en-dashes, or em-dashes
- Direct, specific, journalistic — not clickbait
- Put the most important news first

Return ONLY the finished headline. Nothing else."""


def build_summary_user_message(original_content: str, max_words: int = 150) -> str:
    """User message for lead paragraph generation."""
    return f"""Source Content: {original_content}

Task: Write a lead paragraph for this story following Flobstar News editorial standards:
- Approximately {max_words} words
- Communicates the most important facts immediately
- Written in natural, flowing journalistic prose
- No bullet points, no subheadings, no filler

Return ONLY the finished lead paragraph. Nothing else."""


def build_fact_check_user_message(content: str) -> str:
    """User message for fact-checking a draft article."""
    return f"""Content to fact-check:
{content}

Task: Analyze this health news content as a Flobstar News fact-checker.

Return ONLY valid JSON in this exact structure:
{{
  "issues_found": false,
  "suspicious_claims": [],
  "requires_verification": [],
  "confidence_score": 0.9,
  "notes": "General observations about accuracy and sourcing"
}}

Focus on:
- Medical claims needing verification
- Statistics that need sources
- Sensational or exaggerated language
- Unattributed quotes
- Unverified institutional claims"""
