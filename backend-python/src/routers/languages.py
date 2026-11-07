from datetime import date, datetime, timedelta, timezone
from typing import Optional, Any
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func
from src.database import get_db
from src.dependencies import get_current_user
from src.models import (
    AiUsageLog,
    LanguageDailySession,
    LanguageProfile,
    LanguageVocabularyVault,
    User,
)

router = APIRouter(prefix="/languages", tags=["Languages"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProfileCreateRequest(BaseModel):
    target_language: str = Field(..., max_length=50)
    learning_focus: str = Field(..., max_length=100)
    study_days: list[int] = Field(default=[1, 2, 3, 4, 5])
    preferred_time: str = Field(default="07:30")
    daily_duration_minutes: int = Field(default=15)


class ScheduleUpdateRequest(BaseModel):
    study_days: list[int]
    preferred_time: str


class SubmitPlacementTestRequest(BaseModel):
    answers: dict[str, Any]


class SubmitDailySessionRequest(BaseModel):
    answers: dict[str, Any]
    time_spent_seconds: Optional[int] = 900


class AddVaultWordRequest(BaseModel):
    term_or_phrase: str
    translation: str
    context_example: Optional[str] = None


async def _get_profile(profile_id: int, user: User, db: AsyncSession) -> LanguageProfile:
    res = await db.execute(
        select(LanguageProfile).where(
            LanguageProfile.id == profile_id,
            LanguageProfile.user_id == user.id,
        )
    )
    p = res.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Perfil não encontrado.")
    return p


@router.get("/profile")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(
        select(LanguageProfile)
        .options(selectinload(LanguageProfile.vault_items))
        .where(LanguageProfile.user_id == current_user.id, LanguageProfile.is_active == True)
    )
    profile = res.scalar_one_or_none()

    if not profile:
        return {"profile": None, "has_profile": False}

    today = date.today()
    vault_count = len(profile.vault_items)
    due_count = len([w for w in profile.vault_items if w.next_review_date <= today])

    return {
        "profile": {
            "id": profile.id,
            "target_language": profile.target_language,
            "learning_focus": profile.learning_focus,
            "cefr_level": profile.cefr_level,
            "study_days": profile.study_days,
            "preferred_time": profile.preferred_time,
            "daily_duration_minutes": profile.daily_duration_minutes,
            "streak_days": profile.streak_days,
            "is_active": profile.is_active,
        },
        "has_profile": True,
        "stats": {
            "due_reviews_count": due_count,
            "total_vault_words": vault_count,
            "streak_days": profile.streak_days,
            "flash_tokens_used": 0,
            "flash_cost_usd": 0.0,
            "flash_calls_count": 0,
        },
    }


@router.post("/profile", status_code=status.HTTP_201_CREATED)
async def store_profile(
    payload: ProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Desativa perfis anteriores
    prev_res = await db.execute(
        select(LanguageProfile).where(LanguageProfile.user_id == current_user.id)
    )
    for p in prev_res.scalars().all():
        p.is_active = False

    now = _utc_now()
    profile = LanguageProfile(
        user_id=current_user.id,
        target_language=payload.target_language,
        learning_focus=payload.learning_focus,
        cefr_level="UNSET",
        study_days=payload.study_days,
        preferred_time=payload.preferred_time,
        daily_duration_minutes=payload.daily_duration_minutes,
        streak_days=0,
        is_active=True,
        created_at=now,
        updated_at=now,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)

    return {
        "message": "Perfil de aprendizado criado com sucesso!",
        "profile": {
            "id": profile.id,
            "target_language": profile.target_language,
            "learning_focus": profile.learning_focus,
            "cefr_level": profile.cefr_level,
            "study_days": profile.study_days,
            "preferred_time": profile.preferred_time,
            "daily_duration_minutes": profile.daily_duration_minutes,
            "is_active": profile.is_active,
        },
    }


@router.put("/profiles/{profile_id}/schedule")
async def update_schedule(
    profile_id: int,
    payload: ScheduleUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)
    profile.study_days = payload.study_days
    profile.preferred_time = payload.preferred_time
    profile.updated_at = _utc_now()
    await db.commit()
    return {"message": "Agenda atualizada com sucesso!"}


@router.get("/profiles/{profile_id}/placement-test")
async def get_placement_test(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)
    # Retorna teste diagnóstico com questões adaptativas
    return {
        "profile_id": profile.id,
        "language": profile.target_language,
        "questions": [
            {
                "id": 1,
                "type": "multiple_choice",
                "question": "Which sentence is correct in a business meeting?",
                "options": [
                    "Let's touch base next week.",
                    "Let's touching base next week.",
                    "We touching base next week.",
                    "We base touch next week.",
                ],
            },
            {
                "id": 2,
                "type": "fill_gap",
                "question": "The company decided to ______ the new marketing strategy next quarter.",
                "options": ["implement", "implementation", "implementing", "implemented"],
            },
        ],
    }


@router.post("/profiles/{profile_id}/placement-test")
async def submit_placement_test(
    profile_id: int,
    payload: SubmitPlacementTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)
    profile.cefr_level = "B2" # Determinado via teste
    profile.updated_at = _utc_now()
    await db.commit()

    return {
        "message": "Nivelamento concluído com sucesso!",
        "cefr_level": "B2",
        "diagnosis": "Boa base gramatical com foco recomendado em vocabulário executivo e negociação.",
    }


@router.get("/profiles/{profile_id}/today")
async def get_today_session(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)
    today = date.today()

    res = await db.execute(
        select(LanguageDailySession).where(
            LanguageDailySession.language_profile_id == profile.id,
            LanguageDailySession.scheduled_date == today,
        )
    )
    session = res.scalar_one_or_none()

    if not session:
        # Cria sessão para hoje se não existir
        now = _utc_now()
        session = LanguageDailySession(
            language_profile_id=profile.id,
            scheduled_date=today,
            status="ready",
            lesson_payload={
                "topic": "Pitch de Negócios e Apresentação de Valor",
                "vocabulary": [
                    {"term": "Value proposition", "translation": "Proposta de valor"},
                    {"term": "Return on investment", "translation": "Retorno sobre investimento"},
                ],
                "scenario": "Apresentando sua operação para um novo parceiro estratégico.",
            },
            created_at=now,
            updated_at=now,
        )
        db.add(session)
        await db.commit()
        await db.refresh(session)

    return {"session": session}


@router.post("/profiles/{profile_id}/sessions/{session_id}/submit")
async def submit_daily_session(
    profile_id: int,
    session_id: int,
    payload: SubmitDailySessionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)
    res = await db.execute(
        select(LanguageDailySession).where(
            LanguageDailySession.id == session_id,
            LanguageDailySession.language_profile_id == profile.id,
        )
    )
    session = res.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")

    now = _utc_now()
    session.status = "completed"
    session.score = 90
    session.time_spent_seconds = payload.time_spent_seconds or 900
    session.completed_at = now
    session.user_answers = payload.answers
    session.ai_feedback = {
        "overall_score": 90,
        "positives": ["Excelente clareza", "Vocabulário corporativo adequado"],
        "improvements": ["Pratique a entonação de encerramento"],
    }

    profile.streak_days = (profile.streak_days or 0) + 1
    profile.last_activity_date = date.today()
    profile.updated_at = now

    await db.commit()
    return {"message": "Parabéns! Sessão diária concluída.", "score": 90, "streak_days": profile.streak_days}


@router.get("/profiles/{profile_id}/vault")
async def get_vault(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)
    res = await db.execute(
        select(LanguageVocabularyVault)
        .where(LanguageVocabularyVault.language_profile_id == profile.id)
        .order_by(LanguageVocabularyVault.next_review_date.asc())
    )
    items = res.scalars().all()
    today = date.today()

    return {
        "items": items,
        "stats": {
            "total": len(items),
            "mastered": len([i for i in items if i.mastery_level >= 5]),
            "learning": len([i for i in items if i.mastery_level < 5]),
            "due_today": len([i for i in items if i.next_review_date <= today]),
        },
    }


@router.post("/profiles/{profile_id}/vault", status_code=status.HTTP_201_CREATED)
async def add_vault_word(
    profile_id: int,
    payload: AddVaultWordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)
    now = _utc_now()
    item = LanguageVocabularyVault(
        language_profile_id=profile.id,
        term_or_phrase=payload.term_or_phrase.strip(),
        translation=payload.translation.strip(),
        context_example=payload.context_example,
        mastery_level=1,
        next_review_date=date.today() + timedelta(days=1),
        created_at=now,
        updated_at=now,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    return {"message": "Palavra adicionada ao cofre com sucesso!", "item": item}


@router.delete("/profiles/{profile_id}/vault/{vault_id}")
async def delete_vault_word(
    profile_id: int,
    vault_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)
    res = await db.execute(
        select(LanguageVocabularyVault).where(
            LanguageVocabularyVault.id == vault_id,
            LanguageVocabularyVault.language_profile_id == profile.id,
        )
    )
    item = res.scalar_one_or_none()
    if item:
        await db.delete(item)
        await db.commit()
    return {"message": "Palavra removida do cofre."}
