import pytest
from fastapi import HTTPException
from src.auth.models import Role, RoleLevel, User, ROLE_HIERARCHY
from src.auth.rbac import require_role_level


def test_role_hierarchy_ordering():
    assert ROLE_HIERARCHY[Role.SUPER_ADMIN] > ROLE_HIERARCHY[Role.BENCHMARK_ADMIN]
    assert ROLE_HIERARCHY[Role.BENCHMARK_ADMIN] > ROLE_HIERARCHY[Role.ANALYST]
    assert ROLE_HIERARCHY[Role.ANALYST] > ROLE_HIERARCHY[Role.USER]
    assert ROLE_HIERARCHY[Role.USER] == ROLE_HIERARCHY[Role.SERVICE_ACCOUNT]


@pytest.mark.asyncio
async def test_require_role_level_allows_higher_role():
    checker = require_role_level(RoleLevel.ANALYST)
    admin_user = User(
        id="u1",
        email="admin@test.com",
        username="admin",
        role=Role.BENCHMARK_ADMIN,
        hashed_password="hash",
    )
    result = await checker(current_user=admin_user)
    assert result.username == "admin"


@pytest.mark.asyncio
async def test_require_role_level_denies_lower_role():
    checker = require_role_level(RoleLevel.BENCHMARK_ADMIN)
    standard_user = User(
        id="u2",
        email="user@test.com",
        username="norman",
        role=Role.USER,
        hashed_password="hash",
    )
    with pytest.raises(HTTPException) as exc_info:
        await checker(current_user=standard_user)
    assert exc_info.value.status_code == 403
    assert "Operation not permitted" in exc_info.value.detail
