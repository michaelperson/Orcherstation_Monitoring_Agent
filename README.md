# Orchestration d'agents IA & Monitoring — HelpDesk-Ops

Formation BStorm : LangGraph + Langfuse, stack 100 % locale (vLLM sur le GPU de la salle, Qdrant, Langfuse auto-hébergé ; Ollama en repli sur un poste sans GPU).

## Installation en salle (Ubuntu 24.04, GPU NVIDIA)

```bash
git clone https://github.com/michaelperson/Orcherstation_Monitoring_Agent.git ~/helpdesk-ops
cd ~/helpdesk-ops
bash infrastructure/installer_reseau.sh          # J1 matin : ≈ 28 Go (dont l'image vLLM, 9,2 Go), smoke test à la fin
```

Si le formateur distribue la clé USB des modèles : `bash infrastructure/installer_reseau.sh --cle /media/$USER/<NOM>/helpdesk-modeles` (≈ 10 Go de moins à télécharger).

L'après-midi du J1, à la demande du formateur :

```bash
bash infrastructure/installer_reseau.sh --fond   # modèles et embeddings restants, en arrière-plan
```

Ensuite, depuis la racine du dépôt :

```bash
uv run --project infrastructure jupyter lab
```

Langfuse : http://127.0.0.1:3000 (identifiants dans `infrastructure/.env`).

Le J4, à la demande du formateur : `bash infrastructure/vllm_mode.sh juge` (le juge gemma4 prend la place des deux modèles granite sur le GPU), puis `bash infrastructure/vllm_mode.sh agents` pour revenir.

## Contenu

| Dossier | Contenu |
| --- | --- |
| `notebooks/` | un notebook par séquence (`J1_01` … ) |
| `exercices/enonces/` | exercices de la semaine |
| `src/helpdesk_ops/` | code partagé par les notebooks |
| `infrastructure/` | Docker Compose, `.env` généré, scripts d'installation et `smoke_test.py` |
| `data/` | base de connaissances, jeux d'évaluation |

Détails techniques et pannes fréquentes : `infrastructure/README.md`.
