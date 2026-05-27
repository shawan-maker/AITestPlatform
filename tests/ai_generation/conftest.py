import asyncio
import os
import uuid

import pytest

os.environ.setdefault("API_TEST_GEN_MOCK", "1")
os.environ.setdefault("FUNCTIONAL_GEN_MOCK", "1")


@pytest.fixture
async def db():
    from service.core.database import close_db, init_db

    await init_db()
    yield
    await close_db()


@pytest.fixture
async def admin_user(db):
    from service.user.models import User

    user = await User.get_or_none(username="admin", is_deleted=False)
    if user is None:
        pytest.skip("需要 admin 用户，请先初始化数据库")
    return user


@pytest.fixture
async def api_gen_context(db, admin_user):
    from service.api_test.interface.models import ApiInterfaceCatalog
    from service.project.models import Project
    from service.test_environment.models import TestEnvironment

    suffix = uuid.uuid4().hex[:8]
    project = await Project.create(
        name=f"ai-gen-test-{suffix}",
        description="ai generation test",
        owner_id=admin_user.id,
    )
    catalog = await ApiInterfaceCatalog.create(
        project_id=project.id,
        name=f"cat-{suffix}",
        level=1,
        sort_order=0,
    )
    env = await TestEnvironment.create(
        project_id=project.id,
        env_name=f"env-{suffix}",
    )
    ctx = {
        "user": admin_user,
        "project_id": project.id,
        "catalog_id": catalog.id,
        "environment_id": env.id,
    }
    yield ctx
    from service.ai_generation.models import AIGenerationSession
    from service.api_test.models import ApiBaseCase, ApiTestCase

    await ApiTestCase.filter(project_id=project.id).delete()
    await ApiBaseCase.filter(project_id=project.id).delete()
    await AIGenerationSession.filter(project_id=project.id).delete()
    from service.api_test.interface.models import ApiInterface

    await ApiInterface.filter(project_id=project.id).delete()
    await env.delete()
    await catalog.delete()
    await project.delete()


@pytest.fixture
async def agent_context(db, admin_user):
    from service.api_test.interface.models import ApiInterface, ApiInterfaceCatalog
    from service.core.enums import ProjectMemberRole
    from service.core.security import hash_password
    from service.functional_test.case.models import FunctionalCaseCatalog
    from service.project.models import Project, ProjectMember
    from service.test_environment.models import TestEnvironment
    from service.user.models import User

    suffix = uuid.uuid4().hex[:8]
    project = await Project.create(
        name=f"agent-test-{suffix}",
        description="agent api test",
        owner_id=admin_user.id,
    )
    func_catalog = await FunctionalCaseCatalog.create(
        project_id=project.id,
        name=f"func-cat-{suffix}",
        level=1,
        sort_order=0,
    )
    api_catalog = await ApiInterfaceCatalog.create(
        project_id=project.id,
        name=f"api-cat-{suffix}",
        level=1,
        sort_order=0,
    )
    env = await TestEnvironment.create(
        project_id=project.id,
        env_name=f"env-{suffix}",
    )
    iface = await ApiInterface.create(
        project_id=project.id,
        catalog_id=api_catalog.id,
        method="GET",
        path=f"/agent/{suffix}",
        summary="agent test interface",
        parameters={"header": [], "path": [], "query": []},
        responses=[],
        version=1,
        is_current=True,
    )

    viewer = await User.create(
        username=f"viewer-{suffix}",
        email=f"viewer-{suffix}@test.local",
        password_hash=hash_password("test1234"),
    )
    editor = await User.create(
        username=f"editor-{suffix}",
        email=f"editor-{suffix}@test.local",
        password_hash=hash_password("test1234"),
    )
    await ProjectMember.create(
        project_id=project.id,
        user_id=viewer.id,
        role=ProjectMemberRole.viewer.value,
    )
    await ProjectMember.create(
        project_id=project.id,
        user_id=editor.id,
        role=ProjectMemberRole.editor.value,
    )

    ctx = {
        "project_id": project.id,
        "func_catalog_id": func_catalog.id,
        "api_catalog_id": api_catalog.id,
        "environment_id": env.id,
        "interface_id": iface.id,
        "viewer": viewer,
        "editor": editor,
    }
    yield ctx

    from service.ai_generation.models import AIGenerationSession
    from service.api_test.models import ApiBaseCase, ApiTestCase
    from service.functional_test.case.models import FunctionalCase

    await FunctionalCase.filter(project_id=project.id).delete()
    await ApiTestCase.filter(project_id=project.id).delete()
    await ApiBaseCase.filter(project_id=project.id).delete()
    await AIGenerationSession.filter(project_id=project.id).delete()
    await ApiInterface.filter(project_id=project.id).delete()
    await ProjectMember.filter(project_id=project.id).delete()
    await viewer.delete()
    await editor.delete()
    await env.delete()
    await api_catalog.delete()
    await func_catalog.delete()
    await project.delete()


async def wait_for_functional_session(session_id: int, user):
    from service.ai_generation.functional_agent_service import FunctionalAgentService
    from service.core.enums import SessionStatus

    for _ in range(100):
        session = await FunctionalAgentService.get_session(user, session_id)
        if session.status in (SessionStatus.success, SessionStatus.failed):
            return session
        await asyncio.sleep(0.05)
    raise AssertionError("functional session did not finish in time")
