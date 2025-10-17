from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class VocabItem(BaseModel):
    word_id: int
    word: str
    HSK_level: int
    skill_distribution: Dict[str, int]

class Lesson(BaseModel):
    lesson_id: int
    lesson_name: str
    description: str
    duration: int
    skill_distribution: Dict[str, int]
    
    related_vocabulary: List[VocabItem]

class Stage2Input(BaseModel):

    topic: str
    question_num: int   
    hsk_level: int 
    total_lessons: int
    estimated_duration: int
    lessons: List[Lesson]

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
    audio_url: Optional[str] = None

class VocabPackage(BaseModel):
    word_id: str
    word: str
    questions: List[Question]

class LessonPackage(BaseModel):
    lesson_id: str
    lesson_name: str
    passage: Passage
    vocab_packages: List[VocabPackage]


class AgentState(BaseModel):
    stage2_input: Stage2Input
    lesson_queue: List[Lesson] = Field(default_factory=list)
    current_lesson: Optional[Lesson] = None
    current_passage: Optional[Passage] = None
    outputs: List[Dict] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)