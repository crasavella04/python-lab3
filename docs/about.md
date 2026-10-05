# О сайте

## Стек

| Компонент | Что используется |
|-----------|------------------|
| Генератор | MkDocs 1.6 + Material for MkDocs 9.7 |
| Python | 3.14, окружение `virtualenv` |
| Зависимости | `requirements.txt` с точными версиями |
| CI/CD | GitHub Actions |
| Хостинг | GitHub Pages, Helios ИТМО |

## Локальная сборка

```bash
python -m virtualenv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
mkdocs serve                     # предпросмотр на http://127.0.0.1:8000
mkdocs build --strict            # проверочная сборка в каталог site/
```

В режиме `--strict` любое предупреждение (битая ссылка, страница вне навигации, несуществующий
якорь) приводит к ошибке сборки. Поэтому сломанный сайт не попадёт в публикацию.

## Публикация на GitHub Pages: два подхода

=== "Push в ветку gh-pages"

    Workflow собирает сайт и коммитит содержимое `site/` в отдельную ветку `gh-pages`
    (экшен `peaceiris/actions-gh-pages` или команда `mkdocs gh-deploy`). Pages раздаёт файлы
    из этой ветки (Source = *Deploy from a branch*).

    - Нужно право `contents: write`: workflow пишет в репозиторий.
    - В истории репозитория копится сгенерированный HTML, по коммиту на каждый деплой.
    - Работает везде, где есть git. Ветку можно скачать и посмотреть, что именно опубликовано.
    - Тот же приём годится для любого хостинга, который раздаёт сайт из git-ветки.

=== "upload-pages-artifact + deploy-pages"

    Сайт упаковывается в артефакт сборки (`actions/upload-pages-artifact`), а
    `actions/deploy-pages` передаёт его напрямую в Pages (Source = *GitHub Actions*).

    - Репозиторий содержит только исходники, ветка с HTML не нужна.
    - Хватает права `contents: read`. Для деплоя нужны `pages: write` и `id-token: write`
      (OIDC-токен подтверждает, что деплой идёт из этого workflow).
    - Деплой привязан к окружению `github-pages`: в нём видна история деплоев и ссылка на сайт,
      можно настроить правила защиты.
    - Сборка и публикация разделены на два job'а. В pull request выполняется только сборка,
      то есть проверка `--strict`.

На этом сайте используется второй, официальный подход: см. `.github/workflows/pages.yml`.

## Формулы без внешних CDN

Формулы размечаются расширением `pymdownx.arithmatex` и рендерятся библиотекой KaTeX. Её скрипты,
стили и шрифты лежат в репозитории (`docs/assets/katex`), а шрифт темы не грузится с Google Fonts.
Поэтому формулы отображаются и там, где внешние CDN недоступны. Контрольный пример:

$$
\bar{x} = \frac{1}{n}\sum_{i=1}^{n} x_i, \qquad
s^2 = \frac{1}{n-1}\sum_{i=1}^{n} \left(x_i - \bar{x}\right)^2
$$

Строчная формула: $e^{i\pi} + 1 = 0$.
