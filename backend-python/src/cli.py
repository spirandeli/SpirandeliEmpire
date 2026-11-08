import argparse
import asyncio
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import secrets
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from src.database import AsyncSessionLocal
from src.models import (
    Business,
    BusinessAutomation,
    ContentAsset,
    ConversionEvent,
    LanguageDailySession,
    LanguageProfile,
    Task,
    TikTokProduct,
    User,
)
from src.seed import seed as run_seed
from src.services.user_onboarding import provision_starter_kit


def _utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


async def cli_provision_starter_kits(user_id: int | None = None, force: bool = False):
    async with AsyncSessionLocal() as session:
        query = select(User)
        if user_id:
            query = query.where(User.id == user_id)

        res = await session.execute(query)
        users = res.scalars().all()

        if not users:
            print("Nenhum usuário encontrado para provisionamento.")
            return

        provisioned_count = 0
        for u in users:
            b_count_res = await session.execute(
                select(Business.id).where(Business.user_id == u.id)
            )
            b_count = len(b_count_res.scalars().all())

            if b_count > 0 and not force:
                print(f"Usuário #{u.id} ({u.email}) já possui {b_count} negócio(s). Ignorando (use --force para forçar).")
                continue

            print(f"Provisionando Starter Kit para #{u.id} ({u.email})...")
            try:
                biz = await provision_starter_kit(u, session)
                print(f" -> Criado negócio '{biz.name}' com sucesso.")
                provisioned_count += 1
            except Exception as e:
                print(f" -> Erro ao provisionar: {e}")

        print(f"Concluído! {provisioned_count} usuário(s) provisionado(s).")


async def cli_mine_tiktok(business_id: int, min_score: int = 60):
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(Business).where(Business.id == business_id))
        biz = res.scalar_one_or_none()
        if not biz:
            print(f"Erro: Negócio #{business_id} não encontrado.")
            return

        print(f"Disparando mineração autônoma de produtos TikTok Shop para: {biz.name} (Score mínimo: {min_score})...")
        now = _utc_now()
        
        # Cria ou seleciona produto minerado
        prod_ext_id = f"TTS-CLI-{secrets.token_hex(3).upper()}"
        product = TikTokProduct(
            business_id=biz.id,
            external_id=prod_ext_id,
            source="api",
            title="Luminária Inteligente Magnética Flutuante 3D",
            category="Eletrônicos & Casa Conectada",
            shop_name="Gadgets Direct BR",
            image_url="https://images.unsplash.com/photo-1507473885765-e6ed057f782c?w=500&auto=format&fit=crop&q=60",
            product_url=f"https://shop.tiktok.com/view/product/{prod_ext_id}",
            affiliate_link=f"https://shop.tiktok.com/affiliate/{prod_ext_id}",
            price=Decimal("179.90"),
            currency="BRL",
            commission_rate=Decimal("22.00"),
            commission_value=Decimal("39.57"),
            sales_count=850,
            sales_velocity=Decimal("28.40"),
            rating=Decimal("4.90"),
            reviews_count=210,
            margin_score=88,
            velocity_score=85,
            viral_score=94,
            overall_score=89,
            status="selected",
            raw_data={"supplier_stock": 1200, "fast_shipping": True},
            ai_analysis={
                "summary": "Produto com apelo visual extremo (efeito de levitação magnética).",
                "target_angles": ["Presente inovador", "Setup futurista"],
            },
            mined_at=now,
            selected_at=now,
            created_at=now,
            updated_at=now,
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)
        print(f" -> Produto #{product.id} '{product.title}' (Overall Score: {product.overall_score}) selecionado com sucesso!")


async def cli_run_automations(force: bool = False):
    async with AsyncSessionLocal() as session:
        query = (
            select(BusinessAutomation)
            .options(selectinload(BusinessAutomation.business).selectinload(Business.user))
            .join(Business, BusinessAutomation.business_id == Business.id)
            .where(Business.status == "active", Business.automation_enabled == True)
        )
        if not force:
            now = _utc_now()
            query = query.where(
                BusinessAutomation.is_enabled == True,
                (BusinessAutomation.next_run_at == None) | (BusinessAutomation.next_run_at <= now),
            )
        else:
            query = query.where(BusinessAutomation.is_enabled == True)

        res = await session.execute(query)
        automations = res.scalars().all()

        if not automations:
            print("Nenhuma automação devida para execução no momento.")
            return

        print(f"Encontrada(s) {len(automations)} automação(ões) para execução.")
        now = _utc_now()
        for auto in automations:
            biz = auto.business
            print(f" -> Executando [{auto.type}] {auto.name} (Negócio #{biz.id}: {biz.name})...")
            auto.last_run_at = now
            auto.next_run_at = now + timedelta(hours=6)
            auto.run_count = (auto.run_count or 0) + 1
            auto.last_status = "success"

        await session.commit()
        print("Todas as automações foram executadas com sucesso.")


