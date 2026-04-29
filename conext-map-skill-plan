# Context Map Skill Plan

> План создания скилла, который генерирует `context-map.md` для проектов разработки.
> Файл намеренно назван `conext-map-skill-plan` по текущей договоренности.

## Цель скилла

Создать навык для AI-агента, который быстро исследует проект и генерирует `context-map.md`: короткую, практичную карту проекта для восстановления контекста после сброса памяти, ускорения разработки и снижения риска повторять уже найденные ошибки.

Главный принцип: `context-map.md` не заменяет README, PRD или архитектурную документацию. Это навигационная карта для агента: что это за проект, где что лежит, какие инварианты нельзя ломать, какие команды запускать и куда идти для конкретного типа задачи.

## Язык общения

Скилл должен общаться на языке текущей пользовательской сессии. Если пользователь пишет по-русски, first-run объяснения, вопросы, финальный ответ и сам `context-map.md` должны быть на русском.

Исключения:

- пользователь явно попросил другой язык;
- в репозитории уже есть жёсткая документационная политика на другом языке, и пользователь хочет её сохранить;
- технические имена, пути, команды, API, названия файлов и устоявшиеся section names лучше оставить как есть для точности.

## Когда использовать скилл

- Пользователь просит создать, обновить или улучшить `context-map.md`.
- Нужно быстро задокументировать существующий проект для будущих AI-агентов.
- Проект большой или старый, и агент каждый раз тратит много времени на повторное исследование.
- После крупного рефакторинга нужно обновить карту архитектуры, gotchas, команды и точки входа.
- Нужно подготовить onboarding-документ для Claude Code, Codex, Cursor, Gemini CLI или другого агента.

## Исходные наблюдения из текущих проектов

В твоих проектах context maps обычно содержат:

- короткое описание проекта и его текущий статус;
- стек технологий;
- дерево директорий с комментариями;
- список файлов, которые читать первыми;
- архитектурные схемы и потоки данных;
- API, БД, модели, env-переменные, конфиги;
- критические инварианты, формулы, порядок роутеров, обязательные поля API;
- known issues: известные ошибки, косяки, нестабильные зоны и обходные пути;
- decisions: основные принятые решения за сессию и в проекте в целом;
- gotchas и уже пройденные ошибки;
- команды локального запуска, тестирования и деплоя;
- карту "что где менять";
- roadmap, что сделано и что не сделано;
- инструкции, что добавлять в context map после будущих изменений.

Лучшие документы написаны не как публичный README, а как оперативная память проекта для агента.

## Масштабы проектов и нужный формат

### XS: микро-проект или одноразовый скрипт

Размер: 1-5 файлов, один язык, нет деплоя или БД.

Цель документа: не раздуть контекст, а зафиксировать назначение, команды и пару gotchas.

Рекомендуемый размер: 30-80 строк.

Структура:

```md
# Context Map: Project Name

> Quick orientation after context reset.

## What This Is
1-3 абзаца: задача, входы, выходы.

## Files
| File | Purpose |
|------|---------|

## How To Run
```bash
...
```

## Gotchas
- ...

## Known Issues
- None known / KI-001 ...

## Decisions
- D-001 ...

## Update This File When
- меняется CLI/API;
- добавляется новый источник данных;
- меняются команды запуска.
```

Что не нужно: подробная архитектура, roadmap, длинные таблицы API, дерево всего проекта.

### S: маленький проект

Размер: 5-25 файлов, один сервис или небольшое приложение, простая структура.

Цель документа: дать агенту быстрый путь к нужным файлам и защитить от типовых ошибок.

Рекомендуемый размер: 80-160 строк.

Структура:

```md
# Context Map: Project Name

> Read first after context reset.

## What This Is
## Tech Stack
## File Map
## Read First
## Main Flow
## Configuration
## Common Tasks
| Task | File(s) |
## Known Issues
## Decisions
## Agent Conflict Protocol
## Gotchas
## Test / Run Commands
## What To Update Here
```

Обязательные элементы: `Read First`, `Common Tasks`, `Known Issues`, `Decisions`, `Gotchas`, команды проверки.

### M: средний проект

Размер: 25-150 файлов, несколько модулей, backend/frontend, БД или внешние API.

Цель документа: заменить повторную разведку проекта перед каждой задачей.

