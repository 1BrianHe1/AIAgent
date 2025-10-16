# src/models.py (最终修复版)

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

# --- 1. 输入数据模型 (Input Data Models) ---

class VocabItem(BaseModel):
    # 类型为 int，匹配 JSON
    word_id: int
    word: str
    HSK_level: int
    skill_distribution: Dict[str, int]

class Lesson(BaseModel):
    # 类型为 int，匹配 JSON
    lesson_id: int
    lesson_name: str
    description: str
    
    # 修改点：同时保留 duration 和 skill_distribution
    duration: int
    skill_distribution: Dict[str, int]
    
    related_vocabulary: List[VocabItem]

class Stage2Input(BaseModel):
    # 修改点：新增 topic 和 question_num 字段
    topic: str
    question_num: int
    
    # 修改点：hsk_level 类型为 int
    hsk_level: int
    
    total_lessons: int
    estimated_duration: int
    lessons: List[Lesson]


# --- 2. 输出/生成内容模型 (保持不变) ---
# 输出模型我们可以保持ID为字符串，增加灵活性

class Passage(BaseModel):
    lesson_id: str
    text: str
    tokens_est: int
    covered_words: List[str]

class Question(BaseModel):
    qid: str
    type: str
    prompt: str
    options: Optional[List[str]] = None
    answer: Any
    explanation: Optional[str] = None
    target_word: str

class VocabPackage(BaseModel):
    word_id: str
    word: str
    questions: List[Question]

class LessonPackage(BaseModel):
    lesson_id: str
    lesson_name: str
    passage: Passage
    vocab_packages: List[VocabPackage]


# --- 3. LangGraph 状态模型 (保持不变) ---

class AgentState(BaseModel):
    stage2_input: Stage2Input
    lesson_queue: List[Lesson] = Field(default_factory=list)
    current_lesson: Optional[Lesson] = None
    current_passage: Optional[Passage] = None
    outputs: List[Dict] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)