"""Named analytics options stored in input and result models."""

from enum import Enum


class ResponseStatus(str, Enum):
    ANSWERED = "answered"
    TIMEOUT = "timeout"


class AnalysisMode(str, Enum):
    CHOICE_ONLY = "choice_only"
    CHOICE_AND_TIME = "choice_and_time"


class TimeAlgorithm(str, Enum):
    SOURCE_V1 = "source_v1"
    SYMMETRIC_CANDIDATE_V2 = "symmetric_candidate_v2"


class IterationStrategy(str, Enum):
    LITERAL_SOURCE_V1 = "literal_source_v1"
    SELF_RETENTION_PROTOTYPE_V1 = "self_retention_prototype_v1"
