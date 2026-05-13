from enum import Enum

class WorkflowStage(str, Enum):
    INIT = "init"
    PREMISE_GENERATED = "premise_generated"
    FACTS_LOCKED = "facts_locked"
    STUDENT_OPENING = "student_opening"
    OPPOSING_RESPONSE = "opposing_response"
    STUDENT_REBUTTAL = "student_rebuttal"
    JUDGE_EVALUATION = "judge_evaluation"
    COMPLETED = "completed"

TOPICS = [
    "title dispute", "adverse possession", "partition suit",
    "coparcenary dispute", "forged sale deed", "mutation dispute",
    "boundary dispute", "encroachment", "inheritance dispute",
    "family settlement", "gift deed challenge", "tenant eviction",
    "builder possession delay", "RERA complaint", "specific performance",
    "injunction dispute", "landlord tenant conflict", "revenue record dispute",
    "fraudulent transfer", "easement rights"
]

GENERATION_MODES = [
    "clean law-school style hypotheticals",
    "messy real-world property disputes",
    "highly ambiguous ownership conflicts",
    "document-heavy evidentiary disputes",
    "family inheritance conflicts",
    "emotionally tense family property fights",
    "oral agreement disputes",
    "weak documentation cases",
    "contradictory timeline disputes",
    "tenant possession ambiguity disputes"
]
