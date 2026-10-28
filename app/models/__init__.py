"""汇总导入全部模型，保证 SQLModel.metadata 完整（Alembic env.py 依赖）。"""
from app.models.ai_chat import AiConversation, AiMessage
from app.models.audit import AuditLog
from app.models.contest import Contest, ContestParticipant, ContestProblem
from app.models.homework import Homework, HomeworkProblem, HomeworkSubmission, TeacherReview
from app.models.org import (
    Account,
    ClassGroup,
    Course,
    Enrollment,
    EnrollmentOrder,
    StudentProfile,
    TeacherProfile,
)
from app.models.problem import (
    KnowledgePoint,
    Problem,
    ProblemKnowledgePoint,
    ProblemTag,
    Tag,
    TestCase,
)
from app.models.profile import KnowledgeMastery, StudyPlan
from app.models.submission import AiCodeReview, Submission, SubmissionCaseResult

__all__ = [
    # ① 组织教务域
    "Account",
    "StudentProfile",
    "TeacherProfile",
    "Course",
    "ClassGroup",
    "Enrollment",
    "EnrollmentOrder",
    # ② 题库知识域
    "KnowledgePoint",
    "Problem",
    "ProblemKnowledgePoint",
    "Tag",
    "ProblemTag",
    "TestCase",
    # ③ 提交判题域
    "Submission",
    "SubmissionCaseResult",
    "AiCodeReview",
    # ④ AI 答疑域
    "AiConversation",
    "AiMessage",
    # ⑤ 学习画像与推荐域
    "KnowledgeMastery",
    "StudyPlan",
    # ⑥ 竞赛域
    "Contest",
    "ContestProblem",
    "ContestParticipant",
    # ⑦ 审计域
    "AuditLog",
    # ⑧ 作业与人工点评域
    "Homework",
    "HomeworkProblem",
    "HomeworkSubmission",
    "TeacherReview",
]
