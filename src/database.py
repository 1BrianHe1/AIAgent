# src/database.py
import os
import uuid # (新增) 导入 uuid 模块
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, ForeignKey, Boolean, Index,
    UniqueConstraint, DateTime,CheckConstraint
)
# (新增) 导入 UUID 类型
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import sessionmaker, relationship, declarative_base
from sqlalchemy.sql import func
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL not set in .env file")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

SCHEMA_NAME = "Scenario_learning"

class TopicDB(Base):
    __tablename__ = "topics"
    topic_id = Column(Integer, primary_key=True) # SERIAL 由 DB 处理, index=True 默认给主键
    topic_name = Column(String(255), nullable=False) # 移除 index=True
    input_hsk_level = Column(Integer, nullable=False) # (修改) 匹配 SQL NOT NULL
    input_total_lessons = Column(Integer) # nullable=True 是默认值
    input_estimated_duration = Column(Integer)
    input_question_num = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    lessons = relationship("GeneratedLessonDB", back_populates="topic")
    __table_args__ = (
        Index('ix_topics_topic_name', 'topic_name'), # 显式定义索引
        {'schema': SCHEMA_NAME}
    )

class VocabularyDB(Base):
    __tablename__ = "vocabulary"
    vocab_uuid = Column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    word = Column(String(255), nullable=False) # 移除 index=True
    hsk_level = Column(Integer, nullable=False) # 移除 index=True
    # (移除) pinyin = Column(String, nullable=True)
    # (移除) english_translation = Column(Text, nullable=True)
    vocab_packages = relationship("GeneratedVocabPackageDB", back_populates="vocabulary_item")
    __table_args__ = (
        UniqueConstraint('word', 'hsk_level', name='uq_vocabulary_word_level'),
        Index('ix_vocabulary_word', 'word'), # 显式定义索引
        Index('ix_vocabulary_hsk_level', 'hsk_level'), # 显式定义索引
        {'schema': SCHEMA_NAME}
    )

class GeneratedLessonDB(Base):
    __tablename__ = "generated_lessons"
    lesson_db_id = Column(Integer, primary_key=True)
    topic_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.topics.topic_id"), nullable=False) # 移除 index=True
    lesson_id_str = Column(String(50), unique=True, nullable=False) # 移除 index=True
    lesson_name = Column(String(255), nullable=False)
    type = Column(String(50), nullable=False) # 移除 index=True
    passage = Column(JSONB)
    roles = Column(JSONB)
    dialogues = Column(JSONB)
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    topic = relationship("TopicDB", back_populates="lessons")
    vocab_packages = relationship("GeneratedVocabPackageDB", back_populates="lesson", cascade="all, delete-orphan")
    __table_args__ = (
        Index('ix_generated_lessons_topic_id', 'topic_id'), # 显式定义索引
        Index('ix_generated_lessons_lesson_id_str', 'lesson_id_str'), # 显式定义索引
        Index('ix_generated_lessons_type', 'type'), # 显式定义索引
        CheckConstraint(type.in_(['passage', 'dialogue'])), # 添加 CHECK 约束
        {'schema': SCHEMA_NAME}
    )

class GeneratedVocabPackageDB(Base):
    __tablename__ = "generated_vocab_packages"
    vocab_package_db_id = Column(Integer, primary_key=True)
    lesson_db_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.generated_lessons.lesson_db_id"), nullable=False) # 移除 index=True
    vocab_uuid = Column(UUID(as_uuid=True), ForeignKey(f"{SCHEMA_NAME}.vocabulary.vocab_uuid"), nullable=False) # 移除 index=True
    # (移除) word_id 列
    lesson = relationship("GeneratedLessonDB", back_populates="vocab_packages")
    vocabulary_item = relationship("VocabularyDB", back_populates="vocab_packages")
    questions = relationship("GeneratedQuestionDB", back_populates="vocab_package", cascade="all, delete-orphan")
    __table_args__ = (
        Index('ix_generated_vocab_packages_lesson_db_id', 'lesson_db_id'), # 显式定义索引
        Index('ix_generated_vocab_packages_vocab_uuid', 'vocab_uuid'), # 显式定义索引
        Index('ix_generated_vocab_packages_lesson_vocab', 'lesson_db_id', 'vocab_uuid'), # 显式定义索引
        {'schema': SCHEMA_NAME}
    )

class GeneratedQuestionDB(Base):
    __tablename__ = "generated_questions"
    question_db_id = Column(Integer, primary_key=True)
    vocab_package_db_id = Column(Integer, ForeignKey(f"{SCHEMA_NAME}.generated_vocab_packages.vocab_package_db_id"), nullable=False) # 移除 index=True
    # (修改) 移除 server_default
    question_uuid = Column(UUID(as_uuid=True), unique=True, nullable=False) # 移除 index=True
    level = Column(Integer, nullable=False) # 移除 index=True
    type = Column(String(50), nullable=False) # 移除 index=True
    stimuli = Column(JSONB)
    stem = Column(Text)
    stem_en = Column(Text)
    options = Column(JSONB)
    answer = Column(JSONB)
    vocab_package = relationship("GeneratedVocabPackageDB", back_populates="questions")
    __table_args__ = (
        Index('ix_generated_questions_vocab_package_db_id', 'vocab_package_db_id'), # 显式定义索引
        Index('ix_generated_questions_question_uuid', 'question_uuid'), # 显式定义索引
        Index('ix_generated_questions_level', 'level'), # 显式定义索引
        Index('ix_generated_questions_type', 'type'), # 显式定义索引
        Index('ix_generated_questions_level_type', 'level', 'type'), # 显式定义索引
        {'schema': SCHEMA_NAME}
    )

