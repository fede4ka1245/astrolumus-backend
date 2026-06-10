import random

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import (
    TarotCard,
    TarotReading,
    TarotSpread,
    get_usage_snapshot,
    try_consume,
)


def _serialize_card(card: TarotCard) -> dict:
    return {
        "code": card.code,
        "name": card.name,
        "arcana": card.arcana,
        "suit": card.suit,
        "number": card.number,
        "image_url": card.image_url,
        "upright_meaning": card.upright_meaning,
        "reversed_meaning": card.reversed_meaning,
        "keywords": card.keywords or [],
    }


def _serialize_spread(s: TarotSpread) -> dict:
    return {
        "code": s.code,
        "name": s.name,
        "description": s.description,
        "card_count": s.card_count,
        "positions": s.positions or [],
    }


def _serialize_snapshot(snapshot: dict) -> dict:
    """Flatten {'monthly':{...}, 'daily':{...}} for the frontend."""
    monthly = snapshot.get("monthly", {})
    daily = snapshot.get("daily", {})
    return {
        "enabled": snapshot.get("enabled", False),
        "limit_per_month": monthly.get("limit", 0),
        "limit_per_day": daily.get("limit", 0),
        "used_today": daily.get("used", 0),
        "used_this_month": monthly.get("used", 0),
        "remaining_today": daily.get("remaining"),
        "remaining_month": monthly.get("remaining"),
    }


@api_view(["GET"])
@permission_classes([AllowAny])
def spread_list(request):
    spreads = TarotSpread.objects.filter(is_active=True).order_by("sort_order", "card_count")
    return Response([_serialize_spread(s) for s in spreads])


@api_view(["GET"])
@permission_classes([AllowAny])
def card_list(request):
    cards = TarotCard.objects.all()
    return Response([_serialize_card(c) for c in cards])


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tarot_usage(request):
    return Response(_serialize_snapshot(get_usage_snapshot(request.user)))


def _compose_interpretation(spread: TarotSpread, drawn: list) -> str:
    lines = []
    for d in drawn:
        card = d["card"]
        position = d["position"]
        meaning = card["reversed_meaning"] if d["reversed"] else card["upright_meaning"]
        rev = " (перевёрнута)" if d["reversed"] else ""
        lines.append(f"{position}: {card['name']}{rev} — {meaning}")
    body = "\n\n".join(lines)
    if spread.card_count > 1:
        body += "\n\nВместе карты складываются в общий ответ — обратите внимание на пересечения тем."
    return body


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reading_create(request):
    spread_code = (request.data.get("spread") or "").strip()
    question = (request.data.get("question") or "").strip()

    if not spread_code:
        return Response({"detail": "Не указан расклад"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        spread = TarotSpread.objects.get(code=spread_code, is_active=True)
    except TarotSpread.DoesNotExist:
        return Response({"detail": "Unknown spread"}, status=status.HTTP_400_BAD_REQUEST)

    # Quota check + atomic debit before drawing the cards.
    consumed = try_consume(request.user)
    if not consumed["ok"]:
        snapshot = _serialize_snapshot(consumed["snapshot"])
        if consumed["reason"] == "no_access":
            return Response(
                {
                    "detail": "Раскладов Таро нет в вашем тарифе.",
                    "reason": consumed["reason"],
                    "quota": snapshot,
                },
                status=status.HTTP_403_FORBIDDEN,
            )
        return Response(
            {
                "detail": "Лимит раскладов исчерпан.",
                "reason": consumed["reason"],
                "quota": snapshot,
            },
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    cards = list(TarotCard.objects.all())
    if len(cards) < spread.card_count:
        return Response(
            {"detail": "Колода не загружена. Обратитесь к администратору."},
            status=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    picked = random.sample(cards, spread.card_count)
    positions = (spread.positions or [])[: spread.card_count]
    if len(positions) < spread.card_count:
        positions = positions + [f"Позиция {i + 1}" for i in range(len(positions), spread.card_count)]

    drawn = [
        {
            "position": positions[i],
            "card": _serialize_card(picked[i]),
            "reversed": random.random() < 0.5,
        }
        for i in range(spread.card_count)
    ]

    interpretation = _compose_interpretation(spread, drawn)

    reading = TarotReading.objects.create(
        user=request.user,
        spread=spread,
        question=question,
        drawn=drawn,
        interpretation=interpretation,
    )

    return Response(
        {
            "reading_id": reading.id,
            "drawn": drawn,
            "interpretation": interpretation,
            "quota": _serialize_snapshot(consumed["snapshot"]),
        },
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def reading_list(request):
    qs = TarotReading.objects.filter(user=request.user).select_related("spread").order_by("-created_at")[:50]
    return Response(
        [
            {
                "id": r.id,
                "spread": _serialize_spread(r.spread),
                "question": r.question,
                "drawn": r.drawn,
                "interpretation": r.interpretation,
                "created_at": r.created_at.isoformat(),
            }
            for r in qs
        ]
    )
