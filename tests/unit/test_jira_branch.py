"""Unit tests for scripts/jira_branch.py."""

from __future__ import annotations

from scripts.jira_branch import issue_key_from_branch_name


def test_ticketed_feat_branch() -> None:
    assert issue_key_from_branch_name("feat/ALPHA-15117-qa-redesign-login") == "ALPHA-15117"


def test_ticketed_kyc_branch() -> None:
    assert issue_key_from_branch_name("fix/KYC-2050-native-signature") == "KYC-2050"


def test_team_branch_has_no_issue() -> None:
    assert issue_key_from_branch_name("chore/superapp-port-wallet") == ""


def test_empty_and_default_branches() -> None:
    assert issue_key_from_branch_name("") == ""
    assert issue_key_from_branch_name("staging") == ""