# (核心修改) 更新保存逻辑以匹配新的模型/键名
def save_lesson_output(topic_name: str, lesson_data: dict, topic_hsk_level: int | None = None):
    db = SessionLocal()
    lesson_id_to_save = lesson_data.get("lesson_id") # 这是字符串 '1', '2' 等
    lesson_name_to_save = lesson_data.get('lesson_name', 'Unknown')

    try:
        # 1. 获取或创建 Topic (使用 TopicDB 和 topic_id)
        topic_db = db.query(TopicDB).filter(TopicDB.topic_name == topic_name).first()
        if not topic_db:
            print(f"  - Topic '{topic_name}' not found. Creating new topic entry...")
            topic_db = TopicDB(topic_name=topic_name, input_hsk_level=topic_hsk_level)
            db.add(topic_db)
            db.flush()
            print(f"  - Created Topic '{topic_name}' with DB ID {topic_db.topic_id}.")
        # else: 更新逻辑可选

        # 2. 检查 Lesson (使用 GeneratedLessonDB 和 lesson_id_str)
        existing_lesson = db.query(GeneratedLessonDB).filter(GeneratedLessonDB.lesson_id_str == lesson_id_to_save).first()
        if existing_lesson:
            print(f"  - Lesson '{lesson_name_to_save}' (ID: {lesson_id_to_save}) already exists in DB. Skipping save.")
            db.close()
            return

        # 3. 创建 LessonDB (使用 GeneratedLessonDB 和 topic_id)
        lesson_db = GeneratedLessonDB(
            topic_id=topic_db.topic_id, # 使用 topic_id
            lesson_id_str=lesson_id_to_save,
            lesson_name=lesson_name_to_save,
            type=lesson_data.get("type"),
            passage=lesson_data.get("passage"),
            roles=lesson_data.get("roles"),
            dialogues=lesson_data.get("dialogues")
        )
        db.add(lesson_db)
        db.flush() # 获取 lesson_db_id

        # 4. 处理 VocabPackages 和 Vocabulary
        vocab_packages_data = lesson_data.get("vocab_packages", [])
        for vp_data in vocab_packages_data:
            word_str = vp_data.get("word")
            # --- HSK Level 获取逻辑 (不变) ---
            word_hsk_level = topic_hsk_level if topic_hsk_level else 0 # 简化默认值
            if vp_data.get("questions"):
                 q_levels = [q.get("level") for q in vp_data["questions"] if q.get("level") is not None]
                 if q_levels: word_hsk_level = q_levels[0]

            if not word_str: continue

            # 获取或创建 VocabularyDB (使用 word 和 hsk_level 查找)
            vocabulary_item = db.query(VocabularyDB).filter(
                VocabularyDB.word == word_str,
                VocabularyDB.hsk_level == word_hsk_level
            ).first()

            if not vocabulary_item:
                print(f"    - Creating new vocabulary entry for '{word_str}' (HSK {word_hsk_level})...")
                vocabulary_item = VocabularyDB(word=word_str, hsk_level=word_hsk_level)
                db.add(vocabulary_item)
                db.flush() # 获取 vocab_uuid

            # 创建 VocabPackageDB (使用 GeneratedVocabPackageDB, lesson_db_id, vocab_uuid)
            vocab_package_db = GeneratedVocabPackageDB(
                lesson_db_id=lesson_db.lesson_db_id,
                vocab_uuid=vocabulary_item.vocab_uuid # 使用 UUID 外键
                # word_id 字段已移除
            )
            db.add(vocab_package_db)
            db.flush() # 获取 vocab_package_db_id

            # 处理 Questions (使用 GeneratedQuestionDB, vocab_package_db_id, question_uuid)
            questions_data = vp_data.get("questions", [])
            for q_data in questions_data:
                 q_uuid_to_save_str = q_data.get("id") # 这是 UUID 字符串
                 if not q_uuid_to_save_str: continue # 跳过没有 ID 的问题数据

                 try:
                     q_uuid_to_save = uuid.UUID(q_uuid_to_save_str) # 转换为 UUID 对象
                 except ValueError:
                      print(f"    - WARN: Invalid UUID format for question id: {q_uuid_to_save_str}. Skipping question.")
                      continue

                 # 检查问题重复 (使用 GeneratedQuestionDB 和 question_uuid)
                 existing_question = db.query(GeneratedQuestionDB).filter(GeneratedQuestionDB.question_uuid == q_uuid_to_save).first()
                 if existing_question:
                     print(f"    - Question (UUID: {q_uuid_to_save_str}) already exists. Skipping.")
                     continue

                 # 创建 QuestionDB (使用 GeneratedQuestionDB, vocab_package_db_id, question_uuid)
                 question_db = GeneratedQuestionDB(
                    vocab_package_db_id=vocab_package_db.vocab_package_db_id,
                    question_uuid=q_uuid_to_save, # 存储 UUID 对象
                    level=q_data.get("level"),
                    type=q_data.get("type"),
                    stimuli=q_data.get("stimuli"),
                    stem=q_data.get("stem"),
                    stem_en=q_data.get("stem_en"),
                    options=q_data.get("options"),
                    answer=q_data.get("answer")
                 )
                 db.add(question_db)

        db.commit() # 提交整个事务
        print(f"  - Successfully saved Lesson '{lesson_db.lesson_name}' (ID: {lesson_db.lesson_id_str}) under Topic '{topic_name}' to DB.")

    except Exception as e:
        db.rollback() # 回滚事务
        print(f"  - ERROR saving Lesson '{lesson_name_to_save}' to DB: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close() # 关闭会话