Рекомендуемый размер: 160-320 строк.

Структура:

```md
# Context Map: Project Name

> Single source of truth for AI assistants to reorient quickly.
> Last updated: YYYY-MM-DD, short reason.

## Project Identity
## Current Status
## Tech Stack
## Directory Structure
## Read First By Task Type
| Task Type | Start Here | Then Check |
## Architecture Overview
ASCII-схема или короткий flow.
## Key Flows
### Auth / Sync / AI / Payment / Deploy
## Data Model / API
## Configuration
## Local Development
## Deployment
## Design System / UI Rules
## Known Issues
## Decisions
## Agent Conflict Protocol
## Gotchas
## What To Change Where
## Validation Checklist
## Keep This Updated
```

Обязательные элементы: task routing, architecture overview, data/API, known issues, decisions, validation checklist, gotchas.

### L: большой монорепо или продуктовая система

Размер: 150-1000+ файлов, несколько приложений, backend/frontend/mobile, CI/CD, БД, интеграции.

Цель документа: быть корневой картой, а не единственным документом. Должен направлять агента в подробные docs.

Рекомендуемый размер: 300-600 строк. Если больше, нужно делить на `docs/context/*.md`.

Структура:

```md
# Product Name — Context Map

> Purpose: fast reorientation for AI assistants and maintainers.
> Last updated: YYYY-MM-DD.
> Scope: root map. Deep details live in linked docs.

## Product Identity
## Live / Repos / Environments
## System Map
## Apps / Packages
## Directory Structure
## Read First By Task Type
## Architecture
### Frontend
### Backend
### Mobile
### Workers / Jobs
### Integrations
## Key Domain Models
## API Surface
## Database / Migrations
## Auth / Permissions
## Deployment / Infra
## Observability
## Design System
## Known Large Files / Refactor Candidates
## Critical Invariants
## Known Issues
## Decisions
## Agent Conflict Protocol
## Gotchas / Avoid Repeating
## Validation Matrix
## Roadmap / Current Phase
## Linked Docs
```

Правило: root context map должен отвечать "куда идти дальше", а не пытаться вместить всю документацию.

### XL: платформа, несколько репозиториев или долгоживущая экосистема

Размер: несколько repos, несколько команд/продуктов, внешние SDK, production-инфраструктура.

Цель документа: root index + отдельные context maps по доменам.

Рекомендуемый формат:

```text
context-map.md                    # root index, 150-300 строк
docs/context/frontend.md
docs/context/backend.md
docs/context/mobile.md
docs/context/deploy.md
docs/context/integrations.md
docs/context/gotchas.md
docs/context/agent-playbook.md
```

Root structure:

```md
# Platform Context Map

## What This Platform Is
## Repositories
## Environments
## System Boundaries
## Read First By Task
## Cross-Cutting Invariants
## Known Issues
## Decisions
## Agent Conflict Protocol
## Where Deep Context Lives
## Current Risks
## Update Protocol
```

Правило: root file должен оставаться обзорным. Детальные API, БД и деплой живут в отдельных файлах.

## Как скилл должен определять масштаб

Скилл не должен спрашивать пользователя, если масштаб можно вывести автоматически. Он должен:

1. Посчитать файлы, исключая `node_modules`, `.git`, `.build`, `dist`, `build`, `.next`, `venv`, `__pycache__`, `DerivedData`.
2. Определить количество языков/стеков по файлам: package.json, pyproject.toml, requirements.txt, Dockerfile, project.yml, *.xcodeproj, Cargo.toml, go.mod и т.д.
3. Найти приложения/пакеты: `frontend/`, `backend/`, `src/`, `apps/`, `packages/`, `ios/`, `android/`, `worker/`.
4. Проверить наличие БД/деплоя/API: migrations, prisma, alembic, docker-compose, .github/workflows, nginx, Terraform, wrangler.
5. Проверить размер ключевых файлов и наличие монолитов.
6. Проверить существующую документацию: README, CLAUDE.md, AGENTS.md, PRD, architecture, decisions, known-issues.

Пример эвристики:

```text
XS: <=5 source files, 1 stack, no deploy/db
S: 6-25 source files, 1 app, simple config
M: 26-150 source files, 1-2 apps, API/db/deploy present
L: 151-1000 source files, 2+ apps or major integrations
XL: multiple repos or platform with separate SDKs/environments
```

