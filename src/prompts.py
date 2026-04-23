SYSTEM_PROMPT = """You are a senior analyst and expert knowledge extractor. 
Your goal is to extract deep, actionable insights from English non-fiction texts and synthesize them into high-quality Russian.
Crucial instructions:
1. Avoid generic fluff (e.g., "The author discusses various ways..."). Be concrete.
2. Extract specific frameworks, metrics, unique concepts, and counter-intuitive ideas.
3. The Russian text must feel like a native, human-written reading note by an expert. Use strong, punchy formatting.
4. Keep the structure clear, scannable, and dense with value.
"""

MAP_PROMPT = """Analyze chunk {chunk_index} of {total_chunks} from the document.
Extract the most valuable and concrete insights.
Respond in JSON format:
{{
  "section_title": "Brief title for this part",
  "summary": "Concrete Russian summary of this chunk (focus on facts, not filler)",
  "key_ideas": ["Specific idea 1", "Specific idea 2"],
  "quotes": ["Direct quote 1 (in English or Russian)"]
}}

Text to analyze:
{text}
"""

REDUCE_PROMPT = """You have analyzed all chunks of the document '{filename}'.
Here are the summaries:
{summaries}

Synthesize this into a cohesive, comprehensive executive summary and structured insights.
Output in JSON format exactly as follows:
{{
  "document_title": "Translated or original title",
  "short_summary": "2-3 highly dense sentences overview in Russian",
  "full_markdown": "A beautifully formatted markdown document in Russian containing all insights. Do NOT escape newlines as \\\\n unnecessarily in the JSON string if it breaks standard JSON parsing. The markdown MUST follow this exact structure:\\n\\n# [Title]\\n\\n## 📌 О чем этот материал\\n[Concrete summary avoiding generic fluff]\\n\\n## 💡 Ключевые идеи\\n[Dense bullets]\\n\\n## 🛠 Практические инсайты\\n[Specific, actionable bullets]\\n\\n## ⚙️ Полезные методы и фреймворки\\n[Named frameworks or specific methods]\\n\\n## 🚀 Что можно применить на практике\\n[Numbered list of actions]\\n\\n## ⚠️ Важные ограничения и оговорки\\n[Bullets on when this does NOT apply]\\n\\n## 🎯 Для кого это особенно полезно\\n[Text]\\n\\n## 💬 Интересные цитаты / фрагменты\\n[Meaningful quotes]\\n\\n## 📚 Краткий конспект по разделам\\n[Bullet points organized by key sections]\\n\\n## 🏁 Итог\\n[Final punchy takeaway]",
  "insights": {{
    "key_ideas": ["...", "..."],
    "practical_takeaways": ["...", "..."],
    "frameworks": ["...", "..."],
    "action_items": ["...", "..."],
    "limitations": ["...", "..."],
    "target_audience": ["...", "..."],
    "quotes": ["...", "..."]
  }},
  "sections": [
    {{
      "title": "Section Title",
      "summary_ru": "Section summary"
    }}
  ]
}}

Ensure "full_markdown" uses markdown headings (##) exactly as requested. It must be highly readable and dense with actual knowledge. Add emojis to headings as shown above.
Constraints:
- target_length_preference: {max_length}
- extract_quotes: {extract_quotes}
"""
