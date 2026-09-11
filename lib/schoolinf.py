# -*- coding: utf-8 -*-
"""schoolinf — автопроверка домашних заданий для учебника «Информатика 7–11».

Модуль подключается в начале каждого урока одной ячейкой и умеет:

* опознать ученика — по подтверждённому Google-аккаунту (OAuth) плюс ФИО и класс;
* проверить решение на наборе тестов и объяснить, что именно не сошлось;
* отправить результат в журнал учителя (Google-таблица через Apps Script);
* выдать «квитанцию», если журнал не настроен или сеть недоступна.

Типовое использование в ноутбуке ученика:

    import schoolinf as si
    si.start(lesson="07-05", name=ФИО, klass=Класс)

    def площадь(a, b):
        return a * b

    si.check("1", площадь, [
        ((3, 4), 12),
        ((1, 1), 1),
    ])

    si.report()

Честное ограничение: код выполняется на стороне ученика, поэтому вердикт
можно подделать. Поэтому в журнал вместе с вердиктом уходит исходный текст
решения — учитель видит, что было написано на самом деле.
"""

from __future__ import annotations

import base64
import hashlib
import inspect
import json
import sys
import time
import traceback
import urllib.error
import urllib.request
import zlib

__version__ = "1.0.0"

# ── Адрес журнала ─────────────────────────────────────────────────────────
# Пустой по умолчанию: адрес не хранится в открытом коде, его сообщает
# учитель, а ученик вписывает в поле «Журнал» или хранит в секрете Colab.
# Без адреса всё работает, только результат печатается квитанцией.
APPS_SCRIPT_URL = ""
COURSE = "Информатика 5–11"

_UNSET = ""

_ПРЕФИКС = "https://script.google.com/macros/s/"
_СУФФИКС = "/exec"


def адрес_журнала(значение):
    """Привести введённое к полному адресу веб-приложения.

    Учителю неудобно диктовать длинную ссылку целиком, поэтому принимаем
    и её, и один только идентификатор вида AKfycb…
    """
    значение = (значение or "").strip()
    if not значение:
        return ""
    if значение.startswith("http"):
        return значение
    return _ПРЕФИКС + значение + _СУФФИКС

# ── Сохранённые настройки ─────────────────────────────────────────────────
# ФИО, класс и адрес журнала одни и те же весь год, а урок каждый раз —
# новый файл. Чтобы не перепечатывать их еженедельно, настройки можно
# сохранить один раз: в «Секретах» Colab либо файлом на Google Диске.
#
# Формат один и тот же: «ФИО | класс | адрес журнала».

СЕКРЕТ = "INFORMATIKA"
# Дети могут назвать секрет по-русски или строчными — принимаем и так.
_ИМЕНА_СЕКРЕТА = (СЕКРЕТ, "informatika", "Informatika", "ИНФОРМАТИКА")
ФАЙЛ_НАСТРОЕК = "/content/drive/MyDrive/информатика.txt"

# Секрет есть, но этому уроку доступ к нему не включён. Colab сам
# об этом не спрашивает, поэтому подсказываем ученику, что сделать.
_нет_доступа = []


def _разобрать(строка):
    части = [ч.strip() for ч in str(строка).split("|")]
    части += [""] * (3 - len(части))
    return {"name": части[0], "klass": части[1], "journal": части[2]}


def _собрать(name, klass, journal):
    return " | ".join([name or "", klass or "", journal or ""])


def _из_секрета():
    """Настройки из «Секретов» Colab."""
    try:
        from google.colab import userdata  # noqa: WPS433 (только в Colab)
    except ImportError:
        return None
    for имя in _ИМЕНА_СЕКРЕТА:
        try:
            значение = userdata.get(имя)
        except Exception as ошибка:
            # NotebookAccessError: секрет заведён, но переключатель
            # доступа у этого урока выключен
            вид = type(ошибка).__name__
            if вид == "NotebookAccessError":
                _нет_доступа.append(имя)
            elif вид == "TimeoutException":
                return None      # интерфейс Colab не отвечает, не ждём зря
            continue
        if значение:
            return _разобрать(значение)
    return None


def _из_файла():
    """Настройки с Диска — только если он уже подключён к этому уроку."""
    try:
        with open(ФАЙЛ_НАСТРОЕК, encoding="utf-8") as файл:
            return _разобрать(файл.read())
    except Exception:
        return None


_кэш_настроек = []          # спрашиваем хранилища один раз за урок


def _сохранённые():
    """Найденные настройки; хранилища опрашиваем один раз за запуск."""
    if not _кэш_настроек:
        _нет_доступа.clear()
        _кэш_настроек.append(_из_секрета() or _из_файла())
    return _кэш_настроек[0]


