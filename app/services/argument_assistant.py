import json
import httpx
from app.config import settings


SYSTEM_PROMPT = """You are helping a French learner structure a 2-3 minute spoken monologue for the TCF exam (Tâche 3 — monologue argumenté).

Given the topic and the student's rough arguments (which may be in French, English, or a mix), produce a well-organized French paragraph (100-150 words) at {level} CEFR level that:

- Uses natural French connectors appropriate for the level:
  - B1: d'abord, ensuite, enfin, aussi, mais, parce que, par exemple, je pense que
  - B2: d'une part / d'autre part, en revanche, par conséquent, cependant, certes... mais, il me semble que, en effet
  - C1: en l'occurrence, à plus forte raison, quand bien même, force est de constater que, il n'en demeure pas moins que
- Follows a clear argumentation structure (context → thesis → arguments → concession → conclusion)
- Sounds like natural spoken French, not literary or overly formal
- Is realistic for a language learner at {level} to speak aloud
- Incorporates the student's ideas and arguments, organizing them logically
- Does NOT include pronunciation guides or parenthetical notes

Return ONLY the paragraph, no preamble, no explanation, no markdown."""


async def generate_structure(
    topic: str,
    student_arguments: str,
    target_level: str = "B2",
) -> dict:
    """Generate a structured argument paragraph from student's rough ideas."""

    if not settings.ANTHROPIC_API_KEY:
        return {
            "structure": f"[DEMO] Configure ANTHROPIC_API_KEY for real argument structuring. Your arguments: {student_arguments}",
        }

    system = SYSTEM_PROMPT.replace("{level}", target_level)

    user_msg = (
        f"Topic: {topic}\n"
        f"Target level: {target_level}\n\n"
        f"Student's rough arguments/ideas:\n\"\"\"\n{student_arguments}\n\"\"\""
    )

    try:
        from app.services.ai_router import pick_model
        from app.services.anthropic_client import call_anthropic

        # F-311 Phase C: outline_scaffold → sonnet (Q2b confirmed
        # 2026-05-12 — reasoning-heavy outline generation needs the
        # better model). cache_system=True so the SYSTEM_PROMPT template
        # caches across calls (static across all users; perfect cache fit).
        # max_tokens=1024 unchanged (already a reasonable cap for outline output).
        result = await call_anthropic(
            system=system,
            messages=[{"role": "user", "content": user_msg}],
            model=pick_model("outline_scaffold"),
            max_tokens=1024,
            cache_system=True,
            timeout=60.0,
        )
        structure = (result if isinstance(result, str) else "").strip()
        return {"structure": structure}

    except Exception as e:
        return {"structure": "", "error": str(e)}