Если проект маленький, но содержит production deploy, БД или внешние платежи/auth, повышать масштаб минимум до M.

## Workflow будущего скилла

1. Найти корень проекта.
2. Прочитать существующие agent-инструкции: `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `.cursor/rules`, если есть.
3. Собрать карту файлов через `rg --files`.
4. Исключить generated/vendor/build папки.
5. Определить стек и масштаб.
6. Прочитать README и основные docs.
7. Прочитать историю решений и проблем, если есть: `decisions.md`, `DECISIONS.md`, `ADR*`, `docs/decisions*`, `known-issues.md`, `KNOWN_ISSUES.md`, `fixed-errors.md`, `troubleshooting.md`, issue notes.
8. Найти entry points, routes, stores, services, migrations, config, deploy.
9. Найти команды запуска и тестов из package scripts, Makefile, pyproject, README, CI.
10. Найти потенциальные gotchas, known issues и decisions:
   - TODO/FIXME/HACK;
   - known-issues/decisions/fixed-errors;
   - ADR и decision logs;
   - явно отмененные подходы;
   - повторяющиеся ошибки из прошлых сессий;
   - нестандартные порты;
   - порядок регистрации роутеров;
   - обязательные env vars;
   - большие монолитные файлы;
   - внешние API со строгими полями.
11. Сгенерировать `context-map.md` по шаблону нужного масштаба.
12. Проверить, что в документе есть:
   - что это;
   - где что лежит;
   - куда идти по типу задачи;
   - как запускать/тестировать;
   - что нельзя ломать;
   - известные проблемы и обходные пути;
   - принятые решения и причины;
   - инструкция агенту сверяться с decisions/known issues перед конфликтующими изменениями;
   - что обновлять после изменений.

## Правила качества для generated context-map.md

- Писать для AI-агента, не для маркетинга.
- Быть конкретным: файлы, команды, порты, endpoint paths, env vars.
- Не пересказывать весь код.
- Не включать секреты, токены, пароли, приватные ключи.
- Не копировать огромные куски README.
- Использовать таблицы для маршрутизации и API.
- Использовать ASCII-схемы только когда они реально ускоряют понимание.
- Явно отмечать предположения и непроверенные части.
- `Known Issues` писать как actionable memory: симптом, причина, статус, workaround, где проверять.
- `Decisions` писать как project history: решение, причина, дата/сессия, последствия, что не повторять.
- Если новая задача конфликтует с `Known Issues` или `Decisions`, агент должен остановиться и спросить человека, действительно ли нужно нарушить/изменить прежнее решение.
- Для больших проектов ссылаться на docs, а не дублировать их.
- Добавлять `Last updated` только если скилл реально знает дату генерации.

## Как улучшить текущие документы

### 1. Добавить единый блок метаданных

Во всех context maps полезно иметь короткий верхний блок:

```md
> Purpose: ...
> Last updated: YYYY-MM-DD — reason
> Scope: root map / frontend map / deploy map
> Read time: ~N minutes
```

Это помогает агенту понять свежесть и границы документа.

### 2. Добавить `Read First By Task Type`

Сейчас это есть в некоторых файлах, но не везде. Это один из самых полезных блоков.

```md
## Read First By Task Type

| Task | Start Here | Then Check | Validate With |
|------|------------|------------|---------------|
| Backend endpoint | `backend/app/routes/...` | `models/`, migrations | `pytest ...` |
| UI change | `frontend/src/...` | design tokens | `npm run build` |
| Deploy issue | `.github/workflows/...` | nginx/PM2 logs | healthcheck |
```

### 3. Разделить `Gotchas` на типы

Вместо одного длинного списка:

```md
## Gotchas
### Runtime
### API / Data
### Deploy
### UI
### Agent Mistakes To Avoid
```

Так агент быстрее находит релевантный риск.

### 4. Добавить validation matrix

Почти каждый файл выигрывает от явной таблицы проверок:

```md
## Validation Checklist

