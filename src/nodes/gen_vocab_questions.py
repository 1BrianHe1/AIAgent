import json
import uuid
from llm_client import llm
import random
from prompts import VOCAB_QUESTIONS_PROMPT, JSON_ONLY_SUFFIX
from models import AgentState, VocabPackage, Question, LessonPackage
import re
from utils.text_utils import clean_word
from config import SKILL_TO_EXERCISE_MAP, LISTENING_EXERCISE_TYPES
from tools.tts import generate_audio_placeholder

def parse_llm_json_output(llm_output: str, word: str) -> list[Question]:
    try:
        if llm_output.strip().startswith("```json"):
            cleaned_output = llm_output.strip()[7:-3].strip()
        else:
            cleaned_output = llm_output
        data = json.loads(cleaned_output)
        questions_data = data.get("questions", [])
        parsed_questions = []
        for item in questions_data:
            q = Question(
                qid=str(uuid.uuid4()),
                type=item.get("type", "UNKNOWN"),
                prompt=item.get("prompt", ""),
                options=item.get("options"),
                answer=item.get("answer"),
                explanation=item.get("explanation"),
                target_word=item.get("target_word", word)
            )
            parsed_questions.append(q)
        return parsed_questions
    except (json.JSONDecodeError, TypeError, IndexError) as e:
        print(f"  - ERROR: Failed to parse JSON for word '{word}'. Error: {e}")
        print(f"  - Raw LLM output was:\n{llm_output}")
        return []

def gen_vocab_questions(state: AgentState) -> AgentState:

    print("---NODE: gen_vocab_questions ---")

    current_lesson = state.current_lesson
    passage = state.current_passage

    if not current_lesson or not passage:
        state.errors.append("gen_vocab_questions: Missing lesson or passage in state.")
        return state

    all_vocab_packages = []
    vocab_list = current_lesson.related_vocabulary
    
    print(f"  - Generating question packages for {len(vocab_list)} vocabulary items...")

    for i, vocab_item in enumerate(vocab_list):
        original_word = vocab_item.word
        cleaned_word = clean_word(original_word)
        print(f"    - ({i+1}/{len(vocab_list)}) Processing word: '{original_word}' -> Cleaned: '{cleaned_word}'")
        
        exercise_requests = []
        for skill, count in vocab_item.skill_distribution.items():
            if count > 0:
                exercise_requests.append(f"- 生成 {count} 道 `{skill}` 技能的题目")
        
        if not exercise_requests:
            print(f"      - No exercises requested for this word. Skipping.")
            package = VocabPackage(word_id=str(vocab_item.word_id), word=original_word, questions=[])
            all_vocab_packages.append(package)
            continue
            
        exercise_requests_str = "\n".join(exercise_requests)

        prompt = VOCAB_QUESTIONS_PROMPT.format(
            word=cleaned_word,
            passage_text=passage.text,
            exercise_requests_list=exercise_requests_str
        ) + JSON_ONLY_SUFFIX
        
        questions = []
        for attempt in range(2):
            llm_output = llm(prompt)
            questions = parse_llm_json_output(llm_output, cleaned_word)
            if questions:
                break
            else:
                print(f"    - Attempt {attempt + 1} failed. Parsing returned no questions. Retrying...")
        
        for q in questions:
            if q.type in LISTENING_EXERCISE_TYPES:
                q.audio_url = generate_audio_placeholder(q.prompt)
        
        package = VocabPackage(
            word_id=str(vocab_item.word_id),
            word=original_word, 
            questions=questions
        )
        all_vocab_packages.append(package)

    lesson_package = LessonPackage(
        lesson_id=str(current_lesson.lesson_id),
        lesson_name=current_lesson.lesson_name,
        passage=passage.model_dump(),
        vocab_packages=[pkg.model_dump() for pkg in all_vocab_packages]
    )
    state.outputs.append(lesson_package.model_dump())
    print(f"  - Successfully created LessonPackage for lesson: '{current_lesson.lesson_name}'")
    return state