"""
Definitions knowledge base API — grouped, slug-addressed, public read-only.

Routes:
  GET /astroprocessor/definitions/groups/               -> list groups
  GET /astroprocessor/definitions/groups/<slug>/        -> items for group
  GET /astroprocessor/definitions/groups/<slug>/<item>/ -> single definition
"""
import re
import unicodedata

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny

from astroprocessor.models import AstroprocessorType, AstroprocessorData
from utils.multilinguality import MultilingualityViewMixin, get_language_value


# ---------------------------------------------------------------------------
# Slug helpers
# ---------------------------------------------------------------------------

# Known slug mapping for the fixed type ids.
TYPE_SLUG_MAP = {
    1: "znaki-zodiaka",
    2: "nakshatry",
    3: "planety",
    4: "karaki",
    5: "arudhi",
    6: "doma",
    7: "planeta-v-znake",
    8: "tip-doma",
}

# Reverse map: slug -> type id
SLUG_TYPE_MAP = {v: k for k, v in TYPE_SLUG_MAP.items()}

# Cyrillic → latin transliteration table
_CYR_MAP = {
    'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e',
    'ё': 'yo', 'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'j', 'к': 'k',
    'л': 'l', 'м': 'm', 'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r',
    'с': 's', 'т': 't', 'у': 'u', 'ф': 'f', 'х': 'kh', 'ц': 'ts',
    'ч': 'ch', 'ш': 'sh', 'щ': 'shch', 'ъ': '', 'ы': 'y', 'ь': '',
    'э': 'e', 'ю': 'yu', 'я': 'ya',
}


def _transliterate(text: str) -> str:
    """Transliterate a Cyrillic string to ASCII latin."""
    result = []
    for ch in text.lower():
        if ch in _CYR_MAP:
            result.append(_CYR_MAP[ch])
        else:
            # Keep ASCII letters/digits; try Unicode normalisation for others
            normalized = unicodedata.normalize('NFKD', ch)
            ascii_ch = normalized.encode('ascii', 'ignore').decode('ascii')
            result.append(ascii_ch)
    return ''.join(result)


def slugify_name(text: str) -> str:
    """Convert a name (possibly Cyrillic) to a URL-safe slug."""
    if not text:
        return ''
    transliterated = _transliterate(text)
    # Replace non-alphanumeric with hyphen
    slug = re.sub(r'[^a-z0-9]+', '-', transliterated)
    # Strip leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def get_item_slug(obj: AstroprocessorData, lang: str = 'ru') -> str:
    """Derive a stable slug for an AstroprocessorData row."""
    name_dict = obj.name or {}
    # Try requested lang first, fallback to 'ru', then any value
    name = name_dict.get(lang) or name_dict.get('ru') or next(iter(name_dict.values()), '')
    # Strip HTML tags if any leaked in
    name = re.sub(r'<[^>]+>', '', name).strip()
    slug = slugify_name(name)
    return slug or str(obj.id)


# ---------------------------------------------------------------------------
# Language helper for view mixins without queryset
# ---------------------------------------------------------------------------

def _get_language_code(request) -> str:
    from utils.multilinguality import get_default_language_code
    lang = request.query_params.get('language_code') or request.query_params.get('lang')
    if lang:
        return lang.split('-')[0].lower()
    accept_lang = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
    if accept_lang:
        primary = accept_lang.split(',')[0].split(';')[0].strip()
        if primary:
            return primary.split('-')[0].lower()
    user = request.user
    if user and user.is_authenticated and getattr(user, 'language', None):
        return user.language.split('-')[0].lower()
    return get_default_language_code()


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------

def _serialize_type(type_obj: AstroprocessorType, slug: str, count: int, lang: str) -> dict:
    return {
        "id": type_obj.id,
        "slug": slug,
        "name": get_language_value(type_obj.name, lang),
        "count": count,
    }


def _serialize_item_list(obj: AstroprocessorData, lang: str) -> dict:
    return {
        "id": obj.id,
        "slug": get_item_slug(obj, lang),
        "name": get_language_value(obj.name, lang),
    }


def _serialize_item_detail(obj: AstroprocessorData, group_slug: str, lang: str) -> dict:
    group_type = obj.type
    return {
        "id": obj.id,
        "slug": get_item_slug(obj, lang),
        "group": {
            "id": group_type.id,
            "slug": group_slug,
            "name": get_language_value(group_type.name, lang),
        },
        "name": get_language_value(obj.name, lang),
        "description": get_language_value(obj.description, lang) if obj.description else None,
    }


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class DefinitionGroupListView(APIView):
    """GET /astroprocessor/definitions/groups/"""
    permission_classes = [AllowAny]

    def get(self, request):
        lang = _get_language_code(request)
        # Gather counts per type for public items
        from django.db.models import Count
        counts = (
            AstroprocessorData.objects.filter(is_public=True)
            .values('type_id')
            .annotate(cnt=Count('id'))
        )
        count_map = {row['type_id']: row['cnt'] for row in counts}

        groups = []
        # Only expose types that have a slug in our map AND have >= 1 public item
        for type_id, slug in sorted(TYPE_SLUG_MAP.items()):
            cnt = count_map.get(type_id, 0)
            if cnt == 0:
                continue
            try:
                type_obj = AstroprocessorType.objects.get(id=type_id)
            except AstroprocessorType.DoesNotExist:
                continue
            groups.append(_serialize_type(type_obj, slug, cnt, lang))

        return Response(groups)


class DefinitionGroupDetailView(APIView):
    """GET /astroprocessor/definitions/groups/<slug>/"""
    permission_classes = [AllowAny]

    def get(self, request, slug):
        lang = _get_language_code(request)
        type_id = SLUG_TYPE_MAP.get(slug)
        if type_id is None:
            return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            type_obj = AstroprocessorType.objects.get(id=type_id)
        except AstroprocessorType.DoesNotExist:
            return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

        items_qs = AstroprocessorData.objects.filter(type=type_obj, is_public=True).order_by('internal_id')
        if not items_qs.exists():
            return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

        group_data = {
            "id": type_obj.id,
            "slug": slug,
            "name": get_language_value(type_obj.name, lang),
            "count": items_qs.count(),
        }
        items = [_serialize_item_list(obj, lang) for obj in items_qs]

        return Response({"group": group_data, "items": items})


class DefinitionItemDetailView(APIView):
    """GET /astroprocessor/definitions/groups/<slug>/<item_slug>/"""
    permission_classes = [AllowAny]

    def get(self, request, slug, item_slug):
        lang = _get_language_code(request)
        type_id = SLUG_TYPE_MAP.get(slug)
        if type_id is None:
            return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

        try:
            type_obj = AstroprocessorType.objects.get(id=type_id)
        except AstroprocessorType.DoesNotExist:
            return Response({"detail": "Group not found."}, status=status.HTTP_404_NOT_FOUND)

        items_qs = AstroprocessorData.objects.filter(type=type_obj, is_public=True).select_related('type')

        # Try numeric id fallback first
        if item_slug.isdigit():
            try:
                obj = items_qs.get(id=int(item_slug))
                return Response(_serialize_item_detail(obj, slug, lang))
            except AstroprocessorData.DoesNotExist:
                pass

        # Match by derived slug
        matched = None
        for obj in items_qs:
            if get_item_slug(obj, lang) == item_slug:
                matched = obj
                break

        if matched is None:
            return Response({"detail": "Definition not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response(_serialize_item_detail(matched, slug, lang))
