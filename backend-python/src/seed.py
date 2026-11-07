import asyncio
from datetime import datetime, timezone
from sqlalchemy.future import select
from src.database import AsyncSessionLocal
from src.models import User
from src.security import hash_password
from src.services.user_onboarding import provision_starter_kit


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def seed():
    async with AsyncSessionLocal() as session:
        # 1. Admin Principal
        res = await session.execute(select(User).where(User.email == "admin@spirandeli.com"))
        admin = res.scalar_one_or_none()
        if not admin:
            admin = User(
                name="Alexander Spirandeli (Admin)",
                email="admin@spirandeli.com",
                password=hash_password("Spirandeli2026!"),
                timezone="America/Sao_Paulo",
                agent_enabled=True,
                is_admin=True,
                is_ai_active=True,
                monthly_token_limit=10000000,
                tokens_used_this_month=0,
                created_at=_utc_now(),
                updated_at=_utc_now(),
                last_login_at=_utc_now(),
            )
            session.add(admin)
            await session.commit()
            await session.refresh(admin)
            await provision_starter_kit(admin, session)
            print("ADMIN_USER_READY: admin@spirandeli.com")
        else:
            admin.is_admin = True
            admin.is_ai_active = True
            admin.password = hash_password("Spirandeli2026!")
            await session.commit()
            print("ADMIN_USER_UPDATED: admin@spirandeli.com")

        # 2. Gabriel Mineiro (gabrielomena@msn.com)
        res_g = await session.execute(select(User).where(User.email == "gabrielomena@msn.com"))
        gabriel = res_g.scalar_one_or_none()
        if not gabriel:
            gabriel = User(
                name="Gabriel Mineiro",
                email="gabrielomena@msn.com",
                password=hash_password("Spirandeli2026!"),
                timezone="America/Sao_Paulo",
                agent_enabled=True,
                is_admin=True,
                is_ai_active=True,
                monthly_token_limit=10000000,
                tokens_used_this_month=0,
                created_at=_utc_now(),
                updated_at=_utc_now(),
                last_login_at=_utc_now(),
            )
            session.add(gabriel)
            await session.commit()
            await session.refresh(gabriel)
            await provision_starter_kit(gabriel, session)
            print("GABRIEL_USER_READY: gabrielomena@msn.com")
        else:
            gabriel.is_admin = True
            gabriel.is_ai_active = True
            gabriel.password = hash_password("Spirandeli2026!")
            await session.commit()
            print("GABRIEL_USER_UPDATED: gabrielomena@msn.com")

        # 3. Spirandeli Dev (spirandelidev@gmail.com)
        res_s = await session.execute(select(User).where(User.email == "spirandelidev@gmail.com"))
        spira_dev = res_s.scalar_one_or_none()
        if not spira_dev:
            spira_dev = User(
                name="Alexander Spirandeli",
                email="spirandelidev@gmail.com",
                password=hash_password("Spirandeli2026!"),
                timezone="America/Sao_Paulo",
                agent_enabled=True,
                is_admin=True,
                is_ai_active=True,
                monthly_token_limit=10000000,
                tokens_used_this_month=0,
                created_at=_utc_now(),
                updated_at=_utc_now(),
                last_login_at=_utc_now(),
            )
            session.add(spira_dev)
            await session.commit()
            await session.refresh(spira_dev)
            await provision_starter_kit(spira_dev, session)
            print("SPIRA_DEV_USER_READY: spirandelidev@gmail.com")
        else:
            spira_dev.is_admin = True
            spira_dev.is_ai_active = True
            spira_dev.password = hash_password("Spirandeli2026!")
            await session.commit()
            print("SPIRA_DEV_USER_UPDATED: spirandelidev@gmail.com")

        # 4. Demo
        res = await session.execute(select(User).where(User.email == "demo@spirandeliempire.tech"))
        demo = res.scalar_one_or_none()
        if not demo:
            demo = User(
                name="Visitante Convidado",
                email="demo@spirandeliempire.tech",
                password=hash_password("Demo2026!"),
                timezone="America/Sao_Paulo",
                agent_enabled=True,
                is_admin=False,
                is_ai_active=True,
                monthly_token_limit=5000000,
                tokens_used_this_month=0,
                created_at=_utc_now(),
                updated_at=_utc_now(),
                last_login_at=_utc_now(),
            )
            session.add(demo)
            await session.commit()
            await session.refresh(demo)
            await provision_starter_kit(demo, session)
            print("DEMO_USER_READY: demo@spirandeliempire.tech")
        else:
            print("DEMO_USER_EXISTS: demo@spirandeliempire.tech")


if __name__ == "__main__":
    asyncio.run(seed())

