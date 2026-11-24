"""Load ``secrets/uat_promissory_note.yaml`` (gitignored)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml
from pydantic import AliasChoices, BaseModel, ConfigDict, Field

from tests.config.settings import REPO_ROOT

DEFAULT_SECRETS_PATH = REPO_ROOT / "secrets" / "uat_promissory_note.yaml"


class PromissoryOwnerSecrets(BaseModel):
    """Owner identity for init / Mongo seed."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    user_id: str = Field(alias="userId")
    cell_number: str = Field(alias="cellNumber")
    national_code: str = Field(alias="nationalCode")
    birth_date: str = Field(alias="birthDate")
    postal_code: str = Field(alias="postalCode")
    city: str
    address: str


class PromissoryNoteSecrets(BaseModel):
    """UAT secrets for promissory-note smoke flows."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    requester_app_name: str
    tejarat_route_requester_app_name: str

    mongo_db_name: str = "promissory_note_db"
    notes_collection: str = "promissory_notes"
    payments_collection: str = "promissory_note_payments"
    refunds_collection: str = "promissory_note_refunds"

    owner: PromissoryOwnerSecrets
    iban: str
    amount: str
    tejarat_amount: str = Field(
        validation_alias=AliasChoices("tejaratAmount", "sanaAmount"),
        serialization_alias="tejaratAmount",
    )
    due_type: str = Field(alias="dueType")
    due_offset_in_years: str = Field(alias="dueOffsetInYears")
    recipient_id: str = Field(alias="recipientId")
    description: str

    seed_template_national_code: str
    seed_owner: PromissoryOwnerSecrets
    seed_iban: str

    def require_ready(self) -> PromissoryNoteSecrets:
        """Skip when placeholder values are still present."""
        for field_name, value in self.model_dump().items():
            if isinstance(value, dict):
                for nested_name, nested_value in value.items():
                    if isinstance(nested_value, str) and (
                        "CHANGE_ME" in nested_value
                        or nested_value.startswith("CHANGE")
                    ):
                        pytest.skip(
                            f"Fill secrets/uat_promissory_note.yaml "
                            f"(field {field_name}.{nested_name!r} still looks "
                            f"like a placeholder)"
                        )
                continue
            if not isinstance(value, str):
                continue
            if "CHANGE_ME" in value or value.startswith("CHANGE"):
                pytest.skip(
                    f"Fill secrets/uat_promissory_note.yaml "
                    f"(field {field_name!r} still looks like a placeholder)"
                )
        return self


def load_promissory_note_secrets(
    path: Path | None = None,
) -> PromissoryNoteSecrets | None:
    """Load secrets YAML if present."""
    target = path or DEFAULT_SECRETS_PATH
    if not target.is_file():
        return None
    raw: Any = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return None
    return PromissoryNoteSecrets.model_validate(raw)


def require_promissory_note_secrets() -> PromissoryNoteSecrets:
    """Load secrets or skip the test."""
    secrets = CHANGE_ME
    if secrets is None:
        pytest.skip(
            "Missing secrets/uat_promissory_note.yaml — copy "
            "secrets/uat_promissory_note.example.yaml and fill UAT values"
        )
    return secrets.require_ready()
