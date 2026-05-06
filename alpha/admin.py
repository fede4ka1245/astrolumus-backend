from ckeditor.widgets import CKEditorWidget
from django.contrib import admin
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse, HttpResponseBadRequest, HttpResponseRedirect
from django.template.response import TemplateResponse
from django.urls import path

from django import forms
from django.utils.html import strip_tags


class SendMailForm(forms.Form):
    title = forms.CharField(label="Заголовок", max_length=255)
    content = forms.CharField(widget=CKEditorWidget())
    user_email = forms.CharField(label="отправить на один email, если указано", required=False)


class AlphaAdminSite(admin.AdminSite):
    hidden_app_labels = {
        "complaints",
        "advertising",
        "astrology_calendar",
        "astrology_forum",
        "favorite",
        "stop_words",
    }

    # Merge these app_labels into a single admin section
    _merge_apps = {
        "tariffs": "payments",  # tariffs models appear under payments section
    }

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label=app_label)
        app_list = [
            app
            for app in app_list
            if app.get("app_label") not in self.hidden_app_labels
            and app.get("app_label") not in {"voting"}
        ]

        # Merge apps: move models from source into target section
        targets = {}
        sources_to_remove = set()
        for app in app_list:
            label = app.get("app_label")
            if label in self._merge_apps.values():
                targets[label] = app
        for app in app_list:
            label = app.get("app_label")
            target_label = self._merge_apps.get(label)
            if target_label and target_label in targets:
                targets[target_label]["models"].extend(app.get("models", []))
                sources_to_remove.add(label)
        app_list = [app for app in app_list if app.get("app_label") not in sources_to_remove]

        # Reorder models within analytics: P&L models first, then users/payments
        analytics_model_order = [
            "Expense", "ExpenseCategory", "CurrencyRate",
            "AnalyticsPayment", "AnalyticsUser",
        ]
        for app in app_list:
            if app.get("app_label") == "analytics":
                app["models"].sort(
                    key=lambda m: (
                        analytics_model_order.index(m["object_name"])
                        if m["object_name"] in analytics_model_order
                        else len(analytics_model_order)
                    )
                )

        top = ["analytics", "payments"]
        bottom = ["fcm_django", "django_celery_beat"]

        def sort_key(app):
            label = app.get("app_label")
            if label in top:
                return (0, top.index(label))
            if label in bottom:
                return (2, bottom.index(label))
            return (1, app.get("name", ""))

        app_list.sort(key=sort_key)

        # Inject P&L Dashboard link and hide MetabaseDashboard from sidebar
        for app in app_list:
            if app.get("app_label") == "analytics":
                app["models"] = [
                    m for m in app["models"]
                    if m.get("object_name") != "MetabaseDashboard"
                ]
                app["models"].insert(0, {
                    "name": "P&L Dashboard",
                    "object_name": "_pnl_dashboard",
                    "admin_url": "/admin/analytics/",
                    "view_only": True,
                })
                break

        return app_list

    def get_urls(self):
        from django.urls import include

        urls = super().get_urls()
        my_urls = [
            path('send-email-users/', self.admin_view(self.send_emails), name="send_email_users"),
            path('set-language/', self.admin_view(self.set_language), name="set_language"),
            path('analytics/', include("analytics.urls")),
        ]

        return my_urls + urls

    def set_language(self, request):
        if request.method != "POST":
            return HttpResponseBadRequest("POST only")

        language = request.POST.get("language", "").strip()
        if not language:
            return HttpResponseBadRequest("Missing language")

        from django.utils import translation

        # Сохраняем язык пользователя в БД
        if request.user.is_authenticated:
            request.user.language = language
            request.user.save(update_fields=["language"])

        # Активируем locale для текущего запроса
        translation.activate(language)
        request.session[translation.LANGUAGE_SESSION_KEY] = language

        next_url = request.POST.get("next", "/admin/")
        return HttpResponseRedirect(next_url)

    def send_emails(self, request):
        context = dict(
            # Include common variables for rendering the admin template.
            self.each_context(request),
            # Anything else you want in the context...
            # key=value,
        )

        if request.method == "POST":
            # create a form instance and populate it with data from the request:
            form = SendMailForm(request.POST)
            # check whether it's valid:
            if form.is_valid():
                # send mails
                if form.data["user_email"]:
                    subject, from_email, to = form.data["title"], 'alphaspace@alpha-astro.com', form.data["user_email"]
                    text_content = strip_tags(form.data["content"])
                    html_content = form.data["content"]
                    msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
                else:
                    pass

                return HttpResponseRedirect("/admin/")

        # if a GET (or any other method) we'll create a blank form
        else:
            form = SendMailForm()

        context["form"] = form

        return TemplateResponse(request, "users/admin_send_emails.html", context)