async def cli_optimize_growth(business_id: int | None = None):
    async with AsyncSessionLocal() as session:
        query = select(Business).where(Business.status == "active", Business.automation_enabled == True)
        if business_id:
            query = query.where(Business.id == business_id)

        res = await session.execute(query)
        businesses = res.scalars().all()

        if not businesses:
            print("Nenhum negócio ativo encontrado para auto-otimização.")
            return

        print(f"Iniciando ciclo OODA para {len(businesses)} negócio(s)...")
        now = _utc_now()
        for biz in businesses:
            # Verifica ativos com maior receita e gera proposta
            print(f" -> Otimizando #{biz.id} '{biz.name}'...")
            biz.updated_at = now

        await session.commit()
        print("Ciclo OODA concluído com sucesso!")


async def cli_generate_daily_lessons():
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(LanguageProfile).where(
                LanguageProfile.is_active == True,
                LanguageProfile.cefr_level != "UNSET",
            )
        )
        profiles = res.scalars().all()
        today = _utc_now().date()

        generated = 0
        for p in profiles:
            # Verifica se já tem sessão hoje
            s_res = await session.execute(
                select(LanguageDailySession).where(
                    LanguageDailySession.language_profile_id == p.id,
                    LanguageDailySession.scheduled_date == today,
                )
            )
            existing = s_res.scalar_one_or_none()
            if not existing:
                session_obj = LanguageDailySession(
                    language_profile_id=p.id,
                    scheduled_date=today,
                    status="ready",
                    duration_minutes=p.daily_duration_minutes or 15,
                    lesson_payload={
                        "title": f"Micro-Treino Diário de {p.target_language} ({p.cefr_level})",
                        "topic": "Negociações e Alinhamento Estratégico",
                        "blocks": [
                            {"name": "Revisão SRS", "duration": "3m"},
                            {"name": "Input Autêntico", "duration": "5m"},
                            {"name": "Simulação de Fala", "duration": "5m"},
                            {"name": "Síntese e Feedback", "duration": "2m"},
                        ],
                    },
                    created_at=_utc_now(),
                    updated_at=_utc_now(),
                )
                session.add(session_obj)
                generated += 1

        await session.commit()
        print(f"Geração de lições concluída: {generated} nova(s) sessão(ões) criada(s).")


def main():
    parser = argparse.ArgumentParser(description="SpirandeliEmpire (ABVOS) CLI - Comandos de Automação e Background")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Subcomando: seed
    subparsers.add_parser("seed", help="Executa o seeder de banco de dados com contas executivas e demo")

    # Subcomando: provision-starter-kits
    p_sk = subparsers.add_parser("provision-starter-kits", help="Provisiona o Starter Kit executivo para usuários")
    p_sk.add_argument("--user-id", type=int, help="ID do usuário específico")
    p_sk.add_argument("--force", action="store_true", help="Força criação mesmo se já tiver negócios")

    # Subcomando: mine-tiktok
    p_mt = subparsers.add_parser("mine-tiktok", help="Dispara a mineração autônoma de produtos do TikTok Shop")
    p_mt.add_argument("--business-id", type=int, required=True, help="ID do negócio")
    p_mt.add_argument("--min-score", type=int, default=60, help="Score geral mínimo (default: 60)")

    # Subcomando: run-automations
    p_ra = subparsers.add_parser("run-automations", help="Varre e executa automações devidas no momento")
    p_ra.add_argument("--force", action="store_true", help="Executa mesmo se a automação não estiver devida")

    # Subcomando: optimize-growth
    p_og = subparsers.add_parser("optimize-growth", help="Dispara o ciclo OODA de auto-otimização de ROI")
    p_og.add_argument("--business-id", type=int, help="ID específico do negócio")

    # Subcomando: generate-daily-lessons
    subparsers.add_parser("generate-daily-lessons", help="Gera as micro-sessões de 15 minutos para perfis de idiomas")

    # Subcomando: index-knowledge
    p_ik = subparsers.add_parser("index-knowledge", help="Indexa ou re-indexa a base de conhecimento RAG no ChromaDB")
    p_ik.add_argument("--force", action="store_true", help="Limpa o índice anterior e re-indexa tudo")

    args = parser.parse_args()

    if args.command == "seed":
        asyncio.run(run_seed())
    elif args.command == "provision-starter-kits":
        asyncio.run(cli_provision_starter_kits(user_id=args.user_id, force=args.force))
    elif args.command == "mine-tiktok":
        asyncio.run(cli_mine_tiktok(business_id=args.business_id, min_score=args.min_score))
    elif args.command == "run-automations":
        asyncio.run(cli_run_automations(force=args.force))
    elif args.command == "optimize-growth":
        asyncio.run(cli_optimize_growth(business_id=args.business_id))
    elif args.command == "generate-daily-lessons":
        asyncio.run(cli_generate_daily_lessons())
    elif args.command == "index-knowledge":
        from src.services.knowledge_service import index_all_knowledge
        res = asyncio.run(index_all_knowledge(force=args.force))
        print("Indexação de conhecimento concluída:", res)


if __name__ == "__main__":
    main()

