---
title: "Челлендж. Action для выкладки на Helios ИТМО"
description: Собственный GitHub Action «Upload to Helios ITMO» — composite action для загрузки каталога на Helios по SSH (rsync или tar, строгая проверка ключа хоста, delete), тесты на одноразовом sshd, семантические версии с подвижным v1 и использование в этом репозитории.
date: 2026-10-12
---

# Челлендж. Action для выкладки на Helios ИТМО

**Upload to Helios ITMO** — composite action, который загружает каталог на Helios
(`helios.cs.ifmo.ru:2222`) или на любой другой SSH-хост и возвращает публичный адрес
`https://se.ifmo.ru/~<логин>/…`.

Репозиторий: **<https://github.com/crasavella04/helios-upload-action>** (выпуск `v1.0.0`, подвижный тег `v1`). Разрабатывался action в
каталоге `actions/helios-upload` этого репозитория и был вынесен в отдельный командой
`git subtree split`, вместе с историей коммитов. После этого копия отсюда удалена, а python-lab3
подключает опубликованный action.

## Что умеет

```yaml
- uses: crasavella04/helios-upload-action@v1
  with:
    username: s123456
    key: ${{ secrets.HELIOS_SSH_KEY }}
    source: site
    destination: public_html/my-site
    delete: true
```

| Требование | Как сделано |
|---|---|
| composite или Docker | composite: один шаг `bash upload.sh`, без контейнера, поэтому запускается за доли секунды |
| `action.yml` | 10 входов, 5 выходов (`method`, `files`, `bytes`, `duration-ms`, `url`), описание, `branding: upload-cloud / blue` |
| хост | `host`, `port` (по умолчанию Helios: `helios.cs.ifmo.ru`, `2222`) |
| путь назначения | `destination` — относительно домашнего каталога |
| исходный каталог | `source` |
| ключ | `key` — приватный ключ деплоя из секрета; `known-hosts` — ключи хоста (для Helios встроены) |
| флаг `--delete` | `delete: true`: у rsync это `--delete`, у tar — распаковка рядом и смена каталогов |

Почему composite, а не Docker. Docker-action при каждом запуске собирает или скачивает образ, это
десятки секунд, и работает он только на Linux-раннерах. Всё, что нужно действию (`bash`, `ssh`,
`rsync`, `tar`), на раннерах GitHub уже есть.

### Безопасность

- **Входы — только через переменные окружения.** `${{ inputs.destination }}`, подставленный прямо
  в текст скрипта, позволил бы выполнить команду через значение параметра.
- **Пути.** `destination` проверяется: только относительный путь, без `..` и спецсимволов оболочки.
  Поэтому он безопасно встаёт в одинарные кавычки удалённой команды. `delete: true` для всего
  `public_html` запрещён: он стёр бы все остальные сайты пользователя.
- **Ключ хоста проверяется строго** (`StrictHostKeyChecking=yes`). Ключи Helios встроены в action.
  Для другого хоста без `known-hosts` action откажется работать, а не поверит первому ответившему
  серверу.
- **Ключ деплоя** пишется во временный файл с правами 600 и удаляется по выходу.

### Выбор способа передачи

`method: auto` проверяет `rsync` на раннере и на сервере (`ssh … command -v rsync`). Если он есть
с обеих сторон, используется rsync, иначе `tar | ssh tar`. На Helios rsync есть, и первая же
реальная выкладка выбрала его. Режим tar нужен для серверов без rsync. С `delete` он не стирает
каталог перед загрузкой, а распаковывает новую версию рядом и меняет каталоги местами, как P4:
оборванная загрузка не оставит полупустой сайт.

## Тесты

