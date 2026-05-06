from django.contrib import admin
from django.utils.html import mark_safe

from astroprocessor.models import (
    AstroprocessorType,
    SignPlanetConnection, PlanetHouseConnection, MasterHouseConnection,
    ZodiacSignData, NakshatraData, PlanetData, KarakaData,
    ArudhaData, HouseData, PlanetInSignData, HouseTypeData,
)

from utils.multilinguality import get_default_language_value_admin, LocalizedModelAdmin

PLANET_NAMES = {
    1: "Солнце (Sun)",
    2: "Луна (Moon)",
    3: "Марс (Mars)",
    4: "Меркурий (Mercury)",
    5: "Юпитер (Jupiter)",
    6: "Венера (Venus)",
    7: "Сатурн (Saturn)",
    8: "Раху (Rahu)",
    9: "Кету (Ketu)",
}

SIGN_NAMES = {
    1: "Овен (Aries)",
    2: "Телец (Taurus)",
    3: "Близнецы (Gemini)",
    4: "Рак (Cancer)",
    5: "Лев (Leo)",
    6: "Дева (Virgo)",
    7: "Весы (Libra)",
    8: "Скорпион (Scorpio)",
    9: "Стрелец (Sagittarius)",
    10: "Козерог (Capricorn)",
    11: "Водолей (Aquarius)",
    12: "Рыбы (Pisces)",
}

# Управитель дома -> планета (дом -> какая планета им управляет)
HOUSE_RULER_NAMES = {
    1: "Дом 1 — Марс (Mars)",
    2: "Дом 2 — Венера (Venus)",
    3: "Дом 3 — Меркурий (Mercury)",
    4: "Дом 4 — Луна (Moon)",
    5: "Дом 5 — Солнце (Sun)",
    6: "Дом 6 — Меркурий (Mercury)",
    7: "Дом 7 — Венера (Venus)",
    8: "Дом 8 — Марс (Mars)",
    9: "Дом 9 — Юпитер (Jupiter)",
    10: "Дом 10 — Сатурн (Saturn)",
    11: "Дом 11 — Сатурн (Saturn)",
    12: "Дом 12 — Юпитер (Jupiter)",
}

# Дом -> планета-управитель (только имя планеты)
HOUSE_TO_PLANET = {
    1: "Марс (Mars)", 2: "Венера (Venus)", 3: "Меркурий (Mercury)",
    4: "Луна (Moon)", 5: "Солнце (Sun)", 6: "Меркурий (Mercury)",
    7: "Венера (Venus)", 8: "Марс (Mars)", 9: "Юпитер (Jupiter)",
    10: "Сатурн (Saturn)", 11: "Сатурн (Saturn)", 12: "Юпитер (Jupiter)",
}

# --- Mapping type_id -> proxy model ---
# 1: Знаки Зодиака, 2: Накшатры, 3: Планеты, 4: Караки,
# 5: Арудхи, 6: Дома, 7: Планета в знаке, 8: Дом

TYPE_ID_MAP = {
    1: ZodiacSignData,
    2: NakshatraData,
    3: PlanetData,
    4: KarakaData,
    5: ArudhaData,
    6: HouseData,
    7: PlanetInSignData,
    8: HouseTypeData,
}


class TypeFilteredAdmin(LocalizedModelAdmin):
    """Base admin that filters queryset by type_id."""
    type_id = None

    @staticmethod
    def description_html(obj):
        return mark_safe(get_default_language_value_admin(obj.description))

    def get_queryset(self, request):
        return super().get_queryset(request).filter(type_id=self.type_id)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.type_id = self.type_id
        super().save_model(request, obj, form, change)

    search_fields = ("internal_id", "name")
    localized_fields = ("name", "description")
    list_display = ("id", "is_public", "internal_id", "default_localized_name", "description_html")


@admin.register(ZodiacSignData)
class ZodiacSignDataAdmin(TypeFilteredAdmin):
    type_id = 1


@admin.register(NakshatraData)
class NakshatraDataAdmin(TypeFilteredAdmin):
    type_id = 2


@admin.register(PlanetData)
class PlanetDataAdmin(TypeFilteredAdmin):
    type_id = 3


@admin.register(KarakaData)
class KarakaDataAdmin(TypeFilteredAdmin):
    type_id = 4


@admin.register(ArudhaData)
class ArudhaDataAdmin(TypeFilteredAdmin):
    type_id = 5


@admin.register(HouseData)
class HouseDataAdmin(TypeFilteredAdmin):
    type_id = 6




@admin.register(AstroprocessorType)
class AstroprocessorTypeAdmin(LocalizedModelAdmin):
    tolgee_namespace = "astroprocessor_types"
    search_fields = ("id", "name")
    localized_fields = ("name", )
    list_display = ("default_localized_name", )


@admin.register(SignPlanetConnection)
class SignPlanetConnectionAdmin(LocalizedModelAdmin):
    tolgee_namespace = "sign_planet"

    @staticmethod
    def description_html(obj):
        return mark_safe(get_default_language_value_admin(obj.description))

    @staticmethod
    @admin.display(description="Планета")
    def planet_name(obj):
        return PLANET_NAMES.get(obj.planet, obj.planet)

    @staticmethod
    @admin.display(description="Знак")
    def sign_name(obj):
        return SIGN_NAMES.get(obj.sign, obj.sign)

    search_fields = ["planet", "sign"]
    localized_fields = ("name", "description")
    list_display = ["id", "default_localized_name", "planet_name", "sign_name", "description_html"]


@admin.register(PlanetHouseConnection)
class PlanetHouseConnectionAdmin(LocalizedModelAdmin):
    tolgee_namespace = "planet_house"

    @staticmethod
    def description_html(obj):
        return mark_safe(get_default_language_value_admin(obj.description))

    @staticmethod
    @admin.display(description="Планета")
    def planet_name(obj):
        return PLANET_NAMES.get(obj.planet, obj.planet)

    @staticmethod
    @admin.display(description="Дом")
    def house_name(obj):
        return f"Дом {obj.house}"

    search_fields = ["planet", "house"]
    localized_fields = ("name", "description")
    list_display = ["id", "default_localized_name", "planet_name", "house_name", "description_html"]


@admin.register(MasterHouseConnection)
class MasterHouseConnectionAdmin(LocalizedModelAdmin):
    tolgee_namespace = "master_house"

    @staticmethod
    def description_html(obj):
        return mark_safe(get_default_language_value_admin(obj.description))

    @staticmethod
    @admin.display(description="Управитель дома")
    def master_house_name(obj):
        return HOUSE_RULER_NAMES.get(obj.master_house, f"Дом {obj.master_house}")

    @staticmethod
    @admin.display(description="В доме")
    def at_house_name(obj):
        return f"Дом {obj.at_house}"

    search_fields = ["master_house", "at_house"]
    localized_fields = ("name", "description")
    list_display = ["id", "default_localized_name", "master_house_name", "at_house_name", "description_html"]
    list_filter = ["master_house", "at_house"]
