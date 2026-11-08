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
from src.services.language_service import (
    get_placement_test_payload,
    evaluate_placement_test,
    get_or_create_today_session,
    evaluate_daily_session_submission,
    review_vault_item,
)

router = APIRouter(prefix="/languages", tags=["Languages"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ProfileCreateRequest(BaseModel):
    target_language: str = Field(..., max_length=50)
    learning_focus: str = Field(..., max_length=100)
    study_days: list[Any] = Field(default=[1, 2, 3, 4, 5])
    preferred_time: str = Field(default="07:30")
    daily_duration_minutes: int = Field(default=15)


class ScheduleUpdateRequest(BaseModel):
    study_days: list[Any]
    preferred_time: str


class SubmitPlacementTestRequest(BaseModel):
    answers: Any
    questions: Optional[list[Any]] = None


class SubmitDailySessionRequest(BaseModel):
    answers: Optional[dict[str, Any]] = None
    user_answers: Optional[dict[str, Any]] = None
    time_spent_seconds: Optional[int] = 900


class AddVaultWordRequest(BaseModel):
    term_or_phrase: str
    translation: str
    context_example: Optional[str] = None


class VaultReviewRequest(BaseModel):
    remembered: bool = True


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

    # FinOps: Consulta agregado real de tokens e custos consumidos em idiomas
    ai_stats_res = await db.execute(
        select(
            func.coalesce(func.sum(AiUsageLog.total_tokens), 0),
            func.coalesce(func.sum(AiUsageLog.estimated_cost_usd), 0.0),
            func.count(AiUsageLog.id),
        ).where(
            AiUsageLog.user_id == current_user.id,
            AiUsageLog.context.like("language%"),
        )
    )
    ai_tokens, ai_cost, ai_calls = ai_stats_res.one()

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
            "weaknesses_diagnosis": profile.weaknesses_diagnosis,
            "is_active": profile.is_active,
        },
        "has_profile": True,
        "stats": {
            "due_reviews_count": due_count,
            "total_vault_words": vault_count,
            "streak_days": profile.streak_days,
            "flash_tokens_used": int(ai_tokens or 0),
            "flash_cost_usd": float(ai_cost or 0.0),
            "flash_calls_count": int(ai_calls or 0),
        },
    }


@router.post("/profile", status_code=status.HTTP_201_CREATED)
async def store_profile(
    payload: ProfileCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Desativa perfis anteriores do usuário
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
    return {"message": "Agenda atualizada com sucesso!", "profile": profile}


@router.get("/profiles/{profile_id}/placement-test")
async def get_placement_test(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)
    return get_placement_test_payload(profile)


@router.post("/profiles/{profile_id}/placement-test")
async def submit_placement_test(
    profile_id: int,
    payload: SubmitPlacementTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)

    # Formata respostas recebidas (lista ou dicionário)
    formatted_answers: list[dict[str, Any]] = []
    if isinstance(payload.answers, list):
        formatted_answers = payload.answers
    elif isinstance(payload.answers, dict):
        formatted_answers = [
            {"question_id": int(k), "answer": str(v)}
            for k, v in payload.answers.items()
        ]

    diag = await evaluate_placement_test(profile, formatted_answers, current_user, db)

    return {
        "message": "Nivelamento concluído com sucesso!",
        "cefr_level": diag["cefr_level"],
        "diagnosis": diag["executive_summary"],
        "evaluation": diag,
        "profile": {
            "id": profile.id,
            "target_language": profile.target_language,
            "cefr_level": profile.cefr_level,
            "streak_days": profile.streak_days,
            "weaknesses_diagnosis": profile.weaknesses_diagnosis,
        },
    }


@router.get("/profiles/{profile_id}/today")
async def get_today_session(
    profile_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await _get_profile(profile_id, current_user, db)
    session = await get_or_create_today_session(profile, current_user, db)
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

    user_answers = payload.user_answers or payload.answers or {}
    result = await evaluate_daily_session_submission(
        profile=profile,
        session=session,
        user_answers=user_answers,
        time_spent=payload.time_spent_seconds or 900,
        user=current_user,
        db=db,
    )

    return {
        "message": "Parabéns! Sessão diária concluída.",
        "score": result["score"],
        "streak_days": result["streak_days"],
        "session": result["session"],
        "profile": {
            "id": profile.id,
            "streak_days": profile.streak_days,
            "target_language": profile.target_language,
            "cefr_level": profile.cefr_level,
        },
        "evaluation": result["evaluation"],
    }


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
            "mastered": len([i for i in items if (i.mastery_level or 0) >= 5]),
            "learning": len([i for i in items if (i.mastery_level or 0) < 5]),
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


@router.post("/profiles/{profile_id}/vault/{vault_id}/review")
async def review_vault_word_endpoint(
    profile_id: int,
    vault_id: int,
    payload: VaultReviewRequest,
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
    if not item:
        raise HTTPException(status_code=404, detail="Item do cofre não encontrado.")

    review_vault_item(item, payload.remembered)
    await db.commit()
    await db.refresh(item)

    return {"message": "Revisão registrada com sucesso!", "item": item}


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
