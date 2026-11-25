# Единая матрица зависимостей: шесть репозиториев (F2, unified-system#156), 2026-11-25

Источник: `dependencies.json` из Workstream F (кандидаты ниже, `git archive`) и pip-пины, найденные текстом в workflow кандидатов. Машиночитаемая версия: `unified-dependency-matrix-20261125.json`.

| repo | candidate |
|---|---|
| unified-system | `f05f9a73581b1c15c4cc78da2801c9f2f5dd08d0` |
| bybit-cluster-grid | `c9ffdaa2af52c4d55871a48655a77a0c669da80f` |
| strattester | `3850995a6c28ed29b05cef4ba067e587d5033453` |
| Terminan | `353d16b2126609579018fafe3f76047b465bb289` |
| math | `9e6acbd9e12a91189f57234828e31640983af553` |
| meta_analyse | `b1a4d6a41054f0040a88dc80b585380fb6b4f323` |

## Правило выбора целевой версии
- Для каждого пакета, который встречается хотя бы в двух репозиториях, берётся одна целевая версия: максимальный точный пин среди живых манифестов (role project/test/workflow). Evidence-копии в `docs/` и `release/` в выборе не участвуют.
- Для psycopg цель задана явно: **3.3.6**. Её подтверждают lock-файлы unified-system (Windows) и meta_analyse, а также grid `requirements.txt`. Версия 3.3.2 встречается только в одной строке workflow.
- `setuptools` и `wheel` описывают ограничения build-backend, а не runtime, поэтому их не унифицируем.
- Статусы вхождений:
  - `OK`: пин совпадает с целью;
  - `RANGE-ALLOWS-TARGET`: диапазон допускает цель;
  - `CHANGED-IN-PR`: пин исправлен PR из F2;
  - `BLOCKED-HASH-LOCK`: пин стоит в lock-файле с хешами; локально хеши пересчитать нельзя (PyPI из песочницы недоступен), это делает CI или владелец;
  - `HISTORICAL`: evidence-копия, её не трогаем;
  - `DIFFERS`: решение за владельцем, его нужно подтвердить в CI.

## Сводка: цель по пакетам

