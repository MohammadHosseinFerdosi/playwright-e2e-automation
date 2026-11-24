"""Static mirror of topup-mng's ``operator_info`` Mongo seed (mobile-operator prefixes).

Ported from ``topup-mng/deployment/operator-info/index.js`` — the mongosh script that seeds the
``topup_mng_db.operator_info`` collection. That script also carries UI-only fields (charge
packages, colors, image ids, Persian marketing copy) that no test or generator here reads; only
``operator`` / ``name`` / ``prefixes`` are ported, so this file is a *prefix table*, not a full
port of the seed document.

This is a static, offline counterpart to
``tests.services.super_app.internet.internet_random_cell_number.random_cell_number_for_operator``,
which fetches the same kind of prefix list live via ``GET /top-ups/operators``. Prefer the live
version when an authenticated ``ApiClient`` is already in scope — it can never drift from the
environment under test. Use this static table when a valid-looking number is needed with no API
call (e.g. unit tests, or building request payloads before a session exists).

Caution: nothing keeps this in sync with the real ``operator_info`` collection automatically. If
topup-mng adds/removes a prefix, this table goes stale until someone updates it by hand from the
source file above.
"""

from __future__ import annotations

import random

from pydantic import BaseModel, ConfigDict, Field

from tests.api.top_ups.admin.operator_settings import OperatorId
from tests.services.fake_ids import fake_cell_number

_secure_rand = random.SystemRandom()


class OperatorPrefixInfo(BaseModel):
    """One prefix entry for an operator, as stored in the Mongo seed (``value`` + SIM ``types``)."""

    model_config = ConfigDict(frozen=True)

    value: str
    types: tuple[str, ...] = Field(default_factory=tuple)


class OperatorInfo(BaseModel):
    """One ``operator_info`` document, trimmed to the fields a phone-number generator needs."""

    model_config = ConfigDict(frozen=True)

    operator: OperatorId
    name: str
    description: str
    prefixes: tuple[OperatorPrefixInfo, ...]

    def prefix_values(self, *, number_type: str | None = None) -> list[str]:
        """All prefix strings, optionally filtered to those offered for ``number_type``.

        ``number_type`` matches the seed's own labels: ``"PRE_PAID"``, ``"POST_PAID"``, ``"DATA"``.
        """
        if number_type is None:
            return [p.value for p in self.prefixes]
        return [p.value for p in self.prefixes if number_type in p.types]


# Ported from topup-mng/deployment/operator-info/index.js (see module docstring for scope).
# ``OperatorId.SHATEL`` (used by the dashboard admin API) has no entry here — the source seed
# file only carries MCI/MTN/RIGHTEL. ``operator_info(OperatorId.SHATEL)`` raises accordingly.
OPERATORS: tuple[OperatorInfo, ...] = (
    OperatorInfo(
        operator=OperatorId.MCI,
        name="MCI",
        description="همراه اول",
        prefixes=(
            OperatorPrefixInfo(value="0910", types=("POST_PAID", "PRE_PAID")),
            OperatorPrefixInfo(value="0919", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0990", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0991", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0992", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0993", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0994", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0911", types=("POST_PAID", "PRE_PAID")),
            OperatorPrefixInfo(value="0912", types=("POST_PAID",)),
            OperatorPrefixInfo(value="0913", types=("POST_PAID", "PRE_PAID")),
            OperatorPrefixInfo(value="0914", types=("POST_PAID", "PRE_PAID")),
            OperatorPrefixInfo(value="0915", types=("POST_PAID", "PRE_PAID")),
            OperatorPrefixInfo(value="0916", types=("POST_PAID", "PRE_PAID")),
            OperatorPrefixInfo(value="0917", types=("POST_PAID", "PRE_PAID")),
            OperatorPrefixInfo(value="0918", types=("POST_PAID", "PRE_PAID")),
            OperatorPrefixInfo(value="09910", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="09911", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="09912", types=("POST_PAID",)),
            OperatorPrefixInfo(value="09913", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="09919", types=("PRE_PAID",)),
        ),
    ),
    OperatorInfo(
        operator=OperatorId.MTN,
        name="MTN",
        description="ایرانسل",
        prefixes=(
            OperatorPrefixInfo(value="0901", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0902", types=("POST_PAID", "PRE_PAID")),
            OperatorPrefixInfo(value="0903", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0904", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0905", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0930", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0933", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0935", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0936", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0937", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0938", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="0939", types=("PRE_PAID",)),
            OperatorPrefixInfo(value="09027", types=("POST_PAID",)),
            OperatorPrefixInfo(value="09029", types=("POST_PAID",)),
            OperatorPrefixInfo(value="09350", types=("POST_PAID",)),
            OperatorPrefixInfo(value="09359", types=("POST_PAID",)),
            OperatorPrefixInfo(value="0941", types=("DATA",)),
        ),
    ),
    OperatorInfo(
        operator=OperatorId.RIGHTEL,
        name="RIGHTEL",
        description="رایتل",
        prefixes=(
            OperatorPrefixInfo(value="0920", types=("POST_PAID", "PRE_PAID")),
            OperatorPrefixInfo(value="0921", types=("PRE_PAID", "DATA")),
            OperatorPrefixInfo(value="0922", types=("PRE_PAID",)),
        ),
    ),
)

_BY_OPERATOR: dict[int, OperatorInfo] = {int(item.operator): item for item in OPERATORS}


def operator_info(operator: OperatorId | int) -> OperatorInfo:
    """Return the static seed entry for ``operator``. Raises ``LookupError`` if unknown."""
    try:
        return _BY_OPERATOR[int(operator)]
    except KeyError as exc:
        raise LookupError(f"No static operator_info entry for operator={operator!r}") from exc


def prefixes_for_operator(
    operator: OperatorId | int, *, number_type: str | None = None
) -> list[str]:
    """Prefix strings for ``operator``, optionally filtered by ``number_type``.

    See ``OperatorInfo.prefix_values`` for the ``number_type`` label set.
    """
    return operator_info(operator).prefix_values(number_type=number_type)


def fake_cell_number_for_operator(
    operator: OperatorId | int, *, number_type: str | None = None
) -> str:
    """Generate a fake cell number under one of ``operator``'s known static prefixes.

    Offline counterpart to
    ``tests.services.super_app.internet.internet_random_cell_number.random_cell_number_for_operator``
    — no ``ApiClient`` / live call required, at the cost of drifting from the real
    ``operator_info`` collection over time (see module docstring). Raises ``LookupError`` if
    ``operator`` is unknown or has no prefixes for ``number_type``.
    """
    prefixes = prefixes_for_operator(operator, number_type=number_type)
    if not prefixes:
        raise LookupError(
            f"No static prefixes for operator={operator!r}, number_type={number_type!r}"
        )
    return fake_cell_number(predefined_prefix=_secure_rand.choice(prefixes))
