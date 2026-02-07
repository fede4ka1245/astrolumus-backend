from ckeditor.widgets import CKEditorWidget
from django.contrib import admin
from django.core.mail import EmailMultiAlternatives
from django.http import HttpResponse, HttpResponseRedirect
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

    def get_app_list(self, request, app_label=None):
        app_list = super().get_app_list(request, app_label=app_label)
        app_list = [
            app
            for app in app_list
            if app.get("app_label") not in self.hidden_app_labels
            and app.get("app_label") not in {"voting"}
        ]

        top = ["payments", "tariffs"]
        bottom = ["fcm_django", "django_celery_beat"]

        def sort_key(app):
            label = app.get("app_label")
            if label in top:
                return (0, top.index(label))
            if label in bottom:
                return (2, bottom.index(label))
            return (1, app.get("name", ""))

        app_list.sort(key=sort_key)
        return app_list

    def get_urls(self):
        urls = super().get_urls()
        my_urls = [
            path('send-email-users/', self.admin_view(self.send_emails), name="send_email_users"),
        ]

        return my_urls + urls

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
