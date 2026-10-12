# Upload to Helios ITMO

[![Test](https://github.com/crasavella04/helios-upload-action/actions/workflows/test.yml/badge.svg)](https://github.com/crasavella04/helios-upload-action/actions/workflows/test.yml)

GitHub Action that uploads a directory to **Helios ITMO** (`helios.cs.ifmo.ru:2222`) — or any other
SSH host — and returns the public URL. Built for publishing static sites and files to
`https://se.ifmo.ru/~<login>/` from CI.

- **SSH key, not password.** A dedicated deploy key from a secret; written to a temp file and removed.
- **Strict host key checking.** Helios host keys are bundled; no `ssh-keyscan` trust-on-first-use.
- **rsync or tar.** rsync when it is available on both sides, otherwise `tar` over `ssh`
  (Helios already has rsync; tar is the fallback for servers without it).
- **`delete`** like `rsync --delete`. With tar it unpacks next to the destination and swaps
  directories, so an interrupted upload never leaves a half-deleted site.
- **Safe paths.** Destination is relative to the home directory; `..`, absolute paths and shell
  metacharacters are rejected; `delete` on the whole `public_html` is refused.

*Русская версия — [ниже](#по-русски).*

## Usage

```yaml
- uses: crasavella04/helios-upload-action@v1
  with:
    username: s123456
    key: ${{ secrets.HELIOS_SSH_KEY }}
    source: site                     # local directory
    destination: public_html/my-site # relative to the home directory
    delete: true                     # remove files that are not in `source`
```

Full example — build a site and publish it:

```yaml
name: Publish
on:
  push:
    branches: [main]
jobs:
  helios:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v5
      - run: mkdir -p site && echo '<h1>Hello, Helios</h1>' > site/index.html
      - id: upload
        uses: crasavella04/helios-upload-action@v1
        with:
          username: ${{ vars.HELIOS_USER }}
          key: ${{ secrets.HELIOS_SSH_KEY }}
          source: site
          destination: public_html/hello
          delete: true
      - run: curl --fail --silent "${{ steps.upload.outputs.url }}" | grep -q 'Hello, Helios'
```

Pin a full release (`@v1.0.0`) or its commit SHA if you need an immutable reference; `@v1`
follows the latest `v1.x.y` release.

### Deploy key

1. `ssh-keygen -t ed25519 -N '' -f helios_deploy -C github-actions`
2. On Helios append `helios_deploy.pub` to `~/.ssh/authorized_keys`.
   Optionally restrict it: `restrict,command="…"` (see [forced commands](https://man.openbsd.org/sshd.8#command=_command_)).
3. In the repository: *Settings → Secrets and variables → Actions* → secret `HELIOS_SSH_KEY`
   with the contents of `helios_deploy`.

## Inputs

| Input | Required | Default | Description |
|---|---|---|---|
| `host` | no | `helios.cs.ifmo.ru` | SSH host |
| `port` | no | `2222` | SSH port |
| `username` | **yes** | | login on the server |
| `key` | **yes** | | private SSH key (OpenSSH format), from a secret |
| `source` | no | `.` | local directory; its *contents* are uploaded |
| `destination` | **yes** | | target directory relative to home, e.g. `public_html/site` |
| `delete` | no | `false` | remove files in `destination` absent from `source` |
| `method` | no | `auto` | `auto`, `rsync` or `tar` |
| `known-hosts` | no | bundled Helios keys | `known_hosts` lines; required for any host other than `helios.cs.ifmo.ru:2222` |
| `make-readable` | no | `true` | `chmod -R a+rX` on `destination` so the web server can read files |

## Outputs

| Output | Description |
|---|---|
| `method` | `rsync` or `tar` — what was actually used |
| `files` | number of files uploaded |
| `bytes` | total size in bytes |
| `duration-ms` | transfer time |
| `url` | `https://se.ifmo.ru/~<username>/<path>/` when `destination` is inside `public_html` on Helios, otherwise empty |

## Compatibility

| Runner | Status |
|---|---|
| `ubuntu-24.04`, `ubuntu-22.04` (GitHub-hosted) | ✅ tested in CI on every push ([`test.yml`](.github/workflows/test.yml)) |
| Helios ITMO (FreeBSD; `rsync` is installed, so `auto` picks it) | ✅ used in production by [python-lab3](https://github.com/crasavella04/python-lab3): 10 files in 7.7 s |
| `macos-*` | ⚠️ should work (bash 3.2-compatible, `ssh`, `rsync`, `tar` present) — not tested in CI |
| `windows-*` | ❌ not supported |
| self-hosted Linux | needs `bash`, `ssh`, `tar`; `rsync` optional |

Server side: any POSIX shell with `tar`, `mkdir`, `mv`, `chmod`; `rsync` optional.

## Versioning

Releases follow [Semantic Versioning](https://semver.org/): `v1.0.0`, `v1.1.0`, … The major tag
`v1` is moved to every new `v1.x.y` release automatically
([`major-tag.yml`](.github/workflows/major-tag.yml)). Breaking changes go to `v2`.

## Used by

- [crasavella04/python-lab3](https://github.com/crasavella04/python-lab3) — research site; datasets
  are published to Helios with this action
  ([workflow](https://github.com/crasavella04/python-lab3/blob/main/.github/workflows/pages.yml)).

## License

[MIT](LICENSE)

---

## По-русски

Action для GitHub Actions: загружает каталог на **Helios ИТМО** (`helios.cs.ifmo.ru:2222`) или на
любой SSH-хост и возвращает публичный адрес `https://se.ifmo.ru/~<логин>/…`.

- Вход **по ключу деплоя** из секрета, не по паролю. Ключ лежит во временном файле и удаляется
  после загрузки.
- **Строгая проверка ключа хоста**: ключи Helios встроены в action, `ssh-keyscan` «на доверии» не
  нужен.
- **rsync** там, где он есть с обеих сторон (на Helios есть), иначе **tar через ssh**: на сервере ничего ставить не
  надо.
- **`delete: true`** удаляет на сервере файлы, которых нет в `source`. В режиме tar новая версия
  распаковывается рядом, и каталоги меняются местами, поэтому оборванная загрузка не оставит
  полуудалённый сайт.
- **Безопасные пути**: `destination` — относительно домашнего каталога. `..`, абсолютные пути и
  спецсимволы оболочки отклоняются, `delete` для всего `public_html` запрещён.

Пример — в разделе [Usage](#usage). Параметры — таблица [Inputs](#inputs), выходы —
[Outputs](#outputs).

**Совместимость:** раннеры Ubuntu 22.04 и 24.04 проверяются в CI при каждом коммите. Helios
(FreeBSD) — в реальной работе в [python-lab3](https://github.com/crasavella04/python-lab3). macOS
должна работать, но в CI не проверяется. Windows не поддерживается.

**Версии**: семантические теги `v1.0.0`, …; мажорный тег `v1` переносится на каждый новый
выпуск `v1.x.y` автоматически.

**Ключ деплоя:** `ssh-keygen -t ed25519 -N '' -f helios_deploy`. Публичную часть добавьте на Helios
в `~/.ssh/authorized_keys`, приватную — в секрет репозитория `HELIOS_SSH_KEY`.
