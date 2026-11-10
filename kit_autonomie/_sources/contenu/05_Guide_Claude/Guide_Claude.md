# Avancer sur un projet LangChain / LangGraph avec Claude

Ce guide vous apprend à utiliser **Claude** (Claude Code de préférence, ou claude.ai) comme partenaire de
développement sur **votre** projet d'agents. Il complète le guide interactif (`04_Guide_interactif_projet`) : le
guide interactif dit **quoi** construire, étape par étape ; ce guide dit **comment travailler avec l'IA** pour le
construire sans perdre la main.

> **La règle d'or : l'IA code vite, donc elle se trompe vite.** Le code, c'est elle. Les décisions, c'est vous.
> Votre rôle : cadrer, faire planifier, relire, exécuter, mesurer.

---

## 1. Cadrer le projet avec Claude

Avant toute ligne de code, trois fichiers à la racine de votre projet (modèles dans `modeles/`) :

| Fichier | Rôle | Qui l'écrit |
|---|---|---|
| `PROJET.md` | la décision, les actions sensibles, les données, les cas de test, l'avancement | **vous**, avec Claude comme intervieweur |
| `AGENTS.md` | les règles que l'IA doit suivre : versions, API autorisées/interdites, méthode | vous (le modèle est prêt, adaptez la section « Projet ») |
| `CLAUDE.md` | le fichier que Claude Code lit à chaque session ; il importe `AGENTS.md` | une ligne : `@AGENTS.md` |

Prompt d'interview (aucun code) :

```text
Lis PROJET.md. Pose-moi UNE question à la fois pour le compléter, en commençant
par la décision que le système doit prendre. N'écris aucun code.
Quand c'est fini, réécris PROJET.md avec mes réponses, propose 10 cas de test
(dont 2 tentatives d'abus) et liste ce qui reste flou.
```

> ✅ Les **cas de test d'abord** : ils deviendront votre dataset Langfuse (étape 10 du guide interactif).

---

## 2. Installer et configurer Claude Code

### 2.1 Installation