| package | target | repos | OK | range ok | changed in PR | blocked hash-lock | historical | differs / range excludes |
|---|---|---|---|---|---|---|---|---|
| aiohttp | 3.14.5 | bybit-cluster-grid, meta_analyse, strattester, unified-system | 1 | 5 | 0 | 0 | 0 | 0 |
| anyio | 4.16.0 | bybit-cluster-grid, meta_analyse, unified-system | 3 | 0 | 0 | 5 | 0 | 1 |
| asyncpg | 0.32.0 | bybit-cluster-grid, strattester, unified-system | 1 | 2 | 0 | 0 | 0 | 0 |
| certifi | 2026.10.23 | bybit-cluster-grid, meta_analyse, unified-system | 3 | 0 | 0 | 5 | 0 | 1 |
| colorama | 0.4.6 | Terminan, bybit-cluster-grid, meta_analyse, unified-system | 5 | 0 | 0 | 0 | 0 | 0 |
| fastapi | 0.162.0 | bybit-cluster-grid, unified-system | 1 | 1 | 0 | 0 | 0 | 0 |
| h11 | 0.16.0 | bybit-cluster-grid, meta_analyse, unified-system | 9 | 0 | 0 | 0 | 0 | 0 |
| httpcore | 1.0.9 | bybit-cluster-grid, meta_analyse, unified-system | 9 | 0 | 0 | 0 | 0 | 0 |
| httpx | 0.28.1 | bybit-cluster-grid, meta_analyse, unified-system | 9 | 2 | 0 | 0 | 0 | 0 |
| hypothesis | 6.170.6 | meta_analyse, unified-system | 4 | 0 | 0 | 0 | 0 | 0 |
| idna | 3.20 | bybit-cluster-grid, meta_analyse, unified-system | 5 | 0 | 0 | 4 | 0 | 0 |
| iniconfig | 2.3.1 | Terminan, bybit-cluster-grid, meta_analyse, unified-system | 3 | 0 | 0 | 4 | 0 | 0 |
| jsonschema | 4.25.1 | bybit-cluster-grid, unified-system | 3 | 0 | 0 | 0 | 0 | 1 |
| numpy | 2.5.4 | bybit-cluster-grid, unified-system | 1 | 1 | 0 | 0 | 0 | 0 |
| packaging | 26.3 | Terminan, bybit-cluster-grid, meta_analyse, unified-system | 3 | 0 | 0 | 4 | 0 | 0 |
| pluggy | 1.7.0 | Terminan, bybit-cluster-grid, meta_analyse, unified-system | 3 | 0 | 0 | 4 | 0 | 0 |
| psutil | 7.2.2 | bybit-cluster-grid, strattester, unified-system | 1 | 2 | 0 | 0 | 0 | 0 |
| psycopg | 3.3.6 | bybit-cluster-grid, meta_analyse, strattester, unified-system | 4 | 1 | 3 | 0 | 0 | 0 |
| psycopg-binary | 3.3.6 | meta_analyse, unified-system | 2 | 0 | 0 | 0 | 0 | 0 |
| pydantic | 2.14.2 | bybit-cluster-grid, unified-system | 1 | 1 | 0 | 0 | 0 | 0 |
| pydantic-settings | 2.16.2 | bybit-cluster-grid, unified-system | 1 | 1 | 0 | 0 | 0 | 0 |
| pygments | 2.21.0 | Terminan, bybit-cluster-grid, meta_analyse, unified-system | 3 | 0 | 0 | 4 | 0 | 0 |
| pyside6 | 6.12.0 | Terminan, meta_analyse, unified-system | 2 | 2 | 0 | 0 | 0 | 0 |
| pyside6-addons | 6.12.0 | meta_analyse, unified-system | 2 | 0 | 0 | 0 | 0 | 0 |
| pyside6-essentials | 6.12.0 | meta_analyse, unified-system | 2 | 0 | 0 | 0 | 0 | 0 |
| pyside6-pdf | 6.12.0.140 | meta_analyse, unified-system | 2 | 0 | 0 | 0 | 0 | 0 |
| pyside6-webengine | 6.12.0.140 | meta_analyse, unified-system | 2 | 0 | 0 | 0 | 0 | 0 |
| pytest | 9.1.1 | Terminan, bybit-cluster-grid, meta_analyse, strattester, unified-system | 3 | 1 | 0 | 4 | 0 | 2 |
| pytest-asyncio | 1.4.0 | Terminan, meta_analyse, strattester, unified-system | 3 | 1 | 0 | 0 | 0 | 2 |
| python-dotenv | 1.2.4 | bybit-cluster-grid, unified-system | 1 | 1 | 0 | 0 | 0 | 0 |
| requests | 2.34.2 | strattester, unified-system | 1 | 1 | 0 | 0 | 0 | 0 |
| setuptools | — | Terminan, bybit-cluster-grid, math, meta_analyse, strattester, unified-system | 0 | 0 | 0 | 0 | 0 | 0 |
| shiboken6 | 6.12.0 | meta_analyse, unified-system | 2 | 0 | 0 | 0 | 0 | 0 |
| sortedcontainers | 2.4.0 | meta_analyse, unified-system | 3 | 0 | 0 | 0 | 0 | 0 |
| typing-extensions | 4.16.0 | Terminan, bybit-cluster-grid, meta_analyse, unified-system | 6 | 0 | 0 | 4 | 0 | 0 |
| tzdata | 2026.6 | meta_analyse, unified-system | 2 | 0 | 0 | 2 | 0 | 1 |
| uvicorn | 0.54.0 | bybit-cluster-grid, unified-system | 1 | 1 | 0 | 0 | 0 | 0 |
| websockets | 15.0.1 | bybit-cluster-grid, meta_analyse, strattester, unified-system | 2 | 4 | 0 | 0 | 0 | 0 |
| wheel | — | Terminan, bybit-cluster-grid, meta_analyse, strattester | 0 | 0 | 0 | 0 | 0 | 0 |

## Текущие пины по репозиториям

