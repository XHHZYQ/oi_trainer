"""业务枚举：数据库中一律以 VARCHAR(n) 存储（不建 PG 原生 enum），枚举值见需求文档 §12.2。"""
from enum import Enum


class AccountRole(str, Enum):
    student = "student"
    teacher = "teacher"
    admin = "admin"


class AccountStatus(str, Enum):
    active = "active"
    disabled = "disabled"


class CourseStatus(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class ClassGroupStatus(str, Enum):
    planned = "planned"
    ongoing = "ongoing"
    finished = "finished"
    cancelled = "cancelled"


class EnrollmentStatus(str, Enum):
    active = "active"
    quit = "quit"
    finished = "finished"


class OrderStatus(str, Enum):
    pending = "pending"
    paid = "paid"
    cancelled = "cancelled"
    refunded = "refunded"


class ProblemStatus(str, Enum):
    draft = "draft"
    published = "published"
    archived = "archived"


class SubmissionLanguage(str, Enum):
    cpp = "cpp"
    python = "python"
    java = "java"


class SubmissionStatus(str, Enum):
    pending = "pending"
    judging = "judging"
    accepted = "accepted"
    wrong_answer = "wrong_answer"
    time_limit_exceeded = "time_limit_exceeded"
    memory_limit_exceeded = "memory_limit_exceeded"
    runtime_error = "runtime_error"
    compile_error = "compile_error"
    system_error = "system_error"


class MessageRole(str, Enum):
    system = "system"
    user = "user"
    assistant = "assistant"
    tool = "tool"


class ReviewErrorType(str, Enum):
    logic = "logic"
    boundary = "boundary"
    complexity = "complexity"
    style = "style"
    none = "none"


class AiReviewStatus(str, Enum):
    pending = "pending"
    done = "done"
    failed = "failed"


class ConversationKind(str, Enum):
    qa = "qa"
    hint = "hint"
    walkthrough = "walkthrough"


class StudyPlanStatus(str, Enum):
    active = "active"
    completed = "completed"
    expired = "expired"


class ContestType(str, Enum):
    oi = "oi"
    acm = "acm"
    mock = "mock"


class ContestStatus(str, Enum):
    not_started = "not_started"
    running = "running"
    finished = "finished"
    frozen = "frozen"


class TeacherReviewType(str, Enum):
    code_review = "code_review"
    hint = "hint"
    encourage = "encourage"


class HomeworkStatus(str, Enum):
    draft = "draft"
    published = "published"
    closed = "closed"


class HomeworkSubmitStatus(str, Enum):
    submitted = "submitted"
    graded = "graded"