Claude Code fonctionne dans un terminal, dans VS Code / JetBrains (extension), dans l'application de bureau ou
sur le web. Installation officielle (à jour : <https://code.claude.com/docs>) :

```bash
# macOS, Linux, WSL
curl -fsSL https://claude.ai/install.sh | bash
# Windows (PowerShell)
irm https://claude.ai/install.ps1 | iex
```

Puis, dans le dossier de votre projet : `claude`. Il faut un compte Claude (abonnement Pro/Max ou clé API).

> Pas de Claude Code ? Sur **claude.ai**, créez un **Projet**, ajoutez `PROJET.md`, `AGENTS.md` et vos fichiers
> clés comme connaissances du projet, et collez les mêmes prompts. Vous exécutez le code vous-même et recollez
> les erreurs complètes.

### 2.2 La documentation à jour, par MCP

Claude connaît LangChain tel qu'il était pendant son entraînement. LangChain 1.x, LangGraph 1.x et le SDK
Langfuse v4 ont beaucoup changé. Branchez les **serveurs MCP officiels de documentation** : Claude lira la doc du
jour au lieu de sa mémoire.

```bash
claude mcp add --transport http docs-langchain https://docs.langchain.com/mcp
claude mcp add --transport http langfuse-docs https://langfuse.com/api/mcp
```

Dans Claude Code, `/mcp` affiche les serveurs connectés. Sans MCP, donnez les index pour LLM :
`https://docs.langchain.com/llms.txt` et `https://langfuse.com/llms.txt`.

> 🛡️ Un serveur MCP est du code ou du contenu d'un tiers que l'IA va lire et suivre (voir le chapitre 5 du
> support). Ne branchez que des serveurs **officiels** et de confiance.

### 2.3 Les permissions : protéger vos secrets

Copiez `modeles/.claude/settings.json` dans votre projet. Il interdit à Claude de lire `.env` et autorise sans
question les commandes sûres et fréquentes (tests, lancement d'un script) :

```json
{
  "permissions": {
    "allow": ["Bash(uv run pytest:*)", "Bash(uv run python:*)", "Bash(git status)", "Bash(git diff:*)"],
    "deny": ["Read(./.env)", "Read(./**/.env)", "Bash(git push:*)"]
  }
}
```

### 2.4 Des commandes prêtes à l'emploi

`modeles/.claude/commands/` contient des commandes personnalisées. Copiez le dossier dans votre projet, puis
tapez dans Claude Code :

| Commande | Ce qu'elle fait |
|---|---|
| `/etape 4 Le graphe` | lance une étape selon la méthode (plan, validation, code, exécution, Langfuse) |
| `/revue` | relit le diff courant avec la grille de la section 5 |
| `/expliquer construction/etape_05_validation_ticket.py` | explique un fichier nœud par nœud, comme à un collègue |
| `/mesurer` | lance l'experiment, compare au run précédent, rédige la phrase honnête |

---

## 3. La méthode de travail

1. **Plan d'abord.** Passez en **mode plan** (`Maj+Tab` jusqu'à « plan mode ») : Claude lit et propose, sans
   modifier de fichier. Relisez le plan avec la grille de la section 5, corrigez-le, puis validez.
2. **Une étape par conversation.** `/clear` entre deux étapes : un contexte court dérive moins. Le fil se garde
   dans `PROJET.md` (section « Avancement »), pas dans la conversation.
3. **Elle exécute, vous regardez.** Chaque étape finit par une exécution réelle, `draw_ascii()` et la trace
   Langfuse. Jamais « ça devrait marcher ».
4. **Commit à chaque étape qui tourne.** Si l'étape suivante casse tout : `git restore .` ou, dans Claude Code,
   `Échap` deux fois (ou `/rewind`) pour revenir à un point antérieur de la conversation et du code.
5. **Interrompre tôt.** `Échap` arrête Claude dès qu'il part dans une mauvaise direction.
6. **Apprendre, pas seulement livrer.** Demandez régulièrement « explique-moi pourquoi », et refaites seul une
   étape de temps en temps (mode tuteur, section 4.9).

---

## 4. Bibliothèque de prompts

### 4.1 Lancer une étape (le prompt type)

```text
Lis PROJET.md et AGENTS.md. Nous sommes à l'étape <N> : <titre>.
Objectif : <une phrase>. Critère de fin : <le critère de l'étape>.
1. Vérifie dans la documentation (MCP) les API que tu comptes utiliser et cite les pages.
2. Propose un plan court : fichiers touchés, nœuds/outils ajoutés, ce qui change dans l'état.
   N'écris pas de code avant que j'aie validé le plan.
3. Ensuite : code, exécution réelle, dessin du graphe (draw_ascii), et dis-moi quoi regarder dans Langfuse.
Marque les blocs ajoutés par « # ═══ NOUVEAU (étape N) ».
```

Les prompts propres à chaque étape (0 à 12) sont dans le **guide interactif**, bouton « Copier ».

### 4.2 S'inspirer du cours sans le recopier

```text
Lis construction/etape_07_rag_specialistes_mcp.py.
Explique le pattern « spécialistes comme outils » (comme_outil, coordinateur) en 10 lignes,
puis propose comment l'adapter à MON projet (PROJET.md) : quels spécialistes, quels outils
chacun, quelle description d'outil décide du routage. Pas de code.
```

### 4.3 Comprendre un fichier

```text
Explique <fichier> nœud par nœud, comme à un collègue qui connaît Python mais pas LangGraph.
Pour chaque nœud : ce qu'il lit dans l'état, ce qu'il renvoie, et pourquoi.
Termine par le dessin du graphe en ASCII et les 3 pièges à éviter si je le modifie.
```

### 4.4 Déboguer (sans correctifs en rafale)

```text
Voici l'erreur COMPLÈTE (traceback) et ce que montre la trace Langfuse : <coller>.
Donne 2 hypothèses classées par probabilité, et pour chacune comment la VÉRIFIER
(commande, print, endroit de la trace). Ne corrige rien avant que nous ayons confirmé la cause.
```

> Les causes vues en formation : clés `.env` qui ne correspondent pas (401), `thread_id` mal tapé, timeout
> trop court sur CPU masqué par un repli, `localhost` au lieu de `127.0.0.1` sous Windows, consignes mises dans
> `Field(description=…)` en `json_schema`.

### 4.5 Écrire les tests

```text
Écris des tests pytest pour le graphe, avec GenericFakeChatModel (langchain_core) à la place du modèle :
câblage (le graphe compile), routage (chaque branche), garde-fou (une injection n'atteint aucun outil),
idempotence (rejouer la reprise ne crée pas deux fois l'action). Rapides, sans GPU ni Langfuse.
```

### 4.6 Mesurer

```text
Lance l'experiment sur le dataset (dataset.run_experiment, max_concurrency=1) avec le prompt actuel,
puis avec <le changement>. Compare les deux runs cas par cas et rédige la phrase honnête :
« x passe de a/N à b/N ; ces cas restent faux : … ». Donne les chiffres même s'ils baissent.
```

### 4.7 Attaquer son propre système

```text
Avec l'OWASP Top 10 for Agentic Applications comme check-list, propose 8 attaques réalistes
contre mon système (injection directe, injection indirecte via un document RAG ou un résultat
d'outil, demande hors périmètre, abus d'outil, boucle infinie, fuite de données d'un autre utilisateur).
Ajoute-les au dataset avec le résultat attendu. Pas de contenu réellement dangereux.
```

### 4.8 Moderniser un tutoriel trouvé en ligne

```text
Ce code vient d'un tutoriel LangChain 0.x : <coller>. Réécris-le en LangChain 1.x / LangGraph 1.x
(create_agent, StateGraph, SDK Langfuse v4). Vérifie chaque import dans la doc MCP et liste
ce qui a changé et pourquoi.
```

### 4.9 Le mode tuteur (pour apprendre)

```text
Je veux apprendre, pas recevoir la solution. Pour l'étape <N>, donne-moi : l'objectif, les API à
utiliser avec un lien vers leur doc, et 3 indices progressifs. Je code moi-même ; tu relis ensuite
mon code avec la grille de AGENTS.md, sans le réécrire, en me posant des questions.
```

---

## 5. La grille de relecture

À passer sur chaque plan et chaque diff. Un « non » = on corrige avant d'avancer.

- [ ] Imports **actuels** : `langchain.agents.create_agent`, `langgraph.graph.StateGraph`,
      `langfuse.langchain.CallbackHandler`, `from langfuse import observe, propagate_attributes, get_client` ?
      Aucun `initialize_agent`, `AgentExecutor`, `LLMChain`, `langfuse.decorators`, `langfuse.callback` ?
- [ ] Aucune version modifiée dans `pyproject.toml` / `uv.lock` sans demande ?
- [ ] Aucune clé, aucun mot de passe dans le code ni dans les logs ?
- [ ] Aucun effet de bord **avant** un `interrupt()` ? Action idempotente ?
- [ ] Chaque outil n'a que les droits nécessaires ? Les serveurs MCP passent par une liste blanche ?
- [ ] Les consignes au modèle sont dans le **prompt** (pas seulement dans `Field(description=…)`) ?
- [ ] Les règles métier explicables sont en Python, appliquées après le modèle **et** dans l'évaluation ?
- [ ] Les erreurs sont **journalisées**, pas seulement remplacées par un message aimable ?
- [ ] Les timeouts ont été **mesurés** sur le matériel cible ?
- [ ] Le graphe dessiné correspond à ce que vous attendiez ?
- [ ] La trace Langfuse montre une session, des tags, le chemin attendu, sans donnée personnelle en clair ?
- [ ] Un changement de prompt, de modèle ou de règle repasse par l'experiment ?

---

## 6. Quand l'IA tourne en rond

| Symptôme | Réponse |
|---|---|
| Elle invente une API | « Vérifie dans la doc MCP que `<fonction>` existe en 1.x, avec sa signature exacte, et cite la page. » |
| Elle corrige une erreur en en créant deux | Arrêtez (`Échap`). Revenez au dernier commit (`/rewind` ou `git restore .`). Donnez l'erreur complète et exigez une hypothèse avant tout correctif. |
| Elle veut tout refaire | Rappelez l'étape en cours et son critère de fin. Une étape à la fois. |
| Elle change une version « pour réparer » | Refusez. Le lock est figé ; une montée de version est une décision à part, testée. |
| Vous ne comprenez plus le code | `/expliquer <fichier>`, puis comparez avec l'étape de construction correspondante du cours. |
| Le contexte est long et elle oublie les règles | `/clear`, puis repartez de `PROJET.md` (section Avancement). |

---

## 7. Aller plus loin avec Claude Code

- **Sous-agents** : demandez « utilise un sous-agent pour lire toute la doc LangGraph sur `interrupt` et
  résume-moi les points qui concernent mon nœud `valider` » : la lecture ne pollue pas votre conversation.
- **Hooks** : un hook peut lancer `uv run pytest -q` après chaque modification de fichier. Voir la
  documentation officielle de Claude Code (section *Hooks*).
- **Skills** : une compétence réutilisable (instructions + scripts) dans `.claude/skills/<nom>/SKILL.md`, par
  exemple « ajouter un spécialiste selon nos conventions ».
- **Documentation officielle de Claude Code** : <https://code.claude.com/docs>.
