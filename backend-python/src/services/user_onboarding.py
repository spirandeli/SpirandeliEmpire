import secrets
import string
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from src.models import (
    AgentConversation,
    AgentLog,
    AgentMessage,
    ApprovalQueue,
    Business,
    BusinessAutomation,
    ContentAsset,
    ConversionEvent,
    Task,
    TikTokProduct,
    User,
)


def _random_str(length: int = 4) -> str:
    alphabet = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def provision_starter_kit(user: User, db: AsyncSession) -> Business:
    """
    Provisiona instantaneamente um Venture completo de alta fidelidade
    para o usuário (Negócio, Produtos minerados, Ativos, Fila de Aprovação,
    Tarefas Kanban, Conversão e Conversa com o Gemini Co-Pilot).
    """
    first_name = (user.name or "Showcase").split()[0]
    suffix = _random_str(4)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    # 1. Cria o Negócio Modelo TikTok Shop
    business = Business(
        user_id=user.id,
        name=f"TikTok Shop Viral · {first_name}",
        slug=f"tiktok-viral-{user.id}-{suffix}",
        type="tiktok_shop_affiliate",
        archetype="affiliate_tiktok",
        status="active",
        automation_enabled=True,
        activated_at=now,
        niche="Tecnologia & Utilidades Virais",
        description="Operação automatizada de alta performance na TikTok Shop Brasil operada pelo Gemini 3.8 Co-Pilot.",
        north_star_metric="commission_volume",
        target_kpi_value=Decimal("12000.00"),
        webhook_secret_token=secrets.token_urlsafe(30),
        canvas={
            "value_propositions": [
                "Demonstração hipnótica de produtos que solucionam dores imediatas em menos de 30 segundos.",
                "Recomendações curadas com alta pontuação de viralidade e pronta entrega nacional.",
            ],
            "customer_segments": [
                "Público jovem e adulto (18-35 anos) que consome vídeos curtos e compra por impulso.",
            ],
            "channels": [
                "TikTok Shop Vitrine & Vídeos Orgânicos",
                "Instagram Reels & YouTube Shorts",
            ],
            "revenue_streams": [
                "Comissões diretas de afiliado TikTok Shop (20% a 25% por venda concluída).",
            ],
        },
        brand_rules={
            "tone_of_voice": "Enérgico, dinâmico, autêntico e focado em demonstrar o benefício em 3 segundos.",
            "target_audience": "Consumidores de compras por impulso e amantes de novidades tecnológicas no Brasil.",
        },
        created_at=now,
        updated_at=now,
    )
    db.add(business)
    await db.flush()

    # 2. Automação Padrão de Mineração
    automation = BusinessAutomation(
        business_id=business.id,
        type="tiktok_mining",
        name="Mineração de Produtos Virais (6 em 6 horas)",
        cron_expression="0 */6 * * *",
        is_enabled=True,
        next_run_at=now + timedelta(hours=6),
        config={
            "categories": ["Eletrônicos", "Casa & Cozinha"],
            "min_commission_rate": 15,
            "min_price": 50,
            "max_items_per_run": 20,
            "min_overall_score": 70,
        },
        created_at=now,
        updated_at=now,
    )
    db.add(automation)

    # 3. Produtos Minerados Reais
    prod1 = TikTokProduct(
        business_id=business.id,
        external_id=f"TTS-PROJ-{_random_str(6).upper()}",
        source="api",
        title="Mini Projetor Portátil 4K Smart Cinema (Wi-Fi 6 & Bluetooth)",
        category="Eletrônicos & Casa Conectada",
        shop_name="TechShop Global Direct",
        image_url="https://images.unsplash.com/photo-1517604931442-7e0c8ed2963c?w=500&auto=format&fit=crop&q=60",
        product_url="https://shop.tiktok.com/view/product/demo-projector",
        affiliate_link="https://shop.tiktok.com/affiliate/demo-projector",
        price=Decimal("289.90"),
        currency="BRL",
        commission_rate=Decimal("20.00"),
        commission_value=Decimal("57.98"),
        sales_count=1840,
        sales_velocity=Decimal("46.50"),
        rating=Decimal("4.85"),
        reviews_count=430,
        margin_score=85,
        velocity_score=92,
        viral_score=95,
        overall_score=91,
        status="selected",
        raw_data={"supplier_stock": 2500, "fast_shipping": True},
        ai_analysis={
            "summary": "Excelente conversão por apelo visual imediato. Ideal para transformar o teto do quarto em cinema gastando pouco.",
            "target_angles": ["Cinema no quarto sem gastar R$ 3.000", "Ligue no celular e assista na cama"],
        },
        mined_at=now - timedelta(days=2),
        selected_at=now - timedelta(days=1),
        created_at=now,
        updated_at=now,
    )
    db.add(prod1)
    await db.flush()

    # 4. Criativos Validados & Ativos
    asset_code1 = f"TTK-PROJ-{_random_str(4).upper()}"
    asset1 = ContentAsset(
        tracking_code=asset_code1,
        business_id=business.id,
        tiktok_product_id=prod1.id,
        type="video_script",
        platform="tiktok",
        title="Gancho Viral: Cinema no Quarto por R$ 289",
        body="Roteiro de 25s focando no contraste luz apagada vs projeção 4K gigante no teto do quarto.",
        is_selected=True,
        funnel_stage="tof_attraction",
        angle_category="Dor Financeira & Economia",
        total_views=48500,
        total_clicks=2420,
        total_leads=0,
        total_sales_count=120,
        total_revenue_brl=Decimal("6957.60"),
        roi_score=Decimal("89.40"),
        status="published",
        published_at=now - timedelta(days=1),
        created_at=now,
        updated_at=now,
    )
    db.add(asset1)
    await db.flush()

    # 5. Evento de Conversão
    conv_event = ConversionEvent(
        business_id=business.id,
        content_asset_id=asset1.id,
        source_platform="tiktok_shop",
        event_type="purchase_approved",
        external_transaction_id=f"TTS-TX-{_random_str(8).upper()}",
        gross_amount=Decimal("289.90"),
        net_amount=Decimal("57.98"),
        occurred_at=now - timedelta(hours=3),
        created_at=now,
        updated_at=now,
    )
    db.add(conv_event)

    # 6. Tarefas Kanban
    tasks_data = [
        ("Publicar e impulsionar roteiro campeão (Asset: " + asset_code1 + ")", "user", "in_progress", "urgent", 0),
        ("Minerar 5 novos produtos de beleza/skincare com comissão > 20%", "agent", "ready", "high", 1),
        ("Gravar vídeo de 15 segundos usando o gancho 'Cinema no Teto'", "user", "backlog", "medium", 2),
        ("Revisar proposta de novo lote de criativos gerados pelo Gemini", "user", "supervision", "high", 3),
    ]
    for title, assignee, status, priority, pos in tasks_data:
        t = Task(
            business_id=business.id,
            user_id=user.id,
            title=title,
            assignee=assignee,
            status=status,
            priority=priority,
            source="system",
            position=pos,
            created_at=now,
            updated_at=now,
        )
        db.add(t)

    # 7. Item da Fila de Supervisão
    approval_item = ApprovalQueue(
        business_id=business.id,
        user_id=user.id,
        type="tiktok_affiliate_package",
        title=f"Novo Pacote Viral: 3 Ganchos para '{prod1.title[:40]}...'",
        summary="O Gemini Co-Pilot identificou tendência ascendente de buscas e redigiu 3 variações de ganchos hipnóticos para o produto.",
        status="pending",
        priority="high",
        payload={
            "product_id": prod1.id,
            "product_title": prod1.title,
            "commission_value": 57.98,
            "hooks": [
                {"hook": "Você ainda gasta fortuna em cinema? Olha o que eu fiz no teto do meu quarto.", "angle": "Dor Financeira & Economia"},
                {"hook": "Descobri o segredo das pessoas que transformam qualquer parede em uma TV 4K por menos de R$ 300.", "angle": "Curiosidade Viral"},
                {"hook": "Se você joga videogame ou assiste filmes na cama, você PRECISA conhecer esse projetor.", "angle": "Desejo & Conforto"},
            ],
            "caption": "Transformei meu quarto em um cinema 4K gastando menos de 300 reais! 🍿✨",
        },
        created_at=now,
        updated_at=now,
    )
    db.add(approval_item)

    # 8. Conversa Inaugural com Gemini Co-Pilot
    conversation = AgentConversation(
        uuid=str(uuid.uuid4()),
        user_id=user.id,
        business_id=business.id,
        title="Diretoria Executiva · Gemini 3.8 Co-Pilot",
        context_type="business_chat",
        status="active",
        model="gemini-3.8",
        context={
            "business_name": business.name,
            "archetype": business.archetype,
            "top_product": prod1.title,
        },
        messages_count=2,
        created_at=now,
        updated_at=now,
    )
    db.add(conversation)
    await db.flush()

    msg1 = AgentMessage(
        agent_conversation_id=conversation.id,
        role="user",
        content="Olá! Qual é o status atual da minha nova operação no SpirandeliEmpire?",
        created_at=now,
        updated_at=now,
    )
    db.add(msg1)

    msg2 = AgentMessage(
        agent_conversation_id=conversation.id,
        role="model",
        content=f"Olá, **{first_name}**! Seja muito bem-vindo ao **SpirandeliEmpire**.\n\nEu sou o seu **Diretor de Operações (COO) Inteligente** baseado no Gemini 3.8. Já montei a infraestrutura da sua operação **{business.name}** com produtos validados na TikTok Shop e funil de conversão ativo.\n\n📈 **Raio-X da Operação:**\n- **Receita Gerada:** R$ 6.957,60 acumulados através do criativo campeão `{asset_code1}` (ROI Score: 89.4);\n- **Supervisão Humana:** 1 proposta de escalação com 3 novos hooks aguardando seu clique de aprovação na Fila de Supervisão;\n- **Kanban Ativo:** 4 tarefas distribuídas entre trabalho do agente e suas gravações de 15 segundos;\n- **Webhooks Integrados:** Ledger pronto para receber postbacks da Kiwify, Hotmart, TikTok Shop e Stripe.\n\nComo posso acelerar seus resultados agora?",
        created_at=now,
        updated_at=now,
    )
    db.add(msg2)

    # 9. Log de Auditoria
    log = AgentLog(
        user_id=user.id,
        business_id=business.id,
        level="info",
        event="starter_kit_provisioned",
        message=f'Venture demonstrativo "{business.name}" provisionado com sucesso para {user.name}.',
        context={"archetype": business.archetype},
        created_at=now,
    )
    db.add(log)

    await db.commit()
    await db.refresh(business)
    return business