### aiohttp: цель `3.14.5`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==3.14.5` | OK |
| bybit-cluster-grid | `pyproject.toml[project.dependencies]` | project | `>=3.10,<4` | RANGE-ALLOWS-TARGET |
| bybit-cluster-grid | `requirements.txt` | project | `>=3.10` | RANGE-ALLOWS-TARGET |
| strattester | `.github/workflows/market-data-pure.yml:62` | workflow | `>=3.10,<4` | RANGE-ALLOWS-TARGET |
| strattester | `pyproject.toml[project.dependencies]` | project | `>=3.10,<4` | RANGE-ALLOWS-TARGET |
| meta_analyse | `pyproject.toml[optional[archive]]` | project | `>=3.10,<4` | RANGE-ALLOWS-TARGET |

### anyio: цель `4.16.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==4.14.2` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==4.14.2` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/intelligence/research-identity/requirements-linux.lock` | evidence/docs copy (hashes) | `==4.16.0` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-windows.lock` | evidence/docs copy (hashes) | `==4.16.0` | OK |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==4.15.1` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `tests/control_mux/requirements.lock` | test (hashes) | `==4.16.0` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==4.14.2` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==4.14.2` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| meta_analyse | `requirements.lock` | project | `==4.15.1` | DIFFERS (owner/CI decision) |

### asyncpg: цель `0.32.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==0.32.0` | OK |
| bybit-cluster-grid | `requirements.txt` | project | `>=0.30` | RANGE-ALLOWS-TARGET |
| strattester | `pyproject.toml[optional[ingestion]]` | project | `>=0.29,<1` | RANGE-ALLOWS-TARGET |

### certifi: цель `2026.10.23`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==2026.10.19` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==2026.10.19` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/intelligence/research-identity/requirements-linux.lock` | evidence/docs copy (hashes) | `==2026.10.23` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-windows.lock` | evidence/docs copy (hashes) | `==2026.10.23` | OK |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==2026.7.22` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `tests/control_mux/requirements.lock` | test (hashes) | `==2026.10.23` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==2026.10.19` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==2026.10.19` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| meta_analyse | `requirements.lock` | project | `==2026.7.22` | DIFFERS (owner/CI decision) |

### colorama: цель `0.4.6`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==0.4.6 ; sys_platform == "win32"` | OK |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==0.4.6` | OK |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==0.4.6 ; sys_platform == "win32"` | OK |
| Terminan | `requirements-test.lock` | project (hashes) | `==0.4.6` | OK |
| meta_analyse | `requirements.lock` | project | `==0.4.6 ; sys_platform == 'win32'` | OK |

### fastapi: цель `0.162.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==0.162.0` | OK |
| bybit-cluster-grid | `requirements.txt` | project | `>=0.115` | RANGE-ALLOWS-TARGET |

### h11: цель `0.16.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==0.16.0` | OK |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==0.16.0` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-linux.lock` | evidence/docs copy (hashes) | `==0.16.0` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-windows.lock` | evidence/docs copy (hashes) | `==0.16.0` | OK |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==0.16.0` | OK |
| unified-system | `tests/control_mux/requirements.lock` | test (hashes) | `==0.16.0` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==0.16.0` | OK |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==0.16.0` | OK |
| meta_analyse | `requirements.lock` | project | `==0.16.0` | OK |

### httpcore: цель `1.0.9`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==1.0.9` | OK |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==1.0.9` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-linux.lock` | evidence/docs copy (hashes) | `==1.0.9` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-windows.lock` | evidence/docs copy (hashes) | `==1.0.9` | OK |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==1.0.9` | OK |
| unified-system | `tests/control_mux/requirements.lock` | test (hashes) | `==1.0.9` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==1.0.9` | OK |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==1.0.9` | OK |
| meta_analyse | `requirements.lock` | project | `==1.0.9` | OK |