| Change Type | Required Check |
|-------------|----------------|
| Backend route | unit/integration test + curl healthcheck |
| UI token change | build + visual smoke check |
| DB schema | migration + seed/startup check |
| Deploy config | dry run / healthcheck |
```

### 5. Убрать устаревающую git-историю

Блок "последние коммиты" полезен только временно. Лучше заменить на:

```md
## Current Phase
- Active focus:
- Recently changed:
- Known unstable areas:
```

Коммиты быстро устаревают, а смысловая фаза проекта живет дольше.

### 6. Явно отделять verified от inferred

Если агент генерирует карту не после глубокого чтения, нужно помечать:

```md
## Confidence Notes
- Verified from code: ...
- Inferred from names/docs: ...
- Needs human confirmation: ...
```

Это снижает риск ложной уверенности.

### 7. Для больших проектов вынести deep sections

Если context map >600 строк, лучше:

```text
docs/context-map.md
docs/context/backend.md
docs/context/frontend.md
docs/context/deploy.md
docs/context/gotchas.md
```

Root map должен быть маршрутизатором.

### 8. Добавить "Do Not Touch / Be Careful"

Особенно для проектов с legacy или production:

```md
## Be Careful
- Не менять порядок роутеров.
- Не трогать seed migration order.
- Не использовать port 5000 на macOS.
- Не хранить API keys в DB.
```

### 9. Добавить `Known Issues`

Это не просто список багов. Это память проекта о проблемах, которые уже известны и могут повлиять на будущие изменения.

Рекомендуемый формат:

```md
## Known Issues

| ID | Area | Symptom | Cause | Status | Workaround / Rule |
|----|------|---------|-------|--------|-------------------|
| KI-001 | Deploy | 502 after deploy | backend crashes before seed migration finishes | open | check PM2 logs and migration order |
| KI-002 | UI | dark mode colors inconsistent | old components use hardcoded colors | partial | use design tokens for new UI |
```

Для маленьких проектов можно проще:

```md
## Known Issues

- **KI-001: Port 5000 fails on macOS.**
  Cause: AirPlay uses this port.
  Rule: use port 5050.
```

Правила:

- Каждая known issue должна быть понятна без чтения всей истории.
- Обязательно писать статус: `open`, `partial`, `fixed`, `wontfix`, `watch`.
- Если issue fixed, оставить ее, если агент может повторить старую ошибку.
- Для fixed issues писать "do not regress" или "avoid repeating".

### 10. Добавить `Decisions`

`Decisions` фиксирует не только архитектурные решения проекта, но и важные решения, принятые в текущей агентской сессии.

Рекомендуемый формат:

```md
## Decisions

| ID | Date / Session | Decision | Rationale | Consequence | Do Not Repeat |
|----|----------------|----------|-----------|-------------|---------------|
| D-001 | 2026-04-19 | Public pages stay light-only | product direction and simpler QA | no dark toggle on public pages | do not re-add dark mode without approval |
| D-002 | 2026-04-19 | Use SQLite for bot/admin shared storage | simple deploy, no infra | one shared volume | do not introduce Postgres for this app casually |
```

Для крупных проектов можно держать полный decision log в `decisions.md`, а в `context-map.md` оставить только активные решения, которые влияют на ежедневную работу агента.

Важно: `Decisions` должен содержать не только "что выбрали", но и "почему", иначе будущий агент не поймет, когда решение можно пересмотреть.

### 11. Добавить Agent Conflict Protocol

В каждом M/L/XL context map нужен явный протокол:

```md
## Agent Conflict Protocol

Before making changes, check `Known Issues` and `Decisions`.

If the requested change conflicts with a past decision or known issue:
1. Do not silently override the decision.
2. Explain the conflict in one short paragraph.
3. Ask the human whether they want to intentionally change course.
4. If they confirm, update `Decisions` with the new decision and rationale.
5. If the change fixes or changes a known issue, update `Known Issues`.
```

Пример поведения:

```text
The requested dark-mode toggle conflicts with D-001, where public pages were made light-only to reduce QA scope. Do you want to reverse that decision for this feature?
```

Это защищает проект от ситуации, когда разные агенты по кругу возвращают уже отмененные подходы.

### 12. Добавить "Update Protocol"

В конце каждого документа:

```md
## Update Protocol