def запомнить(name="", klass="", journal=""):
    """Показать строку настроек, чтобы завести из неё секрет.

    Секрет создаётся руками в боковой панели Colab — код туда писать
    не умеет, и это правильно: иначе любой ноутбук мог бы натворить дел.
    """
    строка = _собрать(name or _state["name"],
                      klass or _state["klass"],
                      journal or APPS_SCRIPT_URL)
    print("Твоя строка для секрета (выдели и скопируй её целиком):")
    print()
    print("   " + строка)
    print()
    print("1. Слева на панели Colab нажми значок ключа 🔑.")
    print("2. Нажми «+ Добавить секрет».")
    print(f"3. В поле «Название» напиши: {СЕКРЕТ}")
    print("4. В поле «Значение» вставь строку выше.")
    print("5. Включи переключатель в столбце «Доступ из блокнотов».")
    print()
    print("На следующих уроках открой 🔑 и включи тот же переключатель —")
    print("поля заполнятся сами.")
    return строка


def запомнить_на_диске(name="", klass="", journal=""):
    """Сохранить настройки файлом на Google Диске.

    Запросит доступ к Диску. Вариант для тех, кому секреты неудобны:
    на следующих уроках достаточно запустить si.диск().
    """
    строка = _собрать(name or _state["name"],
                      klass or _state["klass"],
                      journal or APPS_SCRIPT_URL)
    if not _подключить_диск():
        return ""
    try:
        with open(ФАЙЛ_НАСТРОЕК, "w", encoding="utf-8") as файл:
            файл.write(строка)
    except Exception as ошибка:
        print(f"{WARN}  Не удалось записать файл: {ошибка}")
        return ""
    print(f"{OK}  Сохранено на Диске: {ФАЙЛ_НАСТРОЕК}")
    print("   На следующем уроке запусти si.диск() — поля заполнятся сами.")
    return строка


def _подключить_диск():
    try:
        from google.colab import drive  # noqa: WPS433 (только в Colab)
    except ImportError:
        print(f"{WARN}  Диск подключается только в Colab.")
        return False
    try:
        drive.mount("/content/drive")
        return True
    except Exception as ошибка:
        print(f"{WARN}  Диск не подключился: {ошибка}")
        return False


def диск():
    """Подключить Диск и подставить сохранённые там настройки."""
    if not _подключить_диск():
        return False
    настройки = _из_файла()
    if not настройки or not настройки["name"]:
        print(f"{WARN}  Настроек на Диске нет. Заполни поля вручную и запусти")
        print("   si.запомнить_на_диске() — в следующий раз подставится само.")
        return False
    _применить(настройки)
    return True


def _применить(настройки, только_пустые=False):
    """Подставить сохранённые настройки. Введённое руками главнее."""
    global APPS_SCRIPT_URL
    if настройки["name"] and not (только_пустые and _state["name"]):
        _state["name"] = настройки["name"]
    if настройки["klass"] and not (только_пустые and _state["klass"]):
        _state["klass"] = настройки["klass"]
    if настройки["journal"] and not (только_пустые and APPS_SCRIPT_URL):
        APPS_SCRIPT_URL = адрес_журнала(настройки["journal"])
    if _state["name"]:
        print(f"{OK}  Настройки подставлены: {_state['name']}"
              + (f", {_state['klass']}" if _state["klass"] else ""))


# ── Состояние сессии ──────────────────────────────────────────────────────
_state = {
    "lesson": None,
    "name": "",
    "klass": "",
    "email": "",
    "verified": False,
    "started": None,
    "results": {},      # task -> dict(ok, attempts, detail)
    "sent": 0,
    "send_errors": 0,
}

OK = "\N{WHITE HEAVY CHECK MARK}"
BAD = "\N{CROSS MARK}"
WARN = "\N{WARNING SIGN}"
INFO = "\N{INFORMATION SOURCE}"


# ── Опознание ученика ─────────────────────────────────────────────────────

def _colab_email(timeout=20):
    """Вернуть подтверждённый email из Google-аккаунта ученика.

    Работает только в Colab. Сначала пробуем userinfo, затем Drive API —
    у одного из двух эндпоинтов нужный доступ есть почти всегда.
    """
    try:
        from google.colab import auth  # noqa: WPS433  (доступен только в Colab)
    except ImportError:
        return ""

    try:
        auth.authenticate_user()
        import google.auth
        import google.auth.transport.requests as gart

        creds, _ = google.auth.default()
        creds.refresh(gart.Request())
        token = creds.token
    except Exception:
        return ""

    endpoints = (
        ("https://www.googleapis.com/oauth2/v3/userinfo", "email"),
        ("https://www.googleapis.com/drive/v3/about?fields=user", None),
    )
    for url, key in endpoints:
        try:
            req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            email = data.get(key) if key else data.get("user", {}).get("emailAddress")
            if email:
                return email
        except Exception:
            continue
    return ""