### httpx: цель `0.28.1`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==0.28.1` | OK |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==0.28.1` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-linux.lock` | evidence/docs copy (hashes) | `==0.28.1` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-windows.lock` | evidence/docs copy (hashes) | `==0.28.1` | OK |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==0.28.1` | OK |
| unified-system | `tests/control_mux/requirements.lock` | test (hashes) | `==0.28.1` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==0.28.1` | OK |
| bybit-cluster-grid | `requirements.txt` | project | `>=0.27` | RANGE-ALLOWS-TARGET |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==0.28.1` | OK |
| meta_analyse | `pyproject.toml[project.dependencies]` | project | `>=0.27,<1` | RANGE-ALLOWS-TARGET |
| meta_analyse | `requirements.lock` | project | `==0.28.1` | OK |

### hypothesis: цель `6.170.6`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==6.170.6` | OK |
| meta_analyse | `pyproject.toml[optional[test]]` | project | `==6.170.6` | OK |
| meta_analyse | `requirements-identity-synthetic.txt` | project | `==6.170.6` | OK |
| meta_analyse | `requirements.lock` | project | `==6.170.6` | OK |

### idna: цель `3.20`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==3.15` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==3.15` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/intelligence/research-identity/requirements-linux.lock` | evidence/docs copy (hashes) | `==3.20` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-windows.lock` | evidence/docs copy (hashes) | `==3.20` | OK |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==3.20` | OK |
| unified-system | `tests/control_mux/requirements.lock` | test (hashes) | `==3.20` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==3.15` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==3.15` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| meta_analyse | `requirements.lock` | project | `==3.20` | OK |

### iniconfig: цель `2.3.1`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==2.3.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==2.3.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==2.3.1` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==2.3.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==2.3.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| Terminan | `requirements-test.lock` | project (hashes) | `==2.3.1` | OK |
| meta_analyse | `requirements.lock` | project | `==2.3.1` | OK |

### jsonschema: цель `4.25.1`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/intelligence/research-identity/requirements-linux.lock` | evidence/docs copy (hashes) | `==4.25.1` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-windows.lock` | evidence/docs copy (hashes) | `==4.25.1` | OK |
| unified-system | `tests/control_mux/requirements.lock` | test (hashes) | `==4.25.1` | OK |
| bybit-cluster-grid | `.github/workflows/preflight.yml:63` | workflow | `==4.23.0` | DIFFERS (owner/CI decision) |

### numpy: цель `2.5.4`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==2.5.4` | OK |
| bybit-cluster-grid | `requirements-ml.txt` | project | `>=2.0,<3` | RANGE-ALLOWS-TARGET |

### packaging: цель `26.3`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==26.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==26.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==26.3` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==26.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==26.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| Terminan | `requirements-test.lock` | project (hashes) | `==26.3` | OK |
| meta_analyse | `requirements.lock` | project | `==26.3` | OK |

### pluggy: цель `1.7.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==1.6.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==1.6.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==1.7.0` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==1.6.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==1.6.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| Terminan | `requirements-test.lock` | project (hashes) | `==1.7.0` | OK |
| meta_analyse | `requirements.lock` | project | `==1.7.0` | OK |

### psutil: цель `7.2.2`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==7.2.2` | OK |
| bybit-cluster-grid | `requirements.txt` | project | `>=6.0` | RANGE-ALLOWS-TARGET |
| strattester | `pyproject.toml[optional[legacy-test]]` | project | `>=5.9,<8` | RANGE-ALLOWS-TARGET |

### psycopg: цель `3.3.6`
Owner/F2 target; highest exact pin in project locks (unified-system Windows lock, meta lock, grid requirements.txt).

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==3.3.6` | OK |
| bybit-cluster-grid | `.github/workflows/history-integration.yml:73` | workflow | `==3.3.2` | CHANGED-IN-PR: grid PR #297 (claude/f2-deps-grid-20261125) |
| bybit-cluster-grid | `pyproject.toml[project.dependencies]` | project | `==3.3.6` | OK |
| bybit-cluster-grid | `requirements.txt` | project | `==3.3.6` | OK |
| strattester | `.github/workflows/market-data-pure.yml:62` | workflow | `>=3.2,<4` | CHANGED-IN-PR: strattester PR #122 (claude/f2-deps-strattester-20261125) |
| strattester | `pyproject.toml[project.dependencies]` | project | `>=3.2,<4` | CHANGED-IN-PR: strattester PR #122 (claude/f2-deps-strattester-20261125) |
| meta_analyse | `pyproject.toml[project.dependencies]` | project | `>=3.2,<4` | RANGE-ALLOWS-TARGET |
| meta_analyse | `requirements.lock` | project | `==3.3.6` | OK |

### psycopg-binary: цель `3.3.6`
Follows psycopg 3.3.6.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==3.3.6` | OK |
| meta_analyse | `requirements.lock` | project | `==3.3.6 ; implementation_name != 'pypy'` | OK |