Update this file when:
- moved entry points;
- changed deploy flow;
- added DB tables;
- made or reversed an architectural/product decision;
- discovered, fixed, or intentionally accepted a known issue;
- fixed a bug that future agents may repeat;
- changed test/run commands.
```

### 13. Сократить публично-описательные части

Некоторые описания можно сделать более агентскими:

Плохо:
> "Платформа, которая помогает пользователям..."

Лучше:
> "FastAPI + Jinja2 app. User-facing flows: `/`, `/analyze`. Admin flows: `/admin/*`. Shared SQLite DB with bot."

## First-Run пользовательский путь

Когда скилл впервые вызывают в проекте, где ещё нет `context-map.md`, агент должен не просто молча создать файл, а коротко объяснить пользователю, что происходит.

### Первый ответ после вызова

Формат ответа должен быть на языке текущей пользовательской сессии. Для русской сессии:

```text
Я создам `context-map.md`: короткую карту проекта для будущих AI-агентов. Она зафиксирует структуру, точки входа, команды, known issues, decisions и правила, чтобы агенты читали её первой и не повторяли старые ошибки.

Дополнительно могу:
- добавить `context-map.md` в `.gitignore`, если репозиторий публичный или файл должен остаться локальной памятью;
- добавить правила в `AGENTS.md` / `CLAUDE.md`, чтобы агенты всегда читали и обновляли этот файл.

Сначала просканирую проект и подготовлю карту; optional-настройки не буду менять без подтверждения.
```

### Рекомендация по git

- Если репозиторий приватный/внутренний: лучше коммитить `context-map.md`, потому что это общая память проекта.
- Если репозиторий публичный/open-source: предложить добавить `context-map.md` в `.gitignore` или использовать `context-map.local.md`.
- Если видимость репозитория неизвестна: спросить пользователя до изменения `.gitignore`.

Сниппет для `.gitignore`:

```gitignore
# AI agent local project memory
context-map.md
docs/context-map.md
docs/context/
```

Если в проекте уже есть публичная документация в `docs/context/`, нельзя игнорировать всю папку; нужно добавлять только конкретный private/local файл.

### Рекомендация по AGENTS.md / CLAUDE.md

Скилл должен предложить добавить правила:

```md
## Project Context Map

- Read `context-map.md` or `docs/context-map.md` before planning or editing.
- Treat `Known Issues`, `Decisions`, and `Agent Conflict Protocol` as project memory.
- If a requested change conflicts with `Known Issues` or `Decisions`, explain the conflict and ask before proceeding.
- Update the context map when:
  - entry points, architecture, deploy flow, or run/test commands change;
  - DB schema, API contracts, auth, payments, or external integrations change;
  - a significant decision is made or reversed;
  - a known issue is discovered, fixed, accepted, or gets a workaround;
  - an agent fixes a bug that future agents may repeat.
- Do not put secrets, tokens, passwords, or private credentials in the context map.
```

### Поведение после создания файла

Финальный ответ после первого создания:

- показать путь созданного файла;
- сказать, что `.gitignore` и `AGENTS.md`/`CLAUDE.md` не менялись без подтверждения;
- дать рекомендацию: для публичного repo игнорировать или local-variant, для приватного repo закоммитить и добавить agent-rules.

## Предлагаемая структура будущего скилла

```text
context-map-skill/
├── SKILL.md
├── references/
│   ├── templates.md        # шаблоны XS/S/M/L/XL
│   ├── heuristics.md       # определение масштаба и стеков
│   ├── decision-format.md  # формат Decisions + Agent Conflict Protocol
│   ├── first-run.md        # первый пользовательский путь и snippets для .gitignore/AGENTS/CLAUDE
│   └── quality-check.md    # чеклист качества и анти-паттерны
└── scripts/
    └── inspect_project.py  # опционально: deterministic scan summary
```

В `SKILL.md` держать только workflow и правила выбора масштаба. Подробные шаблоны вынести в `references/templates.md`, чтобы не раздувать навык.

## MVP скилла

Первая версия может быть без скриптов:

1. SKILL.md с workflow.
2. Один reference file с шаблонами XS/S/M/L/XL.
3. Quality checklist.
4. Формат `Known Issues`.
5. Формат `Decisions`.
6. `Agent Conflict Protocol`.
7. `First Run` onboarding: объяснить, что создаётся, и предложить `.gitignore` + `AGENTS.md`/`CLAUDE.md` rules.
8. Инструкция: сначала сгенерировать черновик, потом проверить его против codebase и убрать непроверенные утверждения.

## v2 скилла

Добавить `scripts/inspect_project.py`, который печатает JSON/Markdown summary:

- total source files;
- detected stacks;
- entry points;
- package scripts;
- env examples;
- CI workflows;
- largest files;
- likely generated/vendor dirs;
- docs found;
- candidate gotchas from TODO/FIXME/HACK/known-issues.
- candidate decisions from decisions/ADR/docs/history.
- candidate known issues from known-issues/troubleshooting/fixed-errors/TODO.

Агент использует summary как вход для генерации context map.

v2 также должен поддерживать точечные режимы:

- `audit-decisions`: проверить, есть ли в context map решения, которые реально влияют на работу агента.
- `audit-known-issues`: проверить, понятны ли issues агенту: симптом, причина, статус, workaround.
- `conflict-check`: перед предложенным изменением найти конфликтующие decisions/known issues и сформулировать вопрос человеку.

## Batch + Dashboard v2.1

Добавить batch-режимы:

- `batch-discover` — найти проекты в одной или нескольких директориях;
- `batch-plan` — показать найденные проекты с номерами и попросить пользователя выбрать;
- `batch-generate` — создать/обновить context maps для выбранных проектов очередью;
- `batch-index` — собрать общий JSON индекс по всем context maps;
- `dashboard-data` — подготовить данные для будущей веб-морды.

### Global config

Путь:

```text
~/.context-map/config.json
```

Формат:

```json
{
  "version": 1,
  "project_roots": [
    "/Users/viacheslavkuznetsov/Desktop/Projects"
  ],
  "exclude_dirs": [
    "node_modules",
    ".git",
    ".next",
    "dist",
    "build",
    ".build",
    "DerivedData",
    "venv",
    ".venv"
  ],
  "context_map_names": [
    "context-map.md",
    "docs/context-map.md",
    "CONTEXT-MAP.md"
  ],
  "dashboard_index_path": "~/.context-map/index.json"
}
```

Если config отсутствует, скилл использует paths из запроса пользователя или текущую директорию.

### Batch UX

Скилл не должен сразу проходить все проекты автоматически. Он должен:

1. найти кандидатов;
2. показать список с номерами;
3. показать path, stack, scale, наличие context-map, git status;
4. попросить выбрать номера/диапазоны;
5. обрабатывать выбранные проекты по очереди.

Синтаксис выбора:

```text
1,3,5-8
all
none
```

### Контекстные лимиты

Не использовать ручной compact как обязательный UX. Вместо этого:

- каждый проект обрабатывается отдельной итерацией;
- агент читает только контекст текущего проекта;
- после каждого проекта записывает `context-map.md`;
- после каждого чанка обновляет `~/.context-map/index.json`;
- если context всё же сбросится, восстановление идёт из уже записанных файлов и индекса.

### Dashboard-ready frontmatter

Новые/обновляемые context maps должны получать YAML frontmatter:

```yaml
---
context_map_version: 1
project_id: multi-resume
name: Super Resume
repo_path: /Users/.../multi-resume
repo_url: github.com/kyzdes/multiresume
visibility: private
status: active
scale: M
primary_stack: [Python, FastAPI, Docker]
last_updated: 2026-04-20
---
```

### Parseable sections

```md
## Known Issues
| ID | Area | Priority | Symptom | Status | Agent-Ready | Rule |

## Decisions
| ID | Date / Session | Decision | Rationale | Consequence | Do Not Repeat |

## Tasks / Next Work
| ID | Area | Type | Task | Status | Agent-Ready | Validation |
```

### Новые scripts

```text
scripts/discover_projects.py      # batch discovery по roots/config
scripts/collect_context_maps.py   # сбор ~/.context-map/index.json
```

Команды:

```bash
python3 scripts/discover_projects.py --config ~/.context-map/config.json --format markdown
python3 scripts/discover_projects.py /path/one /path/two --format json
python3 scripts/collect_context_maps.py --config ~/.context-map/config.json --output ~/.context-map/index.json
```

## Открытые решения

- Название скилла: `context-map`, `project-context-map`, `agent-context-map`.
- Нужно ли всегда создавать `docs/context-map.md`, или в root, если проект маленький.
- Нужно ли автоматически обновлять существующий context map или сначала делать diff/plan.
- Нужен ли static HTML dashboard как промежуточный шаг перед полноценной веб-мордой.
