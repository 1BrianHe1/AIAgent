
import uuid
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field



class OptionItem(BaseModel):
    id: str                   
    text: str
    meaning: Optional[str] = None
    pinyin: Optional[str] = None

class Stimuli(BaseModel):
    text: Optional[str] = None
    audio_url: Optional[str] = None #

class Question(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    level: int                  
    type: str                  
    stimuli: Stimuli
    stem: str                   
    stem_en: Optional[str] = None #
    options: Optional[List[OptionItem]] = None
    answer: Optional[Any] = None

class VocabPackage(BaseModel):
    word_id: str
    word: str
    questions: List[Question]



class Role(BaseModel):
    roleId: int
    roleName: str

class VocabItem(BaseModel):
    word_id: int
    word: str
    HSK_level: int
    skill_distribution: Dict[str, int] 


class LessonInput(BaseModel):
    lesson_id: int
    lesson_name: str
    description: str
    duration: int
    skill_distribution: Dict[str, int]
    type: str 
    roles: Optional[List[Role]] = None
    related_vocabulary: List[VocabItem]

class Stage2Input(BaseModel):
    topic: str
    question_num: int   
    hsk_level: int 
    total_lessons: int
    estimated_duration: int
    lessons: List[LessonInput] 



class PassageOutput(BaseModel):
    text: str
    covered_words: List[str]
    textEn: Optional[str] = None
    pinyin: Optional[str] = None

class DialogueLine(BaseModel):
    dialogueId: int
    roleId: int
    text: str
    covered_words: List[str]
    textEn: Optional[str] = None
    pinyin: Optional[str] = None


class LessonOutput(BaseModel):
    lesson_id: str
    lesson_name: str
    type: str
    passage: Optional[PassageOutput] = None
    roles: Optional[List[Role]] = None
    dialogues: Optional[List[DialogueLine]] = None
    vocab_packages: List[VocabPackage] = Field(default_factory=list)


class AgentState(BaseModel):
    stage2_input: Stage2Input
    
    lesson_queue: List[LessonInput] = Field(default_factory=list)
    current_lesson: Optional[LessonInput] = None
    
    current_output_lesson: Optional[LessonOutput] = None
    current_content_text: str = "" 
    
    outputs: List[Dict] = Field(default_factory=list) 
    errors: List[str] = Field(default_factory=list)