### pydantic: цель `2.14.2`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==2.14.2` | OK |
| bybit-cluster-grid | `requirements.txt` | project | `>=2.8` | RANGE-ALLOWS-TARGET |

### pydantic-settings: цель `2.16.2`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==2.16.2` | OK |
| bybit-cluster-grid | `requirements.txt` | project | `>=2.4` | RANGE-ALLOWS-TARGET |

### pygments: цель `2.21.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==2.20.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==2.20.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==2.21.0` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==2.20.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==2.20.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| Terminan | `requirements-test.lock` | project (hashes) | `==2.21.0` | OK |
| meta_analyse | `requirements.lock` | project | `==2.21.0` | OK |

### pyside6: цель `6.12.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==6.12.0` | OK |
| Terminan | `pyproject.toml[optional[desktop]]` | project | `>=6.7,<7` | RANGE-ALLOWS-TARGET |
| meta_analyse | `pyproject.toml[project.dependencies]` | project | `>=6.8,<7` | RANGE-ALLOWS-TARGET |
| meta_analyse | `requirements.lock` | project | `==6.12.0` | OK |

### pyside6-addons: цель `6.12.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==6.12.0` | OK |
| meta_analyse | `requirements.lock` | project | `==6.12.0` | OK |

### pyside6-essentials: цель `6.12.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==6.12.0` | OK |
| meta_analyse | `requirements.lock` | project | `==6.12.0` | OK |

### pyside6-pdf: цель `6.12.0.140`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==6.12.0.140` | OK |
| meta_analyse | `requirements.lock` | project | `==6.12.0.140` | OK |

### pyside6-webengine: цель `6.12.0.140`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==6.12.0.140` | OK |
| meta_analyse | `requirements.lock` | project | `==6.12.0.140` | OK |

### pytest: цель `9.1.1`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==9.0.3` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==9.0.3` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==9.1.1` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==9.0.3` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==9.0.3` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| strattester | `.github/workflows/market-data-pure.yml:62` | workflow | `==8.3.5` | DIFFERS (owner/CI decision) |
| strattester | `pyproject.toml[optional[test]]` | project | `==8.3.5` | DIFFERS (owner/CI decision) |
| Terminan | `requirements-test.lock` | project (hashes) | `==9.1.1` | OK |
| meta_analyse | `pyproject.toml[optional[test]]` | project | `>=8,<10` | RANGE-ALLOWS-TARGET |
| meta_analyse | `requirements.lock` | project | `==9.1.1` | OK |

### pytest-asyncio: цель `1.4.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==1.4.0` | OK |
| strattester | `.github/workflows/market-data-pure.yml:62` | workflow | `==0.26.0` | DIFFERS (owner/CI decision) |
| strattester | `pyproject.toml[optional[test]]` | project | `==0.26.0` | DIFFERS (owner/CI decision) |
| Terminan | `requirements-test.lock` | project (hashes) | `==1.4.0` | OK |
| meta_analyse | `pyproject.toml[optional[test]]` | project | `>=0.24,<2` | RANGE-ALLOWS-TARGET |
| meta_analyse | `requirements.lock` | project | `==1.4.0` | OK |

### python-dotenv: цель `1.2.4`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==1.2.4` | OK |
| bybit-cluster-grid | `requirements.txt` | project | `>=1.0` | RANGE-ALLOWS-TARGET |

### requests: цель `2.34.2`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==2.34.2` | OK |
| strattester | `pyproject.toml[optional[legacy-test]]` | project | `>=2.31,<3` | RANGE-ALLOWS-TARGET |

