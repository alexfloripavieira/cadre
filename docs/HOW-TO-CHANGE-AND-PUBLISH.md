# How To Change And Publish

Este é o fluxo operacional padrão para mudar e publicar o `claude-tech-squad` sem mexer manualmente nos metadados de release.

## Regra Principal

Você altera código, prompts, skills, agentes e docs normalmente.

Você **não** edita manualmente estes arquivos para uma release rotineira:

- `CHANGELOG.md`
- `.claude-plugin/marketplace.json`
- `plugins/claude-tech-squad/.claude-plugin/plugin.json`
- `docs/MANUAL.md`

Esses arquivos são gerados pela pipeline de publish.

## Fluxo Padrão

### 1. Crie uma branch

Exemplos:

```bash
git switch -c feat/nova-skill
git switch -c fix/retry-reviewer
```

### 2. Faça a mudança

Edite o que precisar:

- agentes
- skills
- workflows
- scripts
- fixtures
- documentação visível ao operador

Atualize `README.md` quando a mudança alterar a forma de usar ou operar o plugin.

### 3. Valide localmente

```bash
bash scripts/validate.sh
bash scripts/smoke-test.sh
```

Se a mudança for sensível em workflow, orquestração ou release, rode também:

```bash
bash scripts/dogfood.sh
bash scripts/dogfood-report.sh --schema-only
```

### 4. Faça commit em formato convencional

A release automática depende disso.

Use:

- `feat: ...` para release `minor`
- `fix: ...` para release `patch`
- `docs: ...` para release `patch`
- `refactor: ...` para release `patch`
- `chore: ...` para release `patch`
- `type!: ...` ou `BREAKING CHANGE` para release `major`

Exemplos:

```bash
git add .
git commit -m "feat: automate release metadata generation"
git commit -m "fix: harden publish workflow resume behavior"
git commit -m "docs: clarify teammate mode release flow"
```

### 5. Envie a branch e abra o PR

Se você usa squash merge, o título final do PR também precisa estar em formato convencional, porque ele vira o commit que cai em `main`.

### 6. Espere o CI passar

O workflow `validate` roda automaticamente.

### 7. Faça merge em `main`

Depois disso, o restante é automático.

## O Que Acontece Depois Do Merge

O workflow `publish`:

1. Lê os commits desde a última tag
2. Calcula a próxima versão semver
3. Gera a nova entrada do `CHANGELOG.md`
4. Atualiza `marketplace.json`
5. Atualiza `plugin.json`
6. Atualiza `docs/MANUAL.md`
7. Roda `bash scripts/smoke-test.sh`
8. Faz o commit `chore: prepare release vX.Y.Z`
9. Cria a tag `vX.Y.Z`
10. Cria ou atualiza a GitHub Release

## O Que Verificar

Depois do merge, confira:

- GitHub Actions: workflow `publish`
- GitHub Releases: nova release criada
- tag nova publicada
- `CHANGELOG.md` com a entrada da versão
- `marketplace.json`, `plugin.json` e `MANUAL.md` alinhados

## Fluxo Curto

```bash
git switch -c feat/minha-mudanca
# faz a mudança
bash scripts/validate.sh
bash scripts/smoke-test.sh
git add .
git commit -m "feat: minha mudança"
git push
# abre PR
# merge em main
# publish automático
```

## Fluxo de Emergência

### Caminho 1 — Workflow disponível, mas a pipeline não disparou

Se a automação está disponível mas o workflow não foi acionado, use o script de fallback local:

```bash
./scripts/release.sh
```

Esse script usa o mesmo gerador de metadados da pipeline oficial e dispara o workflow `publish`.

---

### Caminho 2 — Release de emergência (GitHub Actions indisponível)

Use este caminho **somente** quando o GitHub Actions estiver completamente indisponível e uma release for urgente. Neste caso, os metadados de release precisam ser atualizados manualmente e a GitHub Release criada via CLI.

> **Atenção:** Releases manuais quebram o histórico de automação. Após concluir, você deve criar um commit de sincronização para que o próximo ciclo automatizado funcione corretamente (veja o Passo 8).

