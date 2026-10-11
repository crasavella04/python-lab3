// P5: переключатель версий сайта и предупреждение на старых версиях.
// Раскладка: корень сайта — main; vX.Y/ — версии по тегам; latest/ — копия новейшей версии.
// versions.json в корне: {"latest": "v1.1", "versions": [{"name", "path", "title", ...}]}
(function () {
  "use strict";

  function init() {
    var box = document.querySelector(".version-switcher");
    if (!box) return;
    var select = box.querySelector("select");
    // Корень этой сборки (для main — корень сайта, для версии — каталог vX.Y/ или latest/)
    var buildRoot = new URL(box.dataset.root, window.location.href);
    var ownName = box.dataset.version;
    // Версии лежат на один уровень ниже корня сайта
    var siteRoot = ownName ? new URL("../", buildRoot) : buildRoot;
    // Путь текущей страницы внутри сборки — чтобы открыть ту же страницу в другой версии
    var pagePath = window.location.href.slice(buildRoot.href.length).split("#")[0];
    // Где мы на самом деле: в latest/ лежит копия версии, но адрес у неё свой
    var here = buildRoot.href.slice(siteRoot.href.length).replace(/\/$/, "");
    var current = ownName ? here : "";

    fetch(new URL("versions.json", siteRoot), { cache: "no-cache" })
      .then(function (r) { if (!r.ok) throw new Error(r.status); return r.json(); })
      .then(function (data) {
        select.innerHTML = "";
        data.versions.forEach(function (v) {
          var opt = document.createElement("option");
          opt.value = v.path;
          opt.textContent = v.title;
          if (v.name === current) opt.selected = true;
          select.appendChild(opt);
        });
        select.disabled = false;
        select.addEventListener("change", function () {
          var base = new URL(select.value, siteRoot);
          var target = new URL(pagePath, base);
          // Страницы может не быть в другой версии — тогда открываем её главную
          fetch(target, { method: "HEAD" })
            .then(function (r) { window.location.href = r.ok ? target.href : base.href; })
            .catch(function () { window.location.href = base.href; });
        });
        if (ownName && ownName !== data.latest) warnOld(ownName, current, data, siteRoot, pagePath);
      })
      .catch(function () {
        // Без versions.json (локальный просмотр через file://) переключатель просто неактивен
      });
  }

  function warnOld(ownName, current, data, siteRoot, pagePath) {
    var latest = new URL("latest/", siteRoot);
    var note = document.createElement("div");
    note.className = "version-warning";
    note.setAttribute("role", "note");
    note.innerHTML = "Это версия <strong>" + ownName + "</strong> — результаты на момент её выпуска. " +
      'Последняя версия — <a href="' + new URL(pagePath, latest).href + '">' + data.latest + "</a>.";
    var article = document.querySelector("article");
    if (article) article.insertBefore(note, article.firstChild);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