### setuptools: цель `—`
Build backend constraint (pyproject [build-system]) vs runtime lock pin; not a runtime dependency, not unified here.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==84.2.1` | N/A |
| bybit-cluster-grid | `pyproject.toml[build-system]` | project | `>=75,<83` | N/A |
| strattester | `.github/workflows/market-data-pure.yml:62` | workflow | `>=75,<83` | N/A |
| strattester | `pyproject.toml[build-system]` | project | `>=75,<83` | N/A |
| Terminan | `pyproject.toml[build-system]` | project | `>=75,<83` | N/A |
| math | `pyproject.toml[build-system]` | project | `>=75,<83` | N/A |
| meta_analyse | `pyproject.toml[build-system]` | project | `>=70` | N/A |

### shiboken6: цель `6.12.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==6.12.0` | OK |
| meta_analyse | `requirements.lock` | project | `==6.12.0` | OK |

### sortedcontainers: цель `2.4.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==2.4.0` | OK |
| meta_analyse | `requirements-identity-synthetic.txt` | project | `==2.4.0` | OK |
| meta_analyse | `requirements.lock` | project | `==2.4.0` | OK |

### typing-extensions: цель `4.16.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `docs/ci/operator-command/requirements-linux.lock` | live (CI: operator-command-contracts.yml; F registry said evidence copy) (hashes) | `==4.15.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==4.15.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `docs/intelligence/research-identity/requirements-linux.lock` | evidence/docs copy (hashes) | `==4.16.0` | OK |
| unified-system | `docs/intelligence/research-identity/requirements-windows.lock` | evidence/docs copy (hashes) | `==4.16.0` | OK |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==4.16.0` | OK |
| unified-system | `tests/control_mux/requirements.lock` | test (hashes) | `==4.16.0` | OK |
| bybit-cluster-grid | `lab/consul/requirements-three-linux.lock` | project (hashes) | `==4.15.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| bybit-cluster-grid | `scripts/agent2-event-v3/requirements.lock` | project (hashes) | `==4.15.0` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| Terminan | `requirements-test.lock` | project (hashes) | `==4.16.0` | OK |
| meta_analyse | `requirements.lock` | project | `==4.16.0 ; python_full_version < '3.15'` | OK |

### tzdata: цель `2026.6`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `.github/workflows/agent5-components.yml:32` | workflow | `==2026.6` | OK |
| unified-system | `docs/ci/requirements-unittest.lock` | live (CI: installer-security.yml, lifecycle-evidence.yml, owner-boundary.yml, preparation-integrity.yml, tests.yml; F registry said evidence copy) (hashes) | `==2025.2` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==2026.5` | BLOCKED-HASH-LOCK (regenerate with network: CI/owner) |
| unified-system | `release/requirements-integration.lock` | live (CI: final-integration.yml; F registry said evidence copy) (hashes) | `==2026.6` | OK |
| meta_analyse | `requirements.lock` | project | `==2026.5 ; sys_platform == 'win32'` | DIFFERS (owner/CI decision) |

### uvicorn: цель `0.54.0`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==0.54.0` | OK |
| bybit-cluster-grid | `requirements.txt` | project | `>=0.30` | RANGE-ALLOWS-TARGET |

### websockets: цель `15.0.1`
Highest exact pin among live (project/test/workflow) manifests.

| repo | file | role | spec | status |
|---|---|---|---|---|
| unified-system | `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock` | project (hashes) | `==15.0.1` | OK |
| bybit-cluster-grid | `requirements.txt` | project | `>=13.0` | RANGE-ALLOWS-TARGET |
| strattester | `.github/workflows/market-data-pure.yml:62` | workflow | `>=15,<16` | RANGE-ALLOWS-TARGET |
| strattester | `pyproject.toml[project.dependencies]` | project | `>=15,<16` | RANGE-ALLOWS-TARGET |
| meta_analyse | `pyproject.toml[project.dependencies]` | project | `>=13,<16` | RANGE-ALLOWS-TARGET |
| meta_analyse | `requirements.lock` | project | `==15.0.1` | OK |

