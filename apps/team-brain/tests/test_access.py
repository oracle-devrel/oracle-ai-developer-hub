"""Access layer — identity resolution, group grants, and MCP tokens.

Proves the ENFORCE-side inputs are correct: a token resolves to the right
principal, groups expand to the right domains, leadership is all-domains, and
an unknown token resolves to nothing (fail closed). Unchanged in intent by the
Oracle port — AccessControl's public API (resolve_token/get_principal/
list_principals) is the same shape as the workshop version.
"""

from __future__ import annotations

import pytest

from team_brain.access import AccessControl, Principal, hash_token, load_access_spec, seed_access

pytestmark = pytest.mark.requires_oracle


def test_hash_token_is_stable_and_one_way() -> None:
    assert hash_token("tb_ops_jeff_7f3a9c21") == hash_token("  tb_ops_jeff_7f3a9c21  ")
    assert hash_token("a") != hash_token("b")
    assert "tb_ops_jeff" not in hash_token("tb_ops_jeff_7f3a9c21")  # not recoverable


def test_seed_and_resolve_token(tokens: dict[str, str]) -> None:
    ac = AccessControl()
    try:
        jeff = ac.resolve_token(tokens["jeff"])
        assert isinstance(jeff, Principal)
        assert jeff.username == "jeff"
        assert jeff.domains == frozenset({"ops"})
        assert jeff.all_domains is False
    finally:
        ac.close()


def test_cross_domain_grant(tokens: dict[str, str]) -> None:
    ac = AccessControl()
    try:
        julia = ac.resolve_token(tokens["julia"])
        assert julia is not None
        # marketing + ops (cross-domain grant), but NOT sales
        assert julia.domains == frozenset({"marketing", "ops"})
        assert "sales" not in julia.domains
    finally:
        ac.close()


def test_leadership_is_all_domains(tokens: dict[str, str]) -> None:
    ac = AccessControl()
    try:
        brian = ac.resolve_token(tokens["brian"])
        assert brian is not None
        assert brian.all_domains is True
    finally:
        ac.close()


def test_unknown_token_resolves_to_none(tokens: dict[str, str]) -> None:
    ac = AccessControl()
    try:
        assert ac.resolve_token("tb_not_a_real_token") is None
        assert ac.resolve_token("") is None
        assert ac.resolve_token("   ") is None
    finally:
        ac.close()


def test_get_principal_unknown(tokens: dict[str, str]) -> None:
    ac = AccessControl()
    try:
        assert ac.get_principal("nobody") is None
    finally:
        ac.close()


def test_reseed_is_idempotent(access_spec_path: str) -> None:
    ac = AccessControl()
    try:
        spec = load_access_spec(access_spec_path)
        seed_access(ac, spec)
        seed_access(ac, spec)  # second run must not error or duplicate
        principals = ac.list_principals()
        usernames = {p.username for p in principals}
        assert {"jeff", "julia", "sam", "brian"} <= usernames
    finally:
        ac.close()
