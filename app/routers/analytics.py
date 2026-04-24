"""
Analytics Router — What the user actually wants to see.
Endpoints:
  GET /api/analytics/dashboard     — everything at a glance
  GET /api/analytics/progress      — couche scores over time
  GET /api/analytics/recurring     — fossilized patterns & reflexes
  GET /api/analytics/coverage      — topic/theme coverage map
  GET /api/analytics/pass          — pass probability estimate
"""

import json
from collections import Counter
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.models.models import User, Recording, Feedback, TestTopic
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


# ═══════════════════════════════════════════════════════════════
# PASS PROBABILITY THRESHOLDS
# ═══════════════════════════════════════════════════════════════

PASS_THRESHOLDS = {
    "B1": {"floor": 8, "target": 11, "excellent": 14},
    "B2": {"floor": 10, "target": 13, "excellent": 16},
    "C1": {"floor": 12, "target": 15, "excellent": 18},
}


# ═══════════════════════════════════════════════════════════════
# DASHBOARD — Everything at a glance
# ═══════════════════════════════════════════════════════════════

@router.get("/dashboard")
def analytics_dashboard(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    One call, full picture:
    - total sessions, average score, current streak
    - latest couche scores
    - pass probability
    - top 3 recurring problems
    - topic coverage summary
    """
    recs = (
        db.query(Recording)
        .filter(Recording.user_id == user.id, Recording.status == "done")
        .order_by(Recording.created_at.asc())
        .all()
    )

    if not recs:
        return {
            "total_sessions": 0,
            "message": "Aucune session enregistrée. Faites votre première production orale !",
        }

    latest_rec = recs[-1]
    latest_fb = latest_rec.feedback

    # ── Basic stats ────────────────────────────────────────────
    scores = [r.feedback.note_globale for r in recs if r.feedback]
    avg_score = sum(scores) / len(scores) if scores else 0
    target_level = latest_rec.target_level or "B2"

    # ── Pass probability ───────────────────────────────────────
    pass_info = _calculate_pass_probability(scores, target_level)

    # ── Recurring problems (across all sessions) ───────────────
    recurring = _get_recurring_problems(recs)

    # ── Topic coverage ─────────────────────────────────────────
    coverage = _get_topic_coverage(recs, db)

    # ── Latest diagnostic summary ──────────────────────────────
    latest_carte = None
    latest_goulet = None
    if latest_fb:
        latest_carte = {
            "le_fond": latest_fb.score_le_fond,
            "les_moules_des_idees": latest_fb.score_les_moules_des_idees,
            "les_moules": latest_fb.score_les_moules,
            "les_reflexes_anglais": latest_fb.score_les_reflexes_anglais,
        }
        latest_goulet = {
            "couche": latest_fb.goulet_couche,
            "nom": latest_fb.goulet_nom,
            "explication": latest_fb.goulet_explication,
        }

    # ── Words per minute (fluency) ─────────────────────────────
    fluency = _get_fluency_stats(recs)

    # ── Latest ordonnance & corrections (for Progress tab) ─────
    latest_ordonnance = None
    latest_corrections = None
    if latest_fb:
        try:
            latest_ordonnance = json.loads(latest_fb.ordonnance) if latest_fb.ordonnance else {}
        except Exception:
            latest_ordonnance = {}
        try:
            latest_corrections = json.loads(latest_fb.corrections) if latest_fb.corrections else []
        except Exception:
            latest_corrections = []

    # ── Average duration ───────────────────────────────────────
    durations = [r.duration_seconds for r in recs if r.duration_seconds and r.duration_seconds > 0]
    avg_duration = round(sum(durations) / len(durations)) if durations else 0

    return {
        "total_sessions": len(recs),
        "target_level": target_level,
        "average_score": round(avg_score, 1),
        "latest_score": scores[-1] if scores else 0,
        "latest_carte": latest_carte,
        "latest_goulet": latest_goulet,
        "pass_probability": pass_info,
        "recurring_problems": recurring,
        "topic_coverage": coverage,
        "fluency": fluency,
        "latest_ordonnance": latest_ordonnance,
        "latest_corrections": latest_corrections,
        "average_duration": avg_duration,
    }


# ═══════════════════════════════════════════════════════════════
# PROGRESS — Couche scores over time
# ═══════════════════════════════════════════════════════════════

@router.get("/progress")
def progress_over_time(
    last_n: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Returns score history for charting.
    Each entry: date, note_globale, 4 couche scores, word_count, goulet.
    """
    recs = (
        db.query(Recording)
        .filter(Recording.user_id == user.id, Recording.status == "done")
        .order_by(Recording.created_at.desc())
        .limit(last_n)
        .all()
    )
    recs.reverse()  # chronological

    points = []
    for r in recs:
        if not r.feedback:
            continue
        fb = r.feedback
        points.append({
            "date": r.created_at.isoformat() if r.created_at else "",
            "topic": r.topic.title if r.topic else None,
            "target_level": r.target_level,
            "note_globale": fb.note_globale,
            "le_fond": fb.score_le_fond,
            "les_moules_des_idees": fb.score_les_moules_des_idees,
            "les_moules": fb.score_les_moules,
            "les_reflexes_anglais": fb.score_les_reflexes_anglais,
            "goulet_nom": fb.goulet_nom,
            "word_count": r.word_count,
        })

    # ── Trend calculation ──────────────────────────────────────
    trend = None
    if len(points) >= 3:
        recent_3 = [p["note_globale"] for p in points[-3:]]
        older_3 = [p["note_globale"] for p in points[:3]]
        recent_avg = sum(recent_3) / len(recent_3)
        older_avg = sum(older_3) / len(older_3)
        diff = recent_avg - older_avg
        if diff > 1.5:
            trend = {"direction": "up", "delta": round(diff, 1), "message": "Progression nette"}
        elif diff < -1.5:
            trend = {"direction": "down", "delta": round(diff, 1), "message": "Régression — revoir les bases"}
        else:
            trend = {"direction": "stable", "delta": round(diff, 1), "message": "Stable — travaillez le goulet pour débloquer"}

    # ── Per-couche trends ──────────────────────────────────────
    couche_trends = {}
    if len(points) >= 3:
        for couche in ["le_fond", "les_moules_des_idees", "les_moules", "les_reflexes_anglais"]:
            recent = [p[couche] for p in points[-3:]]
            older = [p[couche] for p in points[:3]]
            r_avg = sum(recent) / len(recent)
            o_avg = sum(older) / len(older)
            d = r_avg - o_avg
            couche_trends[couche] = {
                "current_avg": round(r_avg, 1),
                "delta": round(d, 1),
                "direction": "up" if d > 0.5 else ("down" if d < -0.5 else "stable"),
            }

    return {
        "total_sessions": len(points),
        "points": points,
        "trend": trend,
        "couche_trends": couche_trends,
    }


# ═══════════════════════════════════════════════════════════════
# RECURRING — Fossilized patterns & reflexes
# ═══════════════════════════════════════════════════════════════

@router.get("/recurring")
def recurring_problems(
    last_n: int = Query(default=10, ge=3, le=50),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Aggregates patterns_manquants and reflexes_detectes across sessions.
    Surfaces the top fossilized problems + the improving ones.
    """
    recs = (
        db.query(Recording)
        .filter(Recording.user_id == user.id, Recording.status == "done")
        .order_by(Recording.created_at.desc())
        .limit(last_n)
        .all()
    )

    result = _get_recurring_problems(recs, detailed=True)
    return result


# ═══════════════════════════════════════════════════════════════
# COVERAGE — Topic & theme map
# ═══════════════════════════════════════════════════════════════

@router.get("/coverage")
def topic_coverage(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    Shows which themes/topics the user has practiced vs. available.
    """
    recs = (
        db.query(Recording)
        .filter(Recording.user_id == user.id, Recording.status == "done")
        .all()
    )
    return _get_topic_coverage(recs, db, detailed=True)


# ═══════════════════════════════════════════════════════════════
# PASS — Pass probability estimate
# ═══════════════════════════════════════════════════════════════

@router.get("/pass")
def pass_probability(
    target_level: str = Query(default="B2"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    "Am I going to pass?" — the only question that matters.
    """
    recs = (
        db.query(Recording)
        .filter(Recording.user_id == user.id, Recording.status == "done")
        .order_by(Recording.created_at.asc())
        .all()
    )
    scores = [r.feedback.note_globale for r in recs if r.feedback]
    result = _calculate_pass_probability(scores, target_level)

    # Add score history for the chart
    result["score_history"] = [
        {
            "date": r.created_at.isoformat() if r.created_at else "",
            "score": r.feedback.note_globale,
        }
        for r in recs if r.feedback
    ]

    return result


# ═══════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ═══════════════════════════════════════════════════════════════

def _calculate_pass_probability(scores: list, target_level: str) -> dict:
    """
    Estimates pass probability based on recent performance.
    Uses weighted average (recent scores count more).
    """
    if not scores:
        return {
            "status": "insufficient_data",
            "message": "Pas assez de données. Enregistrez au moins 3 productions.",
            "probability": None,
            "target_score": PASS_THRESHOLDS.get(target_level, PASS_THRESHOLDS["B2"])["target"],
        }

    thresholds = PASS_THRESHOLDS.get(target_level, PASS_THRESHOLDS["B2"])

    # Weighted average: last 3 sessions count 2x
    if len(scores) >= 3:
        base = scores[:-3] if len(scores) > 3 else []
        recent = scores[-3:]
        weighted = base + recent * 2
        avg = sum(weighted) / len(weighted)
    else:
        avg = sum(scores) / len(scores)

    # Calculate probability bracket
    target = thresholds["target"]
    floor = thresholds["floor"]
    excellent = thresholds["excellent"]

    gap = target - avg

    if avg >= excellent:
        status = "excellent"
        probability = 95
        message = f"Vous performez au-dessus du seuil {target_level}. Continuez comme ça."
    elif avg >= target:
        status = "on_track"
        probability = 75
        message = f"Vous êtes dans la zone cible ({target}/20). Continuez à consolider."
    elif avg >= floor:
        status = "at_risk"
        probability = 40
        gap_str = f"+{round(gap, 1)}"
        message = f"Vous êtes sous la cible. Il vous faut {gap_str} points. Concentrez-vous sur votre goulet."
    else:
        status = "below_target"
        probability = 15
        gap_str = f"+{round(gap, 1)}"
        message = f"Vous êtes en dessous du plancher. Il vous faut {gap_str} points. Intensifiez les sessions."

    # Trend modifier
    if len(scores) >= 5:
        first_half = scores[:len(scores)//2]
        second_half = scores[len(scores)//2:]
        trend = (sum(second_half)/len(second_half)) - (sum(first_half)/len(first_half))
        if trend > 1:
            probability = min(probability + 10, 99)
            message += " Tendance positive."
        elif trend < -1:
            probability = max(probability - 10, 5)
            message += " Attention: tendance à la baisse."

    return {
        "status": status,
        "probability": probability,
        "average_score": round(avg, 1),
        "target_score": target,
        "gap": round(gap, 1) if gap > 0 else 0,
        "sessions_analyzed": len(scores),
        "message": message,
    }


def _get_recurring_problems(recs: list, detailed: bool = False) -> dict:
    """
    Aggregate patterns_manquants and reflexes_detectes across recordings.
    Returns top fossilized problems.
    """
    missing_counter = Counter()
    reflex_counter = Counter()
    goulet_counter = Counter()
    total = 0

    for r in recs:
        if not r.feedback:
            continue
        total += 1
        # Count missing patterns
        try:
            missing = json.loads(r.feedback.patterns_manquants) if r.feedback.patterns_manquants else []
            for p in missing:
                missing_counter[p] += 1
        except (json.JSONDecodeError, TypeError):
            pass
        # Count detected reflexes
        try:
            reflexes = json.loads(r.feedback.reflexes_detectes) if r.feedback.reflexes_detectes else []
            for ref in reflexes:
                reflex_counter[ref] += 1
        except (json.JSONDecodeError, TypeError):
            pass
        # Count goulet
        if r.feedback.goulet_nom:
            goulet_counter[r.feedback.goulet_nom] += 1

    if total == 0:
        return {"total_sessions": 0, "fossilized_patterns": [], "fossilized_reflexes": [], "dominant_goulet": None}

    # "Fossilized" = appears in >50% of sessions
    threshold = total * 0.5

    fossilized_patterns = [
        {"pattern": p, "count": c, "frequency": round(c / total * 100)}
        for p, c in missing_counter.most_common(10)
        if c >= 2  # at least 2 occurrences
    ]

    fossilized_reflexes = [
        {"reflex": r, "count": c, "frequency": round(c / total * 100)}
        for r, c in reflex_counter.most_common(10)
        if c >= 2
    ]

    # Dominant goulet = which couche is most often the bottleneck
    dominant_goulet = None
    if goulet_counter:
        top_goulet, top_count = goulet_counter.most_common(1)[0]
        dominant_goulet = {
            "nom": top_goulet,
            "count": top_count,
            "frequency": round(top_count / total * 100),
            "message": f"Votre goulet dominant est '{top_goulet}' — c'est votre frein principal dans {top_count}/{total} sessions.",
        }

    result = {
        "total_sessions": total,
        "fossilized_patterns": fossilized_patterns[:5],  # top 5
        "fossilized_reflexes": fossilized_reflexes[:5],
        "dominant_goulet": dominant_goulet,
    }

    if detailed:
        result["all_missing_patterns"] = fossilized_patterns
        result["all_detected_reflexes"] = fossilized_reflexes
        result["goulet_distribution"] = [
            {"nom": g, "count": c, "frequency": round(c / total * 100)}
            for g, c in goulet_counter.most_common()
        ]

    return result


def _get_topic_coverage(recs: list, db: Session, detailed: bool = False) -> dict:
    """
    Map of practiced vs. available topics per theme.
    """
    # All available topics grouped by theme
    all_topics = db.query(TestTopic).filter(TestTopic.is_active == True).all()
    themes = {}
    for t in all_topics:
        theme = t.theme or "Sans thème"
        if theme not in themes:
            themes[theme] = {"total": 0, "practiced": set(), "topics": []}
        themes[theme]["total"] += 1
        if detailed:
            themes[theme]["topics"].append({"id": t.id, "title": t.title})

    # Mark practiced topics
    practiced_ids = set()
    for r in recs:
        if r.topic_id:
            practiced_ids.add(r.topic_id)

    for t in all_topics:
        theme = t.theme or "Sans thème"
        if t.id in practiced_ids:
            themes[theme]["practiced"].add(t.id)

    total_available = len(all_topics)
    total_practiced = len(practiced_ids)

    coverage = {
        "total_available": total_available,
        "total_practiced": total_practiced,
        "overall_percentage": round(total_practiced / total_available * 100) if total_available else 0,
        "by_theme": {},
    }

    for theme, data in themes.items():
        practiced_count = len(data["practiced"])
        theme_info = {
            "total": data["total"],
            "practiced": practiced_count,
            "percentage": round(practiced_count / data["total"] * 100) if data["total"] else 0,
        }
        if detailed:
            theme_info["topics"] = [
                {**t, "practiced": t["id"] in practiced_ids}
                for t in data["topics"]
            ]
        coverage["by_theme"][theme] = theme_info

    # Find weakest theme (least coverage)
    unpracticed_themes = [
        theme for theme, info in coverage["by_theme"].items()
        if info["percentage"] < 30
    ]
    if unpracticed_themes:
        coverage["suggestion"] = f"Vous n'avez presque pas touché : {', '.join(unpracticed_themes[:3])}. Variez les thèmes."

    return coverage


def _get_fluency_stats(recs: list) -> dict:
    """
    Word count and words-per-minute trends.
    """
    data_points = []
    for r in recs:
        if r.word_count and r.word_count > 0:
            wpm = None
            if r.duration_seconds and r.duration_seconds > 0:
                wpm = round(r.word_count / (r.duration_seconds / 60), 1)
            data_points.append({
                "word_count": r.word_count,
                "wpm": wpm,
            })

    if not data_points:
        return {"average_word_count": 0, "average_wpm": None}

    avg_wc = sum(d["word_count"] for d in data_points) / len(data_points)
    wpm_values = [d["wpm"] for d in data_points if d["wpm"] is not None]
    avg_wpm = sum(wpm_values) / len(wpm_values) if wpm_values else None

    result = {
        "average_word_count": round(avg_wc),
        "average_wpm": round(avg_wpm, 1) if avg_wpm else None,
        "total_data_points": len(data_points),
    }

    # Fluency assessment
    if avg_wpm:
        if avg_wpm < 60:
            result["assessment"] = "Débit lent — beaucoup d'hésitations probables. Travaillez la fluidité."
        elif avg_wpm < 100:
            result["assessment"] = "Débit correct pour un apprenant. Continuez à automatiser les structures."
        elif avg_wpm < 140:
            result["assessment"] = "Bon débit. Concentrez-vous sur la qualité plutôt que la vitesse."
        else:
            result["assessment"] = "Débit rapide — vérifiez que la précision suit."

    return result