### wheel: цель `—`
Build backend constraint (pyproject [build-system]) vs runtime lock pin; not a runtime dependency, not unified here.

| repo | file | role | spec | status |
|---|---|---|---|---|
| bybit-cluster-grid | `pyproject.toml[build-system]` | project | `` | N/A |
| strattester | `pyproject.toml[build-system]` | project | `` | N/A |
| Terminan | `pyproject.toml[build-system]` | project | `` | N/A |
| meta_analyse | `pyproject.toml[build-system]` | project | `` | N/A |

## Изменения после кандидатов
- bybit-cluster-grid claude/b1-market-data-relocation-20261125 (bf29f81) replaced pyproject.toml with strattester@3850995 bytes: psycopg[binary]>=3.2,<4 (range, allows 3.3.6) and added .github/workflows/market-data-pure.yml with psycopg[binary]>=3.2,<4, pytest==8.3.5, pytest-asyncio==0.26.0. Kept unchanged to preserve the B1 byte-identity invariant.

## PR в рамках F2 (минимальные: только пины psycopg)
- bybit-cluster-grid #297 (`claude/f2-deps-grid-20261125`, ветка поверх B1 #296): `.github/workflows/history-integration.yml:73`, `psycopg[binary]==3.3.2` → `==3.3.6`.
- strattester #122 (`claude/f2-deps-strattester-20261125`, база 3850995): в `pyproject.toml` и `.github/workflows/market-data-pure.yml:62` `psycopg[binary]>=3.2,<4` → `==3.3.6`.
- unified-system и meta_analyse: psycopg уже 3.3.6, изменений нет. В meta_analyse `pyproject.toml` задан диапазон `>=3.2,<4`, но `requirements.lock` закрепляет 3.3.6. Установка в CI и в `install.ps1` всегда идёт с `-c requirements.lock` / `--constraint`.
- Terminan и math: psycopg не используют.

## Что не сделано и почему
- **Lock-файлы с хешами:** grid `lab/consul/requirements-three-linux.lock` и `scripts/agent2-event-v3/requirements.lock` (pytest 9.0.3, certifi 2026.10.19, anyio 4.14.2 и др.); unified-system `tests/control_mux/requirements.lock`, `integration/windows-candidate/requirements-cp312-win_amd64-cpu.lock`, а также `docs/ci/requirements-unittest.lock`, `docs/ci/operator-command/requirements-linux.lock` и `release/requirements-integration.lock`. Реестр F пометил последние три как evidence-копии, но на них ссылаются workflow (`tests.yml`, `installer-security.yml`, `operator-command-contracts.yml`, `final-integration.yml` и др.), значит, это живые lock-файлы. Привести их к цели можно только регенерацией с доступом к PyPI: `uv pip compile --generate-hashes` или `pip-compile --generate-hashes`. В песочнице PyPI недоступен (DNS `pypi.org` не резолвится), поэтому пины без хешей мы не правим: это сломало бы `--require-hashes`. Оставлено CI или владельцу.
- **strattester:** `pytest==8.3.5` и `pytest-asyncio==0.26.0` при цели 9.1.1 / 1.4.0. Это мажорные обновления, а pytest-asyncio 1.x несовместим по API фикстур event loop. Нужно решение владельца и отдельный прогон CI. Strattester выводится из рантайма.
- **grid:** в `requirements.txt` открытые диапазоны без lock (aiohttp, asyncpg, fastapi, pydantic, uvicorn и др.). Для детерминизма нужен lock с хешами, а его нельзя сгенерировать без сети.
- **unified-system:** `.github/workflows/agent5-components.yml:32` ставит `tzdata==2026.6`, а Windows-lock закрепляет 2026.5. Цель 2026.6 (максимальный живой пин). Workflow-файлы unified-system в F2 меняем только в строках `uses:`, а Windows-lock содержит хеши. Оставлено владельцу.
- **Evidence-копии** — `docs/**` и `release/**`, на которые не ссылается ни один workflow. Это исторические записи, их не правим.

