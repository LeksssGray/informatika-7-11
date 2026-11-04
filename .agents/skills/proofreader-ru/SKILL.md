---
name: proofreader-ru
description: Корректура русского текста: исправляет только механические ошибки — орфографию, опечатки, пунктуацию, грамматику и согласование, прописные. Стиль, формулировки, сленг, англицизмы, разметку и типографику (тире, кавычки) не трогает. Использовать на «проверь на ошибки», «вычитай», «корректура», «поправь пунктуацию», «есть опечатки?», последним проходом перед сдачей или публикацией, в том числе курсовой или статьи.
license: MIT
---

## Выполнение в Codex

Применяй методику ниже в рамках текущей задачи. Названия Read/Write/Edit/Bash,
Grep/Glob, Task и TodoWrite из исходника обозначают возможности, а не обязательные
инструменты: используй доступные инструменты Codex. Делегирование допустимо только
при наличии инструмента и разрешения текущей сессии; иначе выполни роли последовательно.
Не считай параметры Claude разрешениями Codex. Аргументы скилла берутся из запроса
пользователя. Инструкции этого скилла не заменяют AGENTS.md и не расширяют задачу.

# Russian text proofreader (proofreader-ru)

> Из [unicodef1wn/russian-writing-skills](https://github.com/unicodef1wn/russian-writing-skills) (MIT), взят 2026-10-16;
> описание переведено. Для учебной работы типографику (тире, «ёлочки») расставит gostdoc при сборке.

The task is to proofread Russian text and fix **only mechanical errors** without touching the author's voice. This is a proofreader, not an editor: it doesn't make the text "better", "livelier" or "smoother". It fixes what is objectively wrong by the norms of the Russian language and leaves everything else alone.

**Core principle:** when in doubt — DON'T touch. Breaking the author's intentional slang is worse than missing a rare typo. The proofreader is conservative.

All examples below are in Russian on purpose — the skill works on Russian text.

---

## What the skill FIXES

- **Spelling and typos** in ordinary Russian words (`карова` → `корова`, `генерция` → `генерация`, `превет` → `привет`)
- **Typos inside slang/anglicisms**, if the word is recognizable as a distortion of a known form (`зафиксеть` → `зафиксить`, `вайбкодиг` → `вайбкодинг`, `задиплоить` → `задеплоить`)
- **Punctuation**: missing and extra commas, periods, question/exclamation marks, colons, semicolons per the rules of Russian
- **Grammar and agreement**: cases, gender, number, verb forms, prepositions (`в Москва` → `в Москве`, `красивый девушка` → `красивая девушка`, `я пошёл в магазин и купил молоко за пять рублях` → `...за пять рублей`)
- **Capitalization per the rules**: sentence start, proper nouns, place names, after a period
- **«ё» — only when it changes meaning**: `все`→`всё`, `узнаем`→`узнаём`, `небо`→`нёбо` where the intended meaning is clear from context. Otherwise leave `е`/`ё` alone

## What the skill does NOT TOUCH (strictly)

- **Slang and colloquialisms**: `го`, `чекнуть`, `залетело`, `кринж`, `рофл`, `зашло` — this is the author's voice
- **Anglicisms** in any form: `вайбкодинг`, `задеплоить`, `закоммитить`, `шиллить`, `холдить`, `фича`, `пайплайн` — leave as is (only an obvious typo inside them is fixed, see above)
- **English text**: names, terms, quotes in English (`Claude Code`, `n8n`, `vibe coding`, `for you feed`) — the proofreader doesn't check English at all
- **Brand casing**: `n8n`, `iPhone`, `yandexGPT` and the like keep their spelling, even at the start of a sentence
- **Typography**: do NOT change hyphen to dash or vice versa, do NOT change `"кавычки"` to `«ёлочки»`, do NOT insert non-breaking spaces. Leave dash and quote glyphs exactly as the author had them
- **Phrasing and style**: word order, word choice, sentence length, rhythm — rewrite nothing
- **Emojis, markup (markdown), line breaks, indentation, numbers, dates, units** — all as they were

---

## Procedure: what to do with each "suspicious" word

For every word that isn't in an ordinary dictionary, go strictly down this ladder and **stop at the first match**:

1. **Is it a (form of a) word from `glossary.md`, spelled correctly?**
   → Leave as is. Account for inflection: `задеплоить → задеплоил, задеплоили, задеплоят` — all forms are valid.

2. **Is it an obvious distortion of a glossary word** (extra/missing letter, wrong vowel, swapped letters)?
   → Fix to the correct spelling of that form, preserving the grammar of the phrase. `зафиксеть` → `зафиксить`, `комитить` → `коммитить`, `вайпкодинг` → `вайбкодинг`.

3. **Is it unfamiliar slang / an anglicism not in the glossary?**
   - Looks like a deliberate authorial form or a new term (reads fine, inflects normally) → **leave it**. Don't touch, don't flag.
   - It's an obvious typo of an ordinary Russian word → fix it.
   - **Unclear whether it's a typo or new slang → LEAVE as is.** Stay silent, flag nothing.

This rule directly implements the chosen mode: the output is clean text only; disputed cases must not be touched.

---

## Output format

**Only the corrected text. Nothing else.**

- No preamble («Вот исправленный вариант:»), no list of edits, no explanations, no comments.
- Preserve the original formatting one-to-one: paragraphs, line breaks, markdown, emojis, blank lines.
- If no errors are found — return the text unchanged (you may say in one line that there are no errors, if the user explicitly asked «есть ли ошибки?»).

---

## Examples

### Typo inside slang → fix to canon, keep the slang
**Before:**
> вчера решил наканец задеплоеть проект, но сначала надо было зафиксеть пару багов

**After:**
> вчера решил наконец задеплоить проект, но сначала надо было зафиксить пару багов

*(`задеплоить`, `зафиксить`, `багов` — slang/anglicisms preserved; only the typos `наканец`, `задеплоеть`, `зафиксеть` were fixed)*

### Slang and anglicisms are left completely alone
**Before:**
> го зачекаем эту фичу, если зайдёт — будем шиллить в канале

**After:**
> го зачекаем эту фичу, если зайдёт — будем шиллить в канале

*(everything inside the slang is correct by the norms — left unchanged)*

### Punctuation and agreement
**Before:**
> Когда я открыл n8n я понял что воркфлоу который мы собрали вчера полностью сломался

**After:**
> Когда я открыл n8n, я понял, что воркфлоу, который мы собрали вчера, полностью сломался

*(`n8n`, `воркфлоу` preserved, brand casing `n8n` untouched; commas added)*

### Capitalization per the rules + brand keeps its casing
**Before:**
> сегодня тестил claude code на новом проекте. iphone рядом разрядился, лол

**After:**
> Сегодня тестил Claude Code на новом проекте. iPhone рядом разрядился, лол

*(capital at the start of sentences; `Claude Code` is a proper noun; `iPhone` keeps its brand casing; `тестил`, `лол` — left alone)*

### «ё» only by meaning
**Before:**
> все что мы сегодня узнаем — это что модель опять галлюцинирует

**After:**
> всё, что мы сегодня узнаём, — это что модель опять галлюцинирует

*(`все`→`всё` and `узнаем`→`узнаём` change the meaning; commas per the rules; `галлюцинирует` is an established term, left alone)*

### Unfamiliar slang when in doubt — leave it
**Before:**
> закинул эту тему в обсидиан, потом заскилапил под свой пайплайн

**After:**
> закинул эту тему в обсидиан, потом заскилапил под свой пайплайн

*(`заскилапил` isn't in the glossary and it's unclear whether it's a typo or the author's coinage; by the conservatism rule we leave it; `обсидиан`, `пайплайн` — preserved)*

---

## Order relative to other skills

If both `humanizer-ru` and `proofreader-ru` are applied to one text — **humanizer first** (it rewrites the voice and may itself introduce typos), **then proofreader** as the final read. The proofreader is always the last pass over an almost-finished text.

---

## Glossary

The list of sanctioned slang and anglicisms with canonical spellings is in `glossary.md` next to this file. Check it before proofreading. The glossary is editable: the user adds new confirmed terms by hand (the skill neither writes to the glossary nor suggests additions — the output mode is silent).

---

## Final audit before output

1. Did I change any slang/anglicism word other than obvious typos? (if yes and it wasn't a typo — roll back)
2. Did I leave English text, brands, emojis, markup, dashes/quotes untouched? (they must be as in the original)
3. Were all disputed words left unchanged?
4. Did I preserve the formatting (paragraphs, line breaks, blank lines) one-to-one?
5. Is the output text only, with no preambles or edit lists?
