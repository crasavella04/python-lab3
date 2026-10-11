// P5: русский поиск Sphinx — дополнение к стеммеру Snowball на стороне запроса.
//
// Индекс строится Snowball (html_search_language = "ru"), запрос стеммируется им же. Поиск
// находит термин индекса, совпадающий с основой запроса, или содержащий её (частичное
// совпадение). Не находит, когда основа запроса ДЛИННЕЕ основы в тексте: у глаголов Snowball
// оставляет суффиксы -ова-/-ыва-/-ива-, и «откатывать» → «откатыва» не входит в «откат»,
// «кэшировать» → «кэширова» не входит в «кэшир» (из «кэширует»).
//
// Здесь у основы запроса отрезается такой суффикс, если остаётся не меньше 4 букв:
// «откатыва» → «откат», «кэширова» → «кэшир». Индекс не меняется — только запрос.
(function () {
  "use strict";
  var SUFFIXES = ["ирова", "ова", "ева", "ыва", "ива"];
  var MIN_STEM = 4;

  function trim(stem) {
    for (var i = 0; i < SUFFIXES.length; i++) {
      var s = SUFFIXES[i];
      if (stem.length - s.length >= MIN_STEM && stem.slice(-s.length) === s) {
        return stem.slice(0, -s.length);
      }
    }
    return stem;
  }

  function wrap(Base) {
    if (!Base || Base.__p5) return Base;
    var Wrapped = function () {
      var base = new Base();
      this.stemWord = function (word) { return trim(base.stemWord(word)); };
    };
    Wrapped.__p5 = true;
    return Wrapped;
  }

  // language_data.js задаёт window.Stemmer, а searchtools.js вызывает new Stemmer() при поиске.
  // Порядок загрузки скриптов может быть любым — перехватываем присваивание.
  var current = wrap(window.Stemmer);
  Object.defineProperty(window, "Stemmer", {
    configurable: true,
    get: function () { return current; },
    set: function (v) { current = wrap(v); },
  });
  window.__searchRuTrim = trim;   // для проверки из research/p5
})();
