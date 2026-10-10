# О сайте

## Стек

| Компонент | Что используется |
|-----------|------------------|
| Генератор | Sphinx 9.1 + MyST-Parser 5.1, тема Furo (до P1 — MkDocs 1.6 + Material 9.7) |
| Python | 3.14, окружение `virtualenv` |
| Зависимости | `requirements.txt` с точными версиями и SHA-256 хешами (`--require-hashes`) |
| CI/CD | GitHub Actions; GitVerse (P1) |
| Хостинг | GitHub Pages, Helios ИТМО |

## Локальная сборка

```bash
python -m virtualenv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install --require-hashes -r requirements.txt
sphinx-build -W --keep-going -b dirhtml docs site    # проверочная сборка в каталог site/
python -m http.server -d site 8000                   # предпросмотр на http://127.0.0.1:8000
```

Ключ `-W` превращает любое предупреждение в ошибку: битую ссылку, ссылку на несуществующий
якорь, страницу вне оглавления. Это аналог `mkdocs build --strict`, поэтому сломанный сайт не
попадёт в публикацию. `--keep-going` выводит все предупреждения сразу, а не только первое.
Сборщик `dirhtml` даёт адреса вида `/t1/`, такие же, как были у MkDocs.

## Публикация на GitHub Pages: два подхода

::::{tab-set}
:::{tab-item} Push в ветку gh-pages
Workflow собирает сайт и коммитит содержимое `site/` в отдельную ветку `gh-pages`
(экшен `peaceiris/actions-gh-pages`, у MkDocs — команда `mkdocs gh-deploy`). Pages раздаёт файлы
из этой ветки (Source = *Deploy from a branch*).

- Нужно право `contents: write`: workflow пишет в репозиторий.
- В истории репозитория копится сгенерированный HTML, по коммиту на каждый деплой.
- Работает везде, где есть git. Ветку можно скачать и посмотреть, что именно опубликовано.
- Тот же приём годится для любого хостинга, который раздаёт сайт из git-ветки.
:::
:::{tab-item} upload-pages-artifact + deploy-pages
Сайт упаковывается в артефакт сборки (`actions/upload-pages-artifact`), а
`actions/deploy-pages` передаёт его напрямую в Pages (Source = *GitHub Actions*).

- Репозиторий содержит только исходники, ветка с HTML не нужна.
- Хватает права `contents: read`. Для деплоя нужны `pages: write` и `id-token: write`
  (OIDC-токен подтверждает, что деплой идёт из этого workflow).
- Деплой привязан к окружению `github-pages`: в нём видна история деплоев и ссылка на сайт,
  можно настроить правила защиты.
- Сборка и публикация разделены на два job'а. В pull request выполняется только сборка,
  то есть строгая проверка.
:::
::::

На этом сайте используется второй, официальный подход: см. `.github/workflows/pages.yml`.

## Формулы без внешних CDN

Формулы записываются в MyST как `$…$` и `$$…$$`, Sphinx размечает их штатным кодом
`sphinx.ext.mathjax`, а рендерит библиотека KaTeX. Её скрипты, стили и шрифты лежат в репозитории
(`docs/_static/katex`), а тема Furo использует системные шрифты. Поэтому формулы отображаются и
там, где внешние CDN недоступны (подробно — в T4). Контрольный пример:

$$
\bar{x} = \frac{1}{n}\sum_{i=1}^{n} x_i, \qquad
s^2 = \frac{1}{n-1}\sum_{i=1}^{n} \left(x_i - \bar{x}\right)^2
$$

Строчная формула: $e^{i\pi} + 1 = 0$.