async def provision_dark_channel_kit(user: User, db: AsyncSession) -> Business:
    """
    Provisiona um Venture completo demonstrativo do arquétipo Canal Dark
    (YouTube / TikTok) com roteiro de alta retenção, prompts visuais de B-Roll,
    fila de aprovação, tarefas Kanban e metas de visualizações/AdSense.
    """
    first_name = (user.name or "Showcase").split()[0]
    suffix = _random_str(4)
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    business = Business(
        user_id=user.id,
        name=f"Mistérios da História · {first_name}",
        slug=f"misterios-dark-{user.id}-{suffix}",
        type="dark_channel_automation",
        archetype="canal_dark",
        status="active",
        automation_enabled=True,
        activated_at=now,
        niche="História Oculta & Mistérios Não Resolvidos",
        description="Canal Dark de alta retenção no YouTube e TikTok focado em narrativas imersivas e monetização mista (AdSense + Afiliados).",
        north_star_metric="monthly_views",
        target_kpi_value=Decimal("500000.00"),  # 500k views mensais
        webhook_secret_token=secrets.token_urlsafe(30),
        canvas={
            "value_propositions": [
                "Vídeos magnéticos sem rosto com retenção média superior a 70% nos primeiros 30 segundos.",
                "Monetização escalável através do YouTube AdSense, Creator Rewards e vendas de produtos físicos/digitais no comentário fixado.",
            ],
            "customer_segments": [
                "Público de 18 a 45 anos fascinado por história militar, conspirações e arqueologia misteriosa.",
            ],
            "channels": [
                "YouTube Shorts & YouTube Vídeos Longos (8-12 min)",
                "TikTok Orgânico",
            ],
            "revenue_streams": [
                "YouTube AdSense (RPM médio de R$ 25,00 por mil visualizações)",
                "TikTok Creator Rewards Program",
                "Comissões de afiliados em livros e cursos de história/arqueologia",
            ],
        },
        brand_rules={
            "tone_of_voice": "Solene, enigmático, imersivo, com ritmo dinâmico e pausas dramáticas pontuais.",
            "target_audience": "Amantes de mistérios, documentários históricos e curiosidades no Brasil e países lusófonos.",
        },
        created_at=now,
        updated_at=now,
    )
    db.add(business)
    await db.flush()

    # Automação de Mineração de Temas
    automation = BusinessAutomation(
        business_id=business.id,
        type="dark_channel_mining",
        name="Mineração Diária de Pautas Virais Dark (08:00)",
        cron_expression="0 8 * * *",
        is_enabled=True,
        next_run_at=now + timedelta(hours=8),
        config={
            "niche": business.niche,
            "min_predicted_ctr": 9.5,
            "target_platforms": ["youtube_shorts", "tiktok", "youtube_long"],
        },
        created_at=now,
        updated_at=now,
    )
    db.add(automation)

    # Roteiro Short Dark Modelo
    asset_code_short = f"DARK-{_random_str(6).upper()}"
    short_scenes = [
        {
            "scene_number": 1,
            "timestamp": "00:00 - 00:04",
            "narration": "O homem que você está vendo na tela enganou o exército mais poderoso do planeta com tanques infláveis.",
            "visual_prompt": "Cinematic archival 1944 style, hyper-realistic inflatable Sherman tank being carried by two soldiers, astonishing visual illusion, dramatic war haze, 35mm photograph, Kodak film grain --ar 9:16",
            "b_roll_description": "Corte rápido revelando dois soldados levantando um tanque falso no nevoeiro",
            "on_screen_text": "O EXÉRCITO FANTASMA DE 1944 🚨",
        },
        {
            "scene_number": 2,
            "timestamp": "00:04 - 00:25",
            "narration": "Conhecido como o Exército Fantasma, esta divisão secreta utilizava efeitos sonoros de alta fidelidade e cenografia para salvar milhares de vidas.",
            "visual_prompt": "Secret audio truck with massive loudspeakers in dark European forest at night, moody volumetric lighting, intense dramatic contrast, neo-noir realism --ar 9:16",
            "b_roll_description": "Caminhões com autofalantes gigantes transmitindo barulho de blindados no meio da floresta",
            "on_screen_text": "ÁUDIO DE ALTA POTÊNCIA",
        },
        {
            "scene_number": 3,
            "timestamp": "00:25 - 00:55",
            "narration": "A missão permaneceu ultrassecreta por mais de 50 anos... e a genialidade desse plano quase não pôde ser revelada ao mundo.",
            "visual_prompt": "Close up of confidential military declassification stamp pressing onto top secret document, atmospheric dust, intense warm spotlight in darkness --ar 9:16",
            "b_roll_description": "Carimbo de desclassificação sendo aplicado em relatórios secretos",
            "on_screen_text": "SEGREDO DE 50 ANOS",
        },
    ]

    short_asset = ContentAsset(
        business_id=business.id,
        tracking_code=asset_code_short,
        type="dark_script_short",
        platform="youtube_shorts",
        title="O Exército Fantasma que Enganou uma Guerra",
        body="O homem que você está vendo na tela enganou o exército mais poderoso do planeta com tanques infláveis. Conhecido como o Exército Fantasma, esta divisão secreta utilizava efeitos sonoros de alta fidelidade e cenografia para salvar milhares de vidas. A missão permaneceu ultrassecreta por mais de 50 anos.",
        content={
            "hook": "O homem que você está vendo enganou um exército com tanques infláveis.",
            "cta": "Inscreva-se no canal para mais histórias secretas.",
            "scenes": short_scenes,
            "seo_tags": ["misterios", "segundaguerra", "curiosidades", "fatosreais", "canaldark"],
            "suggested_music": "Dark Suspense Drone 90 BPM with low cello",
            "voice_persona": "Voz grave e solene, estilo documentário investigativo",
        },
        version=1,
        funnel_stage="tof_attraction",
        total_views=142000,
        total_clicks=3820,
        total_leads=410,
        total_sales_count=48,
        total_revenue_brl=Decimal("2390.40"),
        roi_score=Decimal("94.20"),
        status="supervision",
        created_at=now,
        updated_at=now,
    )
    db.add(short_asset)
    await db.flush()

    # Proposta na Fila de Aprovação
    approval = ApprovalQueue(
        business_id=business.id,
        user_id=user.id,
        type="dark_script_approval",
        title=f"Roteiro Canal Dark: {short_asset.title}",
        summary="Roteiro Short de 55 segundos com 3 cenas e prompts de imagem Midjourney prontos para renderização.",
        payload={
            "content_asset_id": short_asset.id,
            "tracking_code": asset_code_short,
            "format_type": "short",
            "platform": "youtube_shorts",
            "scenes": short_scenes,
        },
        status="pending",
        created_at=now,
        updated_at=now,
    )
    db.add(approval)
    await db.flush()
    short_asset.approval_queue_id = approval.id

    # Tarefas no Kanban
    task1 = Task(
        business_id=business.id,
        user_id=user.id,
        title="Renderizar Imagens e Gerar Voz: Exército Fantasma",
        description="Copiar prompts visuais para o Midjourney/Leonardo e sintetizar narração com voz solene no ElevenLabs.",
        assignee="agent",
        status="supervision",
        priority="high",
        source="agent",
        agent_action="dark_channel_production",
        payload={"content_asset_id": short_asset.id, "approval_id": approval.id},
        created_at=now,
        updated_at=now,
    )
    db.add(task1)
    approval.task_id = task1.id

    task2 = Task(
        business_id=business.id,
        user_id=user.id,
        title="Configurar Capas e Títulos de Alto CTR (A/B Test)",
        description="Criar 3 variações de thumbnail com cores contrastantes e tipografia de impacto para teste A/B no YouTube Studio.",
        assignee="user",
        status="in_progress",
        priority="medium",
        source="agent",
        created_at=now,
        updated_at=now,
    )
    db.add(task2)

    await db.commit()
    await db.refresh(business)
    return business

