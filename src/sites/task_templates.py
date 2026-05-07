"""Pre-built task templates for common customer service requests.

Each template maps to a prompt file and provides a structured way for users
to initiate tasks without writing freeform descriptions.
"""

from dataclasses import dataclass, field
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent.parent / "prompts"


@dataclass
class TaskTemplate:
    """A pre-built task template that users can select."""

    id: str
    name: str
    description: str
    site: str
    prompt_file: str  # Relative to prompts/<site>/
    required_inputs: list[str] = field(default_factory=list)
    example_usage: str = ""


# --- American Express Templates ---

AMEX_TEMPLATES: list[TaskTemplate] = [
    TaskTemplate(
        id="negotiate_fee",
        name="Negotiate Annual Fee",
        description="Negotiate a waiver or reduction of your card's annual fee",
        site="amex",
        prompt_file="negotiate_fee.txt",
        example_usage="flyingpig 'negotiate my annual fee' --site amex --template negotiate_fee",
    ),
    TaskTemplate(
        id="dispute_charge",
        name="Dispute a Charge",
        description="File a dispute for an unauthorized or incorrect charge",
        site="amex",
        prompt_file="dispute_charge.txt",
        required_inputs=["charge_amount", "merchant_name", "charge_date", "dispute_reason"],
        example_usage=(
            "flyingpig 'dispute $50 charge from Amazon on March 15' "
            "--site amex --template dispute_charge"
        ),
    ),
    TaskTemplate(
        id="retention_offer",
        name="Get Retention Offer",
        description="Request retention offers by expressing intent to cancel",
        site="amex",
        prompt_file="retention_offer.txt",
        example_usage=(
            "flyingpig 'get retention offer for my Platinum card' "
            "--site amex --template retention_offer"
        ),
    ),
    TaskTemplate(
        id="general",
        name="General Request",
        description="Any other customer service request (freeform)",
        site="amex",
        prompt_file="general.txt",
        example_usage="flyingpig 'ask about upgrading my card' --site amex",
    ),
]

GENERIC_TEMPLATES: list[TaskTemplate] = [
    TaskTemplate(
        id="negotiate_fee",
        name="Negotiate a Fee",
        description="Reduce or waive a fee on any account",
        site="generic",
        prompt_file="negotiate_fee.txt",
    ),
    TaskTemplate(
        id="dispute_charge",
        name="Dispute a Charge",
        description="File a dispute on any service/card charge",
        site="generic",
        prompt_file="dispute_charge.txt",
    ),
    TaskTemplate(
        id="retention_offer",
        name="Get Retention Offer",
        description="Request retention offers before cancelling",
        site="generic",
        prompt_file="retention_offer.txt",
    ),
    TaskTemplate(
        id="general",
        name="General Request",
        description="Any other customer-service task (freeform)",
        site="generic",
        prompt_file="general.txt",
    ),
]

# Registry of all templates by site
_TEMPLATES: dict[str, list[TaskTemplate]] = {
    "amex": AMEX_TEMPLATES,
    "generic": GENERIC_TEMPLATES,
}


def get_templates(site: str) -> list[TaskTemplate]:
    """Get all available templates for a site."""
    return _TEMPLATES.get(site.lower(), [])


def get_template(site: str, template_id: str) -> TaskTemplate | None:
    """Get a specific template by site and ID."""
    for t in get_templates(site):
        if t.id == template_id:
            return t
    return None


def load_prompt_template(site: str, prompt_file: str) -> str:
    """Load a prompt template file from the prompts directory."""
    path = PROMPTS_DIR / site.lower() / prompt_file
    if not path.exists():
        raise FileNotFoundError(f"Prompt template not found: {path}")
    return path.read_text(encoding="utf-8")


def list_all_templates() -> dict[str, list[TaskTemplate]]:
    """Return all templates grouped by site."""
    return dict(_TEMPLATES)
