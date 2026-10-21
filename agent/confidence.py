from typing import List, Dict, Any, Tuple, Optional

def calculate_confidence(hypothesis: Dict[str, Any], evidence_list: List[Dict[str, Any]]) -> float:
    """
    Computes a deterministic confidence score for a hypothesis based on evidence.
    Formula:
      confidence = supports / (supports + contradicts + 1)
      If contradicts > 0: penalty of 0.7x
      Max cap: 0.95
    """
    valid_keys = {hypothesis.get("id"), hypothesis.get("alias"), hypothesis.get("title")} - {None}

    supports_count = 0
    contradicts_count = 0

    for e in evidence_list:
        # Check if evidence applies to this hypothesis
        target_hypo = e.get("hypothesis_id") or e.get("hypothesis")
        if target_hypo in valid_keys:
            if e.get("classification") == "supports":
                supports_count += 1
            elif e.get("classification") == "contradicts":
                contradicts_count += 1

    # Base formula
    total_items = supports_count + contradicts_count + 1.0
    score = supports_count / total_items

    # Penalty for contradictory evidence
    if contradicts_count > 0:
        score = score * 0.7

    # Cap maximum confidence at 0.95
    score = min(score, 0.95)
    return round(score, 2)

def evaluate_all_hypotheses(hypotheses: List[Dict[str, Any]], evidence: List[Dict[str, Any]]) -> Tuple[float, Optional[Dict[str, Any]]]:
    """
    Evaluates all active hypotheses and returns the top scoring hypothesis and its score.
    """
    best_score = 0.0
    top_hypothesis = None

    for hypo in hypotheses:
        score = calculate_confidence(hypo, evidence)
        hypo["confidence_score"] = score

        if score > best_score:
            best_score = score
            top_hypothesis = hypo

    return best_score, top_hypothesis
