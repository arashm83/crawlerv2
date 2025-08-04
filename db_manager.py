from sqlalchemy import String, ForeignKey,Integer, Column
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy  import select
import hashlib


Base = declarative_base()
engine = create_async_engine('sqlite+aiosqlite:///quora.db')
AsyncSessionLocal = sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


class Question(Base):
    __tablename__ = 'questions'

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, nullable=False)
    question_url = Column(String)
    answers = relationship("Answer", back_populates="question")
    hash = Column(String(64), unique=True)


class Answer(Base):
    __tablename__ = 'answers'

    id = Column(Integer, primary_key=True)
    text = Column(String)
    author_name = Column(String)
    author_url = Column(String)
    question_id = Column(Integer, ForeignKey('questions.id'))
    hash = Column(String(64), unique=True)
    question = relationship("Question", back_populates="answers")


class DbManager:
    def __init__(self):
        self.session: AsyncSession = AsyncSessionLocal()
        self.question_hashes = set()
        self.answer_hashes = set()

    async def init_hashes(self):
        try:
            result = await self.session.execute(select(Question.hash))
            self.question_hashes = set([row[0] for row in result.all()])
        except Exception as e:
            print(f"Error retrieving hashes: {e}")
            self.question_hashes = set()

        try:
            result = await self.session.execute(select(Answer.hash))
            self.answer_hashes = set([row[0] for row in result.all()])
        except Exception as e:
            print(f"Error retrieving hashes: {e}")
            self.answer_hashes = set()

    async def add_question_with_answers(self, question_data, answers_data):

        try:
            question = Question(**question_data)
            question.hash = hashlib.sha256(question.question_url.encode()).hexdigest()
            self.session.add(question)
            await self.session.flush()

            for a_data in answers_data:
                answer = Answer(**a_data, question_id=question.id)
                answer.hash = hashlib.sha256(answer.text.encode()).hexdigest()
                self.session.add(answer)

            await self.session.commit()
            self.question_hashes.add(question.hash)

        except Exception as e:
            await self.session.rollback()

            for a_data in answers_data:
                answer = Answer(**a_data, question_id=question.id)
                self.session.add(answer)
                self.answer_hashes.add(answer.hash)

            await self.session.commit()
            self.question_hashes.add(question.hash)

        except Exception as e:
            await self.session.rollback()
            print(f"❌ Error saving question/answers: {e}")


        async def get_questions(self):
            result = await self.session.execute(select(Question))
            return result.scalars().all()

    async def get_answers(self, question_id: int):
        result = await self.session.execute(
            select(Answer).where(Answer.question_id == question_id)
        )
        return result.scalars().all()

    async def close(self):
        await self.session.close()


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)