Проверять action на настоящем Helios при каждом изменении неудобно, да и секреты в чужих pull
request недоступны. Поэтому тесты поднимают **одноразовый `sshd` на 127.0.0.1:2222** с
только что созданными ключами
([`tests/sshd.sh`](https://github.com/crasavella04/helios-upload-action/blob/main/tests/sshd.sh)),
а [`tests/e2e.sh`](https://github.com/crasavella04/helios-upload-action/blob/main/tests/e2e.sh)
проверяет 18 случаев:

- rsync и tar: файлы на месте, верные выходы, права 644;
- `delete: false` оставляет лишние файлы, `delete: true` их удаляет, временных каталогов не остаётся;
- `auto` выбирает rsync;
- отказ на `../etc`, `/tmp/x`, `a/../../b`, `x;rm -rf ~`, пустом пути и `.`;
- отказ `delete` для `public_html`;
- отказ при неверном ключе хоста и при чужом хосте без `known-hosts`.

Тесты проходят в контейнере Ubuntu 24.04 (`docker run … bash tests/e2e.sh`) и в
[CI action](https://github.com/crasavella04/helios-upload-action/actions/workflows/test.yml) — на Ubuntu 24.04 и 22.04. Первый запуск в
отдельном репозитории полностью зелёный: e2e на обеих версиях, `uses: ./` и `shellcheck`. Отдельный job вызывает action как `uses: ./`, то есть проверяет сам
`action.yml`: разводку входов, выходы, падение на опасном пути. Ещё один job — `shellcheck`.

**Что этот job поймал бы.** Первая выкладка из этого репозитория упала ещё до запуска скрипта:

```text
Failed to load …/actions/helios-upload/action.yml
(Line: 24, Col: 18): Unrecognized named-value: 'secrets'. Located at position 1 within expression: secrets.HELIOS_SSH_KEY
```

В **описании** входа `key` был пример `key: ${{ secrets.HELIOS_SSH_KEY }}`. GitHub вычисляет
выражения `${{ }}` даже в описаниях `action.yml`, а контекста `secrets` у action нет. `e2e.sh`
этого не видел, потому что вызывает `upload.sh` напрямую, минуя `action.yml`.

## Версии

Семантические теги: `v1.0.0`, `v1.0.1`, `v1.1.0`… Мажорный тег `v1` подвижный и указывает на
последний выпуск `v1.x.y`. Workflow
[`major-tag.yml`](https://github.com/crasavella04/helios-upload-action/blob/main/.github/workflows/major-tag.yml)
переносит его автоматически при публикации каждого выпуска (`git tag -f v1 && git push -f`).
Пользователь, указавший `@v1`, получает исправления без правки своего workflow. Если нужна
неизменная ссылка, указывают `@v1.0.0` или SHA коммита (T4).

## Где используется

В этом репозитории, job `publish-data` в
[`pages.yml`](https://github.com/crasavella04/python-lab3/blob/main/.github/workflows/pages.yml):

```yaml
- uses: crasavella04/helios-upload-action@0b9ce27cd15b7f702f756d915cd7b10b38242688 # v1.0.0
```

Сам action закреплён по SHA, как и остальные action проекта (T4). Тег `v1` нужен тем, кто
хочет получать исправления автоматически.
Наборы данных T2 и P3 с паспортами, итоговая таблица T2, `CITATION.cff` и `SHA256SUMS` публикуются
на Helios отдельно от сайта:
**<https://se.ifmo.ru/~s564180/python-lab3-data/>**. После загрузки job скачивает каждый файл по
адресу из выхода `url` и проверяет `sha256sum -c SHA256SUMS`.

Первая реальная выкладка: 10 файлов за 7,7 с, способ — rsync, все суммы сошлись.

## Публикация в Marketplace

Требования GitHub к публикации:
- публичный репозиторий с одним `action.yml` в корне;
- уникальное имя: «Upload to Helios ITMO» в Marketplace свободно, рядом есть только
  «Deploy to Helios (password)», который входит по паролю;
- принятое соглашение разработчика Marketplace и двухфакторная аутентификация владельца аккаунта.

Публикация делается из веб-интерфейса: *Draft a release* → *Publish this Action to the GitHub
Marketplace* → категория → тег `v1.0.0`. Модерации нет. Два последних шага может сделать только
владелец аккаунта.

**Статус.** Репозиторий, тег `v1.0.0` и подвижный `v1` опубликованы, CI зелёный. Выпуск в
Marketplace ожидает подтверждения владельцем аккаунта.

