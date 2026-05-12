"""Prompt rendering for site adapters."""

from pathlib import Path

from src.sites.task_templates import get_template, load_prompt_template

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


def render_site_prompt(
    *,
    site: str,
    base_prompt_file: str,
    user_task: str,
    escalation_instructions: str,
    detection_instructions: str,
    template_id: str | None = None,
    site_context: str = "",
) -> str:
    """Render a full site prompt from base and task templates."""
    task_section = _render_task_section(site=site, user_task=user_task, template_id=template_id)
    base_template = load_prompt_template(site, base_prompt_file)
    return (
        base_template.replace("{task_section}", task_section)
        .replace("{detection_instructions}", detection_instructions)
        .replace("{escalation_instructions}", escalation_instructions)
        .replace(
            "{decision_checkpoint_instructions}", _load_shared_partial("decision_checkpoints.txt")
        )
        .replace("{site_context}", site_context)
    )


def _render_task_section(*, site: str, user_task: str, template_id: str | None) -> str:
    if not template_id:
        return user_task
    template = get_template(site, template_id)
    if not template:
        return user_task
    try:
        raw_template = load_prompt_template(site, template.prompt_file)
    except FileNotFoundError:
        return user_task
    return raw_template.replace("{user_task}", user_task)


def _load_shared_partial(prompt_file: str) -> str:
    path = PROMPTS_DIR / "shared" / prompt_file
    if not path.exists():
        raise FileNotFoundError(f"Shared prompt partial not found: {path}")
    return path.read_text(encoding="utf-8")