def start(lesson, name="", klass="", identify=True, journal=""):
    """Начать урок: опознать ученика и подготовить журнал.

    lesson — код урока, например "07-05".
    name, klass — ФИО и класс из формы в начале ноутбука.
    identify — запрашивать ли подтверждение Google-аккаунта.
    journal — адрес журнала учителя (или его короткий идентификатор).
    """
    global APPS_SCRIPT_URL

    _кэш_настроек.clear()

    _state.update(
        lesson=str(lesson),
        name=name.strip(),
        klass=klass.strip(),
        started=time.time(),
        results={},
        sent=0,
        send_errors=0,
        email="",
        verified=False,
    )

    if journal:
        APPS_SCRIPT_URL = адрес_журнала(journal)

    if not _state["name"] or not APPS_SCRIPT_URL:
        # Что-то не заполнено — возможно, ученик сохранял настройки раньше.
        настройки = _сохранённые()
        if настройки:
            _применить(настройки, только_пустые=True)

    if not _state["name"]:
        if _нет_доступа:
            print(f"{WARN}  Секрет {_нет_доступа[0]} найден, но этому уроку он закрыт.")
            print("   Нажми 🔑 на панели слева, включи переключатель рядом")
            print("   с секретом и запусти эту ячейку ещё раз.")
        else:
            print(f"{WARN}  Заполни поле ФИО в форме выше и запусти эту ячейку заново.")
            print("   Если ты сохранял настройки на Диске — запусти si.диск().")
        return

    if identify:
        email = _colab_email()
        if email:
            _state["email"] = email
            _state["verified"] = True

    who = _state["name"]
    if _state["klass"]:
        who += f", {_state['klass']}"
    print(f"{OK}  Урок {_state['lesson']}. Ученик: {who}")
    if _state["verified"]:
        print(f"{OK}  Аккаунт подтверждён: {_state['email']}")
    else:
        print(f"{WARN}  Аккаунт не подтверждён — результат уйдёт учителю с пометкой «без подтверждения».")
    if APPS_SCRIPT_URL == _UNSET:
        print(f"{INFO}  Журнал не подключён — в конце урока получишь квитанцию,")
        print(f"   её нужно будет отправить учителю. Чтобы результаты уходили")
        print(f"   сами, впиши адрес журнала в поле «Журнал» в форме выше.")
    elif not _сохранённые():
        print(f"{INFO}  Надоело вводить это каждый урок? Запусти si.запомнить()")
    print("\nРешай задачи ниже. После каждой запускай ячейку с проверкой.")


# ── Проверка решений ──────────────────────────────────────────────────────

def _describe(value, limit=120):
    text = repr(value)
    return text if len(text) <= limit else text[:limit] + " …"


def _source_of(func):
    try:
        return inspect.getsource(func)
    except (OSError, TypeError):
        return ""


def _record(task, ok, detail, source=""):
    entry = _state["results"].setdefault(task, {"ok": False, "attempts": 0})
    entry["attempts"] += 1
    entry["ok"] = bool(ok)
    entry["detail"] = detail
    _send(task, entry, source)
    return ok


def check(task, func, cases, name=None):
    """Проверить функцию на наборе тестов.

    cases — список пар (аргументы, ожидаемый результат).
    Аргументы задаются кортежем; для одного аргумента можно писать значение.
    """
    if _state["lesson"] is None:
        print(f"{WARN}  Сначала запусти ячейку регистрации (si.start).")
        return False

    title = name or f"Задача {task}"
    if not callable(func):
        print(f"{BAD}  {title}: ожидалась функция, получено {type(func).__name__}.")
        return _record(task, False, "не функция")

    failures = []
    for args, expected in cases:
        call_args = args if isinstance(args, tuple) else (args,)
        try:
            got = func(*call_args)
        except Exception:
            trace = traceback.format_exc(limit=1).strip().splitlines()[-1]
            failures.append((call_args, expected, f"ошибка: {trace}"))
            continue
        if got != expected:
            failures.append((call_args, expected, _describe(got)))

    total = len(cases)
    passed = total - len(failures)
    source = _source_of(func)

    if not failures:
        print(f"{OK}  {title}: пройдено {total} из {total}. Отлично!")
        return _record(task, True, f"{total}/{total}", source)

    print(f"{BAD}  {title}: пройдено {passed} из {total}.")
    for call_args, expected, got in failures[:3]:
        shown = ", ".join(_describe(a, 40) for a in call_args)
        print(f"    при аргументах ({shown}) ожидалось {_describe(expected, 60)}, получено {got}")
    if len(failures) > 3:
        print(f"    …и ещё {len(failures) - 3} несовпадений")
    return _record(task, False, f"{passed}/{total}", source)


