#!/bin/sh
# P4: выкладка сайта python-lab3 на Helios — релизы, preview-ветки, откат.
#
#   deploy   <цель> <коммит>    архив сайта (tar.gz) — из stdin
#   rollback <цель> [<релиз>]   вернуть предыдущий релиз (или указанный)
#   rollback <цель> failed      то же после проваленного healthcheck: снятая версия сохраняется
#                               как <релиз>-failed (для разбора) и больше не выбирается для отката
#   remove   preview/<имя>      удалить preview ветки вместе с её релизами
#   list     [<цель>]           что сейчас опубликовано и какие релизы сохранены
#
# Цель: root — корень сайта (ветка main), preview/<имя> — подкаталог preview/<имя>/.
#
# Раскладка на сервере:
#   ~/public_html/python-lab3/                 рабочая версия main
#   ~/public_html/python-lab3/preview/<имя>/   рабочие версии веток
#   ~/.deploy/python-lab3/releases/<слот>/<релиз>/   предыдущие версии (KEEP на слот), вне веб-доступа
#   ~/.deploy/python-lab3/stage/<pid>/         приём архива
#
# Публикация — только переименованиями: архив сначала целиком распаковывается в stage,
# проверяется, и лишь затем каталоги меняются местами. Оборванная передача не трогает сайт.
# Скрипт работает и как forced command ключа деплоя (команда — из $SSH_ORIGINAL_COMMAND).
# Только POSIX sh и стандартные утилиты: на сервере нет ни rsync, ни Python-окружения.
set -eu
umask 022

SITE="$HOME/public_html/python-lab3"
BASE="$HOME/.deploy/python-lab3"
KEEP=3                # сколько предыдущих релизов хранить на каждый слот
MAX_KB=102400         # 100 МБ распакованного архива — защита квоты

log() { printf 'deploy: %s\n' "$*" >&2; }
die() { printf 'deploy: ОШИБКА: %s\n' "$*" >&2; exit 1; }

STAGE=""
LOCKED=0
cleanup() {
    if [ -n "$STAGE" ]; then rm -rf "$STAGE"; fi
    if [ "$LOCKED" = 1 ]; then rm -rf "$BASE/lock"; fi
}
on_signal() { log "прервано сигналом — рабочая версия не тронута"; exit 130; }
trap cleanup EXIT
trap on_signal HUP INT TERM PIPE

# --- цель → пути -------------------------------------------------------------
resolve() {
    case "$1" in
        root)
            LIVE=$SITE; SLOT=root ;;
        preview/*)
            name=${1#preview/}
            case "$name" in
                ''|-*|*[!a-z0-9-]*) die "недопустимое имя preview: '$name' (только a-z, 0-9, -)" ;;
            esac
            [ ${#name} -le 40 ] || die "имя preview длиннее 40 символов"
            LIVE=$SITE/preview/$name; SLOT=preview-$name ;;
        *) die "неизвестная цель '$1': root или preview/<имя>" ;;
    esac
    REL=$BASE/releases/$SLOT
}

release_of() {  # $1 — каталог версии; печатает id релиза из release.json
    sed -n 's/.*"release": *"\([^"]*\)".*/\1/p' "$1/release.json" 2>/dev/null | head -n 1
}

commit_of() {
    sed -n 's/.*"commit": *"\([^"]*\)".*/\1/p' "$1/release.json" 2>/dev/null | head -n 1
}

# --- блокировка: mkdir атомарен, flock есть не везде ---------------------------
lock() {
    mkdir -p "$BASE"
    n=0
    while ! mkdir "$BASE/lock" 2>/dev/null; do
        p=$(cat "$BASE/lock/pid" 2>/dev/null || true)
        if [ -n "$p" ] && ! kill -0 "$p" 2>/dev/null; then
            log "снимаю блокировку завершившегося процесса $p"
            rm -rf "$BASE/lock"
            continue
        fi
        n=$((n + 1))
        [ "$n" -lt 300 ] || die "другая выкладка держит блокировку дольше 5 минут"
        [ "$n" -gt 1 ] || log "жду завершения другой выкладки…"
        sleep 1
    done
    echo $$ > "$BASE/lock/pid"
    LOCKED=1
}

# Остатки выкладок, убитых без возможности прибраться (kill -9, перезагрузка сервера)
clean_stale_stage() {
    for d in "$BASE"/stage/*; do
        [ -d "$d" ] || continue
        p=${d##*/}
        [ "$p" = "$$" ] && continue
        case "$p" in *[!0-9]*) ;; *) if kill -0 "$p" 2>/dev/null; then continue; fi ;; esac
        log "удаляю остатки прерванной выкладки: stage/$p"
        rm -rf "$d"
    done
}

# --- переключение: $1 становится рабочей версией, прежняя уходит в releases ------
switch_to() {
    new=$1
    # Между двумя mv сайта нет — сигналы на это время игнорируем, чтобы не застрять посередине
    trap '' HUP INT TERM PIPE
    mkdir -p "$REL"
    if [ -d "$LIVE" ]; then
        old=$(release_of "$LIVE")
        [ -n "$old" ] || old="00000000T000000Z-legacy"  # версия до P4, без release.json
        old="$old${OUT_SUFFIX:-}"
        [ ! -e "$REL/$old" ] || old="$old-$$"
        # preview веток лежат внутри корня — переносим их в новую версию корня
        if [ "$SLOT" = root ] && [ -d "$LIVE/preview" ]; then
            mv "$LIVE/preview" "$new/preview"
        fi
        mv "$LIVE" "$REL/$old"
    fi
    mkdir -p "${LIVE%/*}"
    mv "$new" "$LIVE"
    trap on_signal HUP INT TERM PIPE
}

