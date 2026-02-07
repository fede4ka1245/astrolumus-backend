import json

from django import forms
from django.conf import settings
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe


try:
    from ckeditor.widgets import CKEditorWidget
except Exception:  # pragma: no cover
    CKEditorWidget = None


def _normalize_language_code(code: str) -> str:
    return (code or "").lower().split("-")[0]


def _languages_for_tabs():
    # Пытаемся получить языки из модели AppLanguage (users > Языки приложения)
    try:
        from django.apps import apps

        model_path = getattr(settings, "APP_LANGUAGE_MODEL", None)
        if model_path:
            AppLanguage = apps.get_model(model_path)
            languages = list(AppLanguage.objects.values_list("code", "name"))
            if languages:
                return languages
    except Exception:
        pass

    # Fallback: settings.LANGUAGES
    languages = []
    seen = set()
    for code, label in getattr(settings, "LANGUAGES", []):
        norm = _normalize_language_code(code)
        if not norm or norm in seen:
            continue
        seen.add(norm)
        languages.append((norm, str(label)))
    if not languages:
        languages = [("ru", "Russian"), ("en", "English")]
    return languages


class MultilangJSONCKEditorWidget(forms.Widget):
    _INLINE_CSS = """
.mlj-widget .mlj-tabs{display:flex;gap:6px;margin:0 0 8px 0;flex-wrap:wrap}
.mlj-widget .mlj-tabs button{padding:4px 10px;border:1px solid var(--border-color,#d1d1d1);background:#f8f8f8;cursor:pointer;border-radius:999px}
.mlj-widget .mlj-tabs button.active{background:#e7f0ff;border-color:#79a6ff}
""".strip()

    _INLINE_JS = r"""
(function(){
  if (window.__mlj_inline_init__ === true) return;
  window.__mlj_inline_init__ = true;

  function parseLanguages(el){
    try { return JSON.parse(el.getAttribute("data-languages") || "[]"); } catch(e){ return []; }
  }
  function safeJsonParse(text){
    try {
      var obj = JSON.parse(text || "{}");
      return obj && typeof obj === "object" && !Array.isArray(obj) ? obj : {};
    } catch(e){ return {}; }
  }
  function setActiveTab(container, lang){
    var tabs = container.querySelectorAll(".mlj-tabs button");
    for (var i=0;i<tabs.length;i++){
      tabs[i].classList.toggle("active", tabs[i].getAttribute("data-lang") === lang);
    }
  }
  function waitForCkeditorInstance(editorId, cb){
    var attempts = 0;
    function tick(){
      attempts += 1;
      if (window.CKEDITOR && CKEDITOR.instances && CKEDITOR.instances[editorId]) { cb(CKEDITOR.instances[editorId]); return; }
      if (attempts > 200) { cb(null); return; }
      setTimeout(tick, 50);
    }
    tick();
  }
  function initWidget(container){
    if (container.getAttribute("data-mlj-initialized") === "1") return;
    container.setAttribute("data-mlj-initialized", "1");

    var hiddenId = container.getAttribute("data-hidden-id");
    var editorId = container.getAttribute("data-editor-id");
    var hidden = document.getElementById(hiddenId);
    var textarea = document.getElementById(editorId);
    if (!hidden || !textarea) return;

    var languages = parseLanguages(container);
    if (!languages.length) return;

    var state = safeJsonParse(hidden.value);
    for (var i=0;i<languages.length;i++){
      var code = languages[i].code;
      if (typeof state[code] !== "string") state[code] = "";
    }

    var activeLang = languages[0].code;
    setActiveTab(container, activeLang);

    function syncHidden(){ hidden.value = JSON.stringify(state); }
    function setEditorValue(value){ textarea.value = value; }
    function getEditorValue(){ return textarea.value || ""; }

    waitForCkeditorInstance(editorId, function(instance){
      if (instance){
        setEditorValue = function(value){ instance.setData(value || ""); };
        getEditorValue = function(){ return instance.getData() || ""; };
        instance.on("change", function(){ state[activeLang] = getEditorValue(); syncHidden(); });
      } else {
        textarea.addEventListener("input", function(){ state[activeLang] = getEditorValue(); syncHidden(); });
      }

      setEditorValue(state[activeLang] || "");
      syncHidden();

      var form = container.closest("form");
      if (form){
        form.addEventListener("submit", function(){ state[activeLang] = getEditorValue(); syncHidden(); }, {capture:true});
      }

      var tabs = container.querySelectorAll(".mlj-tabs button");
      for (var i=0;i<tabs.length;i++){
        tabs[i].addEventListener("click", function(e){
          var nextLang = e.currentTarget.getAttribute("data-lang");
          if (!nextLang || nextLang === activeLang) return;
          state[activeLang] = getEditorValue();
          activeLang = nextLang;
          setActiveTab(container, activeLang);
          setEditorValue(state[activeLang] || "");
          syncHidden();
        });
      }
    });
  }

  function initAll(){
    var widgets = document.querySelectorAll(".mlj-widget");
    for (var i=0;i<widgets.length;i++) initWidget(widgets[i]);
  }

  if (window.django && django.jQuery){
    django.jQuery(function(){
      initAll();
      django.jQuery(document).on("formset:added", function(){ initAll(); });
    });
  } else {
    document.addEventListener("DOMContentLoaded", initAll);
  }
})();
""".strip()

    def _inline_assets_html(self):
        return format_html(
            "<style>{}</style><script>{}</script>",
            mark_safe(self._INLINE_CSS),
            mark_safe(self._INLINE_JS),
        )

    def __init__(self, attrs=None, languages=None, ckeditor_config_name="default"):
        super().__init__(attrs)
        self.languages = languages or _languages_for_tabs()
        self.ckeditor_config_name = ckeditor_config_name

    @property
    def media(self):
        media = super().media
        if CKEditorWidget is not None:
            media = media + CKEditorWidget().media
        return media

    def format_value(self, value):
        if value in (None, "", b""):
            return "{}"
        if isinstance(value, dict):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return "{}"
            return value
        return json.dumps({}, ensure_ascii=False)

    def _parse_value(self, value):
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            try:
                loaded = json.loads(value) if value.strip() else {}
            except Exception:
                return {}
            return loaded if isinstance(loaded, dict) else {}
        return {}

    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs or {}
        hidden_id = attrs.get("id") or f"id_{name}"
        editor_id = f"{hidden_id}__ml_editor"
        editor_name = f"{name}__ml_editor"

        parsed = self._parse_value(value)
        languages = list(self.languages)
        active_lang = languages[0][0]
        editor_value = parsed.get(active_lang, "") if isinstance(parsed.get(active_lang, ""), str) else ""
        hidden_value = self.format_value(parsed)

        tabs_html = format_html(
            '<div class="mlj-tabs">{}</div>',
            format_html_join(
                "",
                '<button type="button" data-lang="{}">{}</button>',
                ((code, label) for code, label in languages),
            ),
        )
        inline_assets_html = self._inline_assets_html()
        if CKEditorWidget is not None:
            editor_widget = CKEditorWidget(config_name=self.ckeditor_config_name)
        else:  # pragma: no cover
            editor_widget = forms.Textarea()

        editor_html = editor_widget.render(
            editor_name,
            editor_value,
            attrs={
                "id": editor_id,
            },
            renderer=renderer,
        )

        languages_json = json.dumps(
            [{"code": code, "label": label} for code, label in languages],
            ensure_ascii=False,
        )

        return format_html(
            '<div class="mlj-widget" data-hidden-id="{}" data-editor-id="{}" data-languages="{}">'
            "{}"
            "{}"
            '<input type="hidden" name="{}" id="{}" value="{}" />'
            "{}"
            "</div>",
            hidden_id,
            editor_id,
            languages_json,
            tabs_html,
            inline_assets_html,
            name,
            hidden_id,
            hidden_value,
            editor_html,
        )
