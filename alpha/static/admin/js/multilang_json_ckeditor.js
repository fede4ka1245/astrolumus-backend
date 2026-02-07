(function () {
  function parseLanguages(el) {
    try {
      return JSON.parse(el.getAttribute("data-languages") || "[]");
    } catch (e) {
      return [];
    }
  }

  function safeJsonParse(text) {
    try {
      var obj = JSON.parse(text || "{}");
      return obj && typeof obj === "object" && !Array.isArray(obj) ? obj : {};
    } catch (e) {
      return {};
    }
  }

  function setActiveTab(container, lang) {
    var tabs = container.querySelectorAll(".mlj-tabs button");
    for (var i = 0; i < tabs.length; i++) {
      tabs[i].classList.toggle("active", tabs[i].getAttribute("data-lang") === lang);
    }
  }

  function ensureTabs(container, languages) {
    var existing = container.querySelector(".mlj-tabs");
    if (existing) return existing;

    var tabs = document.createElement("div");
    tabs.className = "mlj-tabs";
    for (var i = 0; i < languages.length; i++) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.setAttribute("data-lang", languages[i].code);
      btn.textContent = languages[i].label || languages[i].code;
      tabs.appendChild(btn);
    }
    container.insertBefore(tabs, container.firstChild);
    return tabs;
  }

  function waitForCkeditorInstance(editorId, cb) {
    var attempts = 0;
    function tick() {
      attempts += 1;
      if (window.CKEDITOR && CKEDITOR.instances && CKEDITOR.instances[editorId]) {
        cb(CKEDITOR.instances[editorId]);
        return;
      }
      if (attempts > 200) {
        cb(null);
        return;
      }
      setTimeout(tick, 50);
    }
    tick();
  }

  function initWidget(container) {
    if (container.getAttribute("data-mlj-initialized") === "1") return;
    container.setAttribute("data-mlj-initialized", "1");

    var hiddenId = container.getAttribute("data-hidden-id");
    var editorId = container.getAttribute("data-editor-id");
    var hidden = document.getElementById(hiddenId);
    var textarea = document.getElementById(editorId);
    if (!hidden || !textarea) return;

    var languages = parseLanguages(container);
    if (!languages.length) return;
    ensureTabs(container, languages);

    var state = safeJsonParse(hidden.value);
    for (var i = 0; i < languages.length; i++) {
      var code = languages[i].code;
      if (typeof state[code] !== "string") state[code] = "";
    }

    var activeLang = languages[0].code;
    setActiveTab(container, activeLang);

    function syncHidden() {
      hidden.value = JSON.stringify(state);
    }

    function setEditorValue(value) {
      textarea.value = value;
    }

    function getEditorValue() {
      return textarea.value || "";
    }

    waitForCkeditorInstance(editorId, function (instance) {
      if (instance) {
        setEditorValue = function (value) {
          instance.setData(value || "");
        };
        getEditorValue = function () {
          return instance.getData() || "";
        };
        instance.on("change", function () {
          state[activeLang] = getEditorValue();
          syncHidden();
        });
      } else {
        textarea.addEventListener("input", function () {
          state[activeLang] = getEditorValue();
          syncHidden();
        });
      }

      setEditorValue(state[activeLang] || "");
      syncHidden();

      var form = container.closest("form");
      if (form) {
        form.addEventListener(
          "submit",
          function () {
            state[activeLang] = getEditorValue();
            syncHidden();
          },
          { capture: true }
        );
      }

      var tabs = container.querySelectorAll(".mlj-tabs button");
      for (var i = 0; i < tabs.length; i++) {
        tabs[i].addEventListener("click", function (e) {
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

  function initAll() {
    var widgets = document.querySelectorAll(".mlj-widget");
    for (var i = 0; i < widgets.length; i++) initWidget(widgets[i]);
  }

  if (window.django && django.jQuery) {
    django.jQuery(function () {
      initAll();
      django.jQuery(document).on("formset:added", function () {
        initAll();
      });
    });
  } else {
    document.addEventListener("DOMContentLoaded", initAll);
  }
})();
