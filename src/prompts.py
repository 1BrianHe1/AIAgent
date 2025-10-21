

JSON_ONLY_SUFFIX = """
重要：除了JSON代码块本身，不要输出任何其他文字、解释或注释。你的回答必须是一个可以直接通过 `json.loads()` 解析的合法JSON对象。
"""


PASSAGE_PROMPT = """
你是一位专业的中文教学内容设计师。
你的任务是为 HSK{hsk_level} 水平的学生，根据下面的要求创作一篇短文。

---
学习单元：{lesson_name}
单元说明：{lesson_desc}
必须自然地包含以下所有核心词汇：{vocab_list}
字数要求：{chars_min}-{chars_max}字
---

输出要求：你必须严格按照以下 JSON 格式返回：
{{
  "text": "（生成的中文文章全文）",
  "textEn": "（对应的英文翻译全文）",
  "pinyin": "（整篇文章的拼音）",
  "covered_words": ["（文章中实际包含的核心词汇列表）", ...]
}}
""" + JSON_ONLY_SUFFIX


DIALOGUE_PROMPT = """
你是一位专业的中文教学内容设计师和剧本作家。
你的任务是为 HSK{hsk_level} 水平的学生创作一段对话。

---
学习单元：{lesson_name}
单元说明：{lesson_desc}
对话角色：{roles_str}
必须自然地包含以下所有核心词V汇：{vocab_list}
---

输出要求：你必须严格按照以下 JSON 列表格式返回，其中每个对象代表一行对话：
[
  {{
    "dialogueId": 1,
    "roleId": 1,
    "text": "（角色1的第一句话）",
    "textEn": "（对应的英文翻译）",
    "pinyin": "（对应的拼音）",
    "covered_words": ["（这句中包含的核心词汇）"]
  }},
  {{
    "dialogueId": 2,
    "roleId": 2,
    "text": "（角色2的回应）",
    "textEn": "...",
    "pinyin": "...",
    "covered_words": []
  }}
]
""" + JSON_ONLY_SUFFIX


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


VOCAB_QUESTIONS_PROMPT = """
你是一位顶级的中文教学内容设计师，你必须严格遵循 JSON 格式要求。

核心教学目标：帮助学生掌握中文词汇 `{word}`。
可参考的上下文（文章或对话）：
---
{passage_text}
---

**你的任务**：
请严格按照下面的“出题要求清单”，为核心词 `{word}` 生成一个包含所有题目的 JSON 对象。

**出题要求清单**:
{exercise_requests_list}

**JSON 格式定义 (V6 结构)**:
你的输出必须是一个 JSON 对象，包含一个 "questions" 列表。
**所有题目**，无论何种类型，都必须遵循以下**统一格式**：

```json
{{
  "type": "（题型ID, 例如: read_choice, listen_tf）",
  "stimuli": {{
    "text": "（做题所需的上下文。听力题则为听力稿。无则为 null）"
  }},
  "stem": "（具体的中文题目问题）",
  "stem_en": "（具体的英文翻译问题）",
  "options": [
    {{
      "id": "A",
      "text": "（选项A的文本）",
      "meaning": "（选项A的英文含义，可选）",
      "pinyin": "（选项A的拼音，可选）"
    }},
    {{
      "id": "B",
      "text": "（选项B的文本）"
    }}
  ],
  "answer": "（答案。选择题为选项id 'A', 判断题为 true/false）"
}}
"""

QUALITY_CHECK_PROMPT = """
你是一位严格的中文教学内容质检专家。
你的任务是评估一个JSON格式的练习题是否符合质量标准。

---
标准1 (相关性): 题目（`stimuli.text`或`stem`）是否紧密围绕核心词汇 `{target_word}` 进行考察？
标准2 (正确性): 题目的 `answer` 字段对于 `stem` 字段来说是否正确无误？
标准3 (难度): 题目的语言难度是否适合 HSK {hsk_level} 级别的学生？
标准4 (唯一性/选择题专项): 如果这是一个选择题（`options` 字段非空），是否只有一个选项（`options.text`）是明确的最佳答案，而其他选项是明确错误的？
标准5 (翻译质量): `stem_en` 字段是否是 `stem` 字段的准确英文翻译？
---

待评估的题目 JSON :
{question_json}
---

请根据上述所有标准，对这个题目进行评估，并严格按照以下 JSON 格式返回你的结论：

{{
  "is_valid": true,
  "reason": "（如果 is_valid 为 false，请在此处用中文简要说明不合格的原因，例如：'标准4不合格：选项B和C均可视为正确答案'）"
}}
"""

