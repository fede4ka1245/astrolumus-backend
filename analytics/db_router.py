"""
Route AnalyticsUser and AnalyticsPayment to the 'analytics' database.
All other models use 'default'.
"""

ANALYTICS_MODELS = {"analyticsuser", "analyticspayment"}


class AnalyticsRouter:
    def db_for_read(self, model, **hints):
        if model._meta.model_name in ANALYTICS_MODELS:
            return "analytics"
        return None

    def db_for_write(self, model, **hints):
        if model._meta.model_name in ANALYTICS_MODELS:
            return "analytics"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        if model_name in ANALYTICS_MODELS:
            return False
        if db == "analytics":
            return False
        return None