prune() {
    n=$(ls -1 "$REL" | wc -l | tr -d ' ')
    extra=$((n - KEEP))
    [ "$extra" -gt 0 ] || return 0
    ls -1 "$REL" | sort | head -n "$extra" | while read -r d; do
        log "удаляю старый релиз $SLOT/$d"
        rm -rf "${REL:?}/$d"
    done
}

# --- команды ----------------------------------------------------------------------
cmd_deploy() {
    [ $# -eq 2 ] || die "deploy <цель> <коммит>"
    resolve "$1"
    commit=$2
    case "$commit" in *[!0-9a-f]*) die "коммит — 40 шестнадцатеричных цифр" ;; esac
    [ ${#commit} -eq 40 ] || die "коммит — 40 шестнадцатеричных цифр"

    mkdir -p "$BASE/stage"
    STAGE=$BASE/stage/$$
    rm -rf "$STAGE"
    mkdir "$STAGE"
    # Распаковка во временный каталог: при обрыве tar завершится с ошибкой, сайт не тронут
    tar -xzf - -C "$STAGE" || die "архив принят не целиком (обрыв передачи?) — рабочая версия не тронута"

    if find "$STAGE" -type l | grep -q .; then die "в архиве есть символические ссылки"; fi
    kb=$(du -sk "$STAGE" | cut -f1)
    [ "$kb" -le "$MAX_KB" ] || die "архив больше лимита: $kb КБ"
    [ -f "$STAGE/index.html" ] || die "в архиве нет index.html"
    [ ! -e "$STAGE/preview" ] || die "в архиве есть каталог preview/ — он занят preview веток"

    id="$(date -u +%Y%m%dT%H%M%SZ)-$(printf '%s' "$commit" | cut -c1-7)"
    printf '{"release": "%s", "target": "%s", "commit": "%s", "deployed_at": "%s"}\n' \
        "$id" "$1" "$commit" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$STAGE/release.json"
    chmod -R a+rX "$STAGE"
    log "принято и распаковано $kb КБ"

    lock
    clean_stale_stage
    switch_to "$STAGE"
    STAGE=""
    prune
    log "опубликован релиз $id → $1"
    echo "release=$id commit=$commit"
}

cmd_rollback() {
    [ $# -ge 1 ] && [ $# -le 2 ] || die "rollback <цель> [<релиз> | failed]"
    resolve "$1"
    if [ "${2:-}" = failed ]; then
        OUT_SUFFIX=-failed
        set -- "$1"
    fi
    lock
    [ -d "$REL" ] || die "для $1 нет сохранённых релизов"
    current=$(release_of "$LIVE")
    if [ $# -eq 2 ]; then
        pick=$2
        case "$pick" in ''|*[!0-9A-Za-z-]*) die "недопустимое имя релиза: $pick" ;; esac
    else
        # Ближайший релиз старше текущего: повторный rollback уходит ещё на шаг назад.
        # Вернуться вперёд — rollback с явным именем релиза (см. list).
        [ -n "$current" ] || die "у рабочей версии нет release.json — укажите релиз явно (см. list)"
        # (без awk -v: на старых Unix его нет) — сортируем вместе с текущим, берём строку перед ним
        pick=$({ ls -1 "$REL"; echo "$current"; } | sort | while read -r r; do
                   [ "$r" = "$current" ] && break
                   case "$r" in *-failed*) ;; *) echo "$r" ;; esac
               done | tail -n 1)
    fi
    [ -n "$pick" ] && [ -d "$REL/$pick" ] || die "нет релиза для отката (текущий: ${current:-нет})"
    switch_to "$REL/$pick"
    log "откат $1: $current${OUT_SUFFIX:-} → $pick"
    echo "release=$pick commit=$(commit_of "$LIVE")"
}

cmd_remove() {
    [ $# -eq 1 ] || die "remove preview/<имя>"
    case "$1" in preview/*) ;; *) die "удалять можно только preview" ;; esac
    resolve "$1"
    lock
    rm -rf "$LIVE" "$REL"
    log "удалён $1"
}

cmd_list() {
    for t in ${1:-root $(ls -1 "$SITE/preview" 2>/dev/null | sed 's|^|preview/|')}; do
        resolve "$t"
        echo "$t: рабочая версия $(release_of "$LIVE" || true)"
        ls -1 "$REL" 2>/dev/null | sort -r | sed 's/^/    сохранён /'
    done
    for d in "$BASE"/stage/*; do
        [ -d "$d" ] && echo "незавершённая выкладка: stage/${d##*/}"
    done
    return 0
}

# --- разбор команды -----------------------------------------------------------------
# Forced command: sshd кладёт присланную клиентом строку в SSH_ORIGINAL_COMMAND.
# Слова до имени команды (например, «sh путь/к/скрипту») пропускаются.
if [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
    set -f
    # shellcheck disable=SC2086
    set -- $SSH_ORIGINAL_COMMAND
    set +f
fi
while [ $# -gt 0 ]; do
    case "$1" in deploy|rollback|remove|list) break ;; esac
    shift
done
[ $# -gt 0 ] || die "команда: deploy | rollback | remove | list"
cmd=$1
shift
"cmd_$cmd" "$@"
