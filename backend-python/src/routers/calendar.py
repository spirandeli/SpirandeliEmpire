import secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from icalendar import Calendar, Event
from src.database import get_db
from src.dependencies import get_current_user
from src.models import CalendarEvent, User

router = APIRouter(prefix="/v1/calendar", tags=["Calendar"])


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _build_ics(events: list[CalendarEvent], prod_id: str = "-//SpirandeliEmpire//ABVOS Calendar//PT") -> str:
    cal = Calendar()
    cal.add("prodid", prod_id)
    cal.add("version", "2.0")
    cal.add("calscale", "GREGORIAN")
    cal.add("x-wr-calname", "Spirandeli Empire Agenda")

    for ev in events:
        event = Event()
        event.add("summary", ev.title)
        if ev.description:
            event.add("description", ev.description)
        if ev.location:
            event.add("location", ev.location)
        if ev.starts_at:
            event.add("dtstart", ev.starts_at)
        if ev.ends_at:
            event.add("dtend", ev.ends_at)
        event.add("uid", f"abvos-event-{ev.id}@spirandeli.io")
        event.add("dtstamp", _utc_now())
        cal.add_component(event)

    return cal.to_ical().decode("utf-8")


@router.get("/feed/{calendar_token}")
async def calendar_feed(calendar_token: str, db: AsyncSession = Depends(get_db)):
    clean_token = calendar_token.replace(".ics", "")

    res = await db.execute(select(User).where(User.calendar_token == clean_token))
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Feed de calendário não encontrado.")

    # Busca eventos do usuário
    events_res = await db.execute(
        select(CalendarEvent).where(CalendarEvent.user_id == user.id)
    )
    events = list(events_res.scalars().all())

    ics_data = _build_ics(events)

    return Response(
        content=ics_data,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": 'inline; filename="agenda.ics"',
            "Cache-Control": "no-cache, no-store, max-age=0, must-revalidate",
        },
    )


@router.get("/events/{event_id}/download")
async def download_single_event(
    event_id: int,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(CalendarEvent).where(CalendarEvent.id == event_id))
    ev = res.scalar_one_or_none()
    if not ev:
        raise HTTPException(status_code=404, detail="Evento não encontrado.")

    ics_data = _build_ics([ev])
    return Response(
        content=ics_data,
        media_type="text/calendar; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="evento-{ev.id}.ics"',
            "Cache-Control": "no-cache, no-store, max-age=0, must-revalidate",
        },
    )


@router.get("/me/feed-url")
async def get_my_feed_url(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.calendar_token:
        current_user.calendar_token = secrets.token_urlsafe(32)
        await db.commit()

    token = current_user.calendar_token
    feed_url = f"http://localhost:8080/api/v1/calendar/feed/{token}.ics"
    webcal_url = feed_url.replace("http://", "webcal://").replace("https://", "webcal://")

    # Contagem de eventos futuros
    upcoming_res = await db.execute(
        select(CalendarEvent).where(
            CalendarEvent.user_id == current_user.id,
            CalendarEvent.starts_at >= _utc_now(),
        )
    )
    upcoming_count = len(upcoming_res.scalars().all())

    return {
        "calendar_token": token,
        "feed_url": feed_url,
        "webcal_url": webcal_url,
        "upcoming_events_count": upcoming_count,
    }