def check_value(task, value, digest, name=None, hint=""):
    """Сверить ответ с эталоном по хешу — ответа в ноутбуке не видно.

    digest получают функцией schoolinf.digest(эталон) при подготовке урока.
    """
    if _state["lesson"] is None:
        print(f"{WARN}  Сначала запусти ячейку регистрации (si.start).")
        return False

    title = name or f"Задача {task}"
    ok = digest_of(value) == digest
    if ok:
        print(f"{OK}  {title}: верно.")
    else:
        print(f"{BAD}  {title}: неверно. Твой ответ — {_describe(value, 60)}.")
        if hint:
            print(f"    Подсказка: {hint}")
    return _record(task, ok, "верно" if ok else "неверно", f"ответ = {_describe(value, 200)}")


def digest_of(value):
    """Хеш ответа. Числа, строки и списки приводятся к единому виду."""
    if isinstance(value, float) and value == int(value):
        value = int(value)
    if isinstance(value, str):
        value = value.strip().lower().replace("ё", "е")
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


# Короткое имя для подготовки материалов учителем.
digest = digest_of

# Понятное имя для младших классов: там задачи решаются переменными,
# а не функциями, и «check_value» звучит для пятиклассника загадочно.
ответ = check_value


# ── Отправка в журнал учителя ─────────────────────────────────────────────

def _payload(task, entry, source):
    return {
        "course": COURSE,
        "lesson": _state["lesson"],
        "task": str(task),
        "name": _state["name"],
        "klass": _state["klass"],
        "email": _state["email"],
        "verified": _state["verified"],
        "ok": entry["ok"],
        "detail": entry.get("detail", ""),
        "attempt": entry["attempts"],
        "source": source[:4000],
        "client_time": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


def _send(task, entry, source):
    if APPS_SCRIPT_URL == _UNSET:
        return
    body = json.dumps(_payload(task, entry, source), ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(
        APPS_SCRIPT_URL,
        data=body,
        headers={"Content-Type": "text/plain;charset=utf-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15):
            _state["sent"] += 1
    except (urllib.error.URLError, TimeoutError, OSError):
        _state["send_errors"] += 1


# ── Итог урока ────────────────────────────────────────────────────────────

def receipt():
    """Компактная строка с результатами — её можно переслать учителю."""
    data = {
        "l": _state["lesson"],
        "n": _state["name"],
        "k": _state["klass"],
        "e": _state["email"],
        "v": int(_state["verified"]),
        "t": time.strftime("%Y-%m-%d %H:%M"),
        "r": {t: [int(v["ok"]), v["attempts"]] for t, v in sorted(_state["results"].items())},
    }
    raw = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "INF-" + base64.urlsafe_b64encode(zlib.compress(raw, 9)).decode("ascii")


def decode_receipt(code):
    """Разобрать квитанцию — используется в журнале учителя."""
    code = code.strip()
    if code.startswith("INF-"):
        code = code[4:]
    raw = zlib.decompress(base64.urlsafe_b64decode(code.encode("ascii")))
    return json.loads(raw.decode("utf-8"))


def report():
    """Показать итог урока и отправить его учителю."""
    if _state["lesson"] is None:
        print(f"{WARN}  Урок не начат: запусти ячейку регистрации.")
        return

    results = _state["results"]
    solved = sum(1 for v in results.values() if v["ok"])
    total = len(results)

    print("─" * 58)
    print(f"Итог урока {_state['lesson']} — {_state['name'] or 'без имени'}")
    print("─" * 58)
    if not results:
        print("Ни одна задача пока не проверена.")
        return
    for task, entry in sorted(results.items()):
        mark = OK if entry["ok"] else BAD
        print(f"  {mark}  Задача {task}: {entry.get('detail', '')}, попыток — {entry['attempts']}")
    print("─" * 58)
    print(f"Решено {solved} из {total}.")

    if APPS_SCRIPT_URL != _UNSET and _state["sent"] and not _state["send_errors"]:
        print(f"{OK}  Результат отправлен учителю.")
    else:
        if APPS_SCRIPT_URL != _UNSET and _state["send_errors"]:
            print(f"{WARN}  Отправить не удалось ({_state['send_errors']} раз). Перешли квитанцию:")
        else:
            print(f"{INFO}  Квитанция для учителя — скопируй строку целиком:")
        print()
        print(receipt())


def status():
    """Текущее состояние сессии — для отладки."""
    return dict(_state)


if __name__ == "__main__":  # быстрая самопроверка модуля вне Colab
    start(lesson="00-00", name="Тест Тестов", klass="7А", identify=False)
    check("1", lambda a, b: a + b, [((1, 2), 3), ((0, 0), 0)])
    check("2", lambda a: a * 2, [(2, 5)])
    check_value("3", 42, digest_of(42))
    report()
    assert decode_receipt(receipt())["n"] == "Тест Тестов"
    print("\nself-test ok", file=sys.stderr)
