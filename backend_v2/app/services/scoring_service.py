from app.models.db_models import Session

class ScoringService:
    def compute_final_score(self, session: Session, judge_result: dict) -> int:
        base_advocacy = judge_result.get("advocacy_score", 0)
        base_procedural = judge_result.get("procedural_discipline", 0)
        hall_penalty = judge_result.get("hallucination_penalty", 0)

        # Additional penalties from flags detected during submission
        flag_penalty = 0
        if hasattr(session, "hallucination_flags"):
            flag_penalty = sum(f.score_penalty for f in session.hallucination_flags)

        # Weighted calculation
        raw = int(0.5 * base_advocacy + 0.3 * base_procedural + 0.2 * (100 - hall_penalty))
        final = max(0, min(100, raw - flag_penalty))
        return final