#### Passo 1 — Determine a próxima versão

Execute o gerador de metadados em modo de prévia para calcular a versão:

```bash
bash scripts/prepare-release-metadata.sh
```

Anote a versão gerada (ex: `5.30.0`). Se o script falhar, calcule manualmente com base nos commits desde a última tag:
- `feat:` → bump minor (`5.29.0` → `5.30.0`)
- `fix:`, `docs:`, `chore:` → bump patch (`5.29.0` → `5.29.1`)
- `BREAKING CHANGE` ou `type!:` → bump major

#### Passo 2 — Atualize os 3 arquivos de versão

Edite manualmente estes 3 arquivos com o número de versão correto (ex: `5.30.0`):

1. `.claude-plugin/marketplace.json` — campo `plugins[0].version`
2. `plugins/claude-tech-squad/.claude-plugin/plugin.json` — campo `version`
3. `docs/MANUAL.md` — campo `**Versão:** X.Y.Z`

> **Não edite** `CHANGELOG.md` aqui — ele será tratado no Passo 3.

#### Passo 3 — Adicione a entrada no CHANGELOG.md

Abra `CHANGELOG.md` e adicione uma nova entrada no topo (após o `## [Unreleased]` se existir):

```markdown
## [5.30.0] — 2026-04-05

### Added
- Resumo das mudanças...

### Fixed
- ...
```

Use a data atual no formato `YYYY-MM-DD`.

#### Passo 4 — Valide o repositório

```bash
bash scripts/validate.sh
bash scripts/smoke-test.sh
```

Ambos devem passar com `exit_code=0` antes de continuar.

#### Passo 5 — Verifique o alinhamento de versão

```bash
bash scripts/verify-release.sh 5.30.0
```

**Output esperado quando o release está correto:**

```
claude-tech-squad release metadata passed (5.30.0)
```

Se o output contiver "does not match" ou "is missing", corrija os arquivos apontados antes de prosseguir.

#### Passo 6 — Faça commit e crie a tag git manualmente

```bash
git add \
  .claude-plugin/marketplace.json \
  plugins/claude-tech-squad/.claude-plugin/plugin.json \
  docs/MANUAL.md \
  CHANGELOG.md

git commit -m "chore: prepare release v5.30.0"
git push origin main

git tag -a "v5.30.0" -m "claude-tech-squad v5.30.0"
git push origin "v5.30.0"
```

#### Passo 7 — Crie a GitHub Release via CLI

```bash
# Extraia as notas do CHANGELOG
awk '/^\#\# \[5\.30\.0\]/{found=1; next} found && /^\#\# \[/{exit} found{print}' CHANGELOG.md > /tmp/release-notes.md

# Build do bundle
bash scripts/build-release-bundle.sh 5.30.0

# Crie a release
gh release create "v5.30.0" \
  --title "v5.30.0" \
  --notes-file /tmp/release-notes.md \
  dist/claude-tech-squad-5.30.0.tar.gz \
  dist/claude-tech-squad-5.30.0.sha256
```

#### Passo 8 — Commit de sincronização (obrigatório)

Após a release manual, a pipeline automatizada pode tentar criar a mesma versão novamente na próxima execução. Para evitar isso, faça um commit vazio de sincronização:

```bash
git commit --allow-empty -m "chore: sync after manual release v5.30.0 [skip-release]"
git push origin main
```

O commit `[skip-release]` sinaliza para a pipeline que não é necessário calcular uma nova versão. Verifique que `prepare-release-metadata.sh` reconhece esse padrão — se não reconhecer, monitore a próxima execução do workflow `publish` para garantir que não tente criar uma versão duplicada.

#### Verificação final

Após concluir todos os passos, confirme:

- [ ] GitHub Releases: release `v5.30.0` existe com as notas corretas
- [ ] Tag `v5.30.0` visível em `git tag --list`
- [ ] `marketplace.json`, `plugin.json` e `MANUAL.md` alinhados na versão
- [ ] `bash scripts/verify-release.sh 5.30.0` retorna `claude-tech-squad release metadata passed (5.30.0)`
