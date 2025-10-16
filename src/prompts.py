PASSAGE_PROMPT = """
你是一位专业的中文教学内容设计师。
你的任务是为一名 HSK{hsk_level} 水平的学生，根据下面的要求创作一篇短文。

---
学习单元：{lesson_name}
单元说明：{lesson_desc}
必须自然地包含以下所有核心词汇：{vocab_list}
字数要求：{chars_min}-{chars_max}字
风格要求：使用日常、口语化的语言，句子结构简单清晰，内容积极向上。
---

输出要求：请只输出文章正文，不要包含任何标题、解释或其他额外内容。
"""


FIX_APPEND_PROMPT = """
你是一位中文写作润色专家。
下面的文章遗漏了一些必须包含的词汇。

原始文章：
---
{text}
---

你的任务是在不改变原文核心内容和风格的前提下，对文章进行扩写或修改，从而自然地融入以下**缺失的词汇**：`{missing_vocab_list}`。

请只输出**完整修改后的新文章全文**，不要解释你的修改过程。
"""


# --- 2. 词汇练习题生成相关 (Vocabulary Question Generation) ---


JSON_ONLY_SUFFIX = """
重要：除了JSON代码块本身，不要输出任何其他文字、解释或注释。你的回答必须是一个可以直接通过 `json.loads()` 解析的合法JSON对象。
"""

VOCAB_QUESTIONS_PROMPT = """
你是一位精通中文教学的AI助手，擅长根据学生的水平和上下文设计练习题。
你的任务是为一个中文词汇 `{word}` 生成一个包含2-3种不同题型的练习题包。

文章上下文参考：
---
{passage_text}
---

你必须严格按照以下 JSON 格式进行输出，其中 `questions` 列表包含2-3个题目对象:
```json
{{
  "questions": [
    {{
      "type": "CLOZE",
      "prompt": "从文章中选择一个包含目标词的句子，并将目标词替换为____。",
      "options": ["目标词", "干扰项A", "干扰项B", "干扰项C"],
      "answer": "目标词",
      "explanation": "对答案的简短中文解释。",
      "target_word": "{word}"
    }},
    {{
      "type": "DEF_MC",
      "prompt": "下面哪个选项是 '{word}' 的正确意思？",
      "options": ["正确的释义", "错误的释义1", "错误的释义2", "错误的释义3"],
      "answer": "正确的释义",
      "explanation": "为什么这个释义是正确的。",
      "target_word": "{word}"
    }},
    {{
      "type": "TRANSLATE",
      "prompt": "请将下面的句子翻译成英文：[包含目标词的中文例句]",
      "options": null,
      "answer": "[对应的英文翻译]",
      "explanation": "翻译的关键点说明。",
      "target_word": "{word}"
    }}
  ]
}}
"""