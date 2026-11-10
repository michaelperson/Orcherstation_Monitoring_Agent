# Ressources pour continuer après la formation

Cette liste rassemble des ressources officielles et à jour pour aller plus loin avec LangChain 1.x, LangGraph 1.x, Langfuse, MCP, Qdrant, Ollama, l'évaluation et la sécurité des agents.
La plupart des contenus sont en anglais : la documentation officielle évolue vite et ses traductions suivent mal. Les ressources en français sont signalées.
Chaque lien a été ouvert et contrôlé ; en cas de doute entre un tuto de blog et la doc officielle, croyez la doc officielle.

## Par où commencer (top 5)

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [LangChain : Quickstart](https://docs.langchain.com/oss/python/langchain/quickstart) | Débutant | EN | Le premier agent `create_agent` en quelques minutes, avec la syntaxe 1.x actuelle. |
| [Introduction to LangGraph (LangChain Academy)](https://academy.langchain.com/courses/intro-to-langgraph) | Débutant à intermédiaire | EN | Cours gratuit, 55 leçons, environ 6 h de vidéo : état, mémoire, human-in-the-loop, déploiement. |
| [Thinking in the Graph API](https://docs.langchain.com/oss/python/langgraph/thinking-in-graph-api) | Intermédiaire | EN | La méthode officielle pour découper un problème en nœuds, état et arêtes avant d'écrire du code. |
| [Langfuse : intégration LangChain / LangGraph](https://langfuse.com/integrations/frameworks/langchain) | Débutant | EN | Brancher le `CallbackHandler` pour tracer vos agents, y compris sur une instance auto-hébergée. |
| [Cours Agents de Hugging Face (version française)](https://huggingface.co/learn/agents-course/fr/unit0/introduction) | Débutant à avancé | FR | Cours gratuit traduit en français, avec une unité LangGraph ; bon complément pour réviser les concepts dans sa langue. |

## 1. Documentation officielle

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [LangChain overview](https://docs.langchain.com/oss/python/langchain/overview) | Débutant | EN | Point d'entrée de la doc LangChain 1.x : agents, modèles, outils, middleware. |
| [LangGraph overview](https://docs.langchain.com/oss/python/langgraph/overview) | Débutant | EN | Point d'entrée de LangGraph 1.x : graphes, persistance, interruptions, streaming. |
| [What's new in LangChain v1](https://docs.langchain.com/oss/python/releases/langchain-v1) | Intermédiaire | EN | Ce qui a changé en 1.0 (`create_agent`, middleware, contenu standard) ; utile pour lire du code ancien. |
| [LangChain v1 migration guide](https://docs.langchain.com/oss/python/migrate/langchain-v1) | Intermédiaire | EN | Table de correspondance entre l'ancienne API et la nouvelle, pour moderniser un tuto 0.x. |
| [Graph API overview](https://docs.langchain.com/oss/python/langgraph/graph-api) | Intermédiaire | EN | Référence conceptuelle sur `StateGraph`, reducers, `Command`, `Send`. |
| [Middleware overview](https://docs.langchain.com/oss/python/langchain/middleware/overview) | Intermédiaire | EN | Le mécanisme 1.x pour ajouter résumé, garde-fous, HITL ou retries autour d'un agent. |
| [Référence API Python](https://reference.langchain.com/python/langchain/) | Avancé | EN | Signatures exactes des classes et fonctions du paquet `langchain`. |
| [Use docs programmatically (llms.txt et serveur MCP de doc)](https://docs.langchain.com/use-these-docs) | Intermédiaire | EN | Explique comment brancher votre assistant IA sur la doc : index [`llms.txt`](https://docs.langchain.com/llms.txt) et serveur MCP `https://docs.langchain.com/mcp`. |

## 2. Cours gratuits structurés

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [Introduction to LangChain - Python (Academy)](https://academy.langchain.com/courses/foundation-introduction-to-langchain-python) | Débutant | EN | Construire des agents avec les architectures prêtes à l'emploi de LangChain 1.x ; gratuit. |
| [Introduction to LangGraph - Python (Academy)](https://academy.langchain.com/courses/intro-to-langgraph) | Débutant à intermédiaire | EN | Le cours de référence sur LangGraph, gratuit, 55 leçons. |
| [Introduction to Deep Agents (Academy)](https://academy.langchain.com/courses/foundation-introduction-to-deepagents) | Intermédiaire | EN | Agents longs avec le harnais Deep Agents (planification, système de fichiers, sous-agents) ; gratuit. |
| [Project: Ambient Agents with LangGraph (Academy)](https://academy.langchain.com/courses/ambient-agents) | Avancé | EN | Projet complet d'assistant e-mail : mémoire, human-in-the-loop, évaluation, déploiement. |
| [Project: Deep Agents (Academy)](https://academy.langchain.com/courses/deep-agents-with-langgraph) | Avancé | EN | Reconstruire pas à pas un agent profond pour comprendre ce que fait le harnais. |
| [AI Agents in LangGraph (DeepLearning.AI)](https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/) | Intermédiaire | EN | 1 h 47, par Harrison Chase : agent écrit à la main puis refait en LangGraph (page mise à jour le 04/11/2026). Certaines API montrées ont été renommées depuis : vérifier dans la doc. |
| [Long-Term Agentic Memory With LangGraph (DeepLearning.AI)](https://www.deeplearning.ai/short-courses/long-term-agentic-memory-with-langgraph/) | Intermédiaire | EN | Mémoire sémantique, épisodique et procédurale d'un agent. |
| [Cours Agents de Hugging Face (FR)](https://huggingface.co/learn/agents-course/fr/unit0/introduction) | Débutant à avancé | FR | Gratuit, traduit en français, certificat possible ; couvre smolagents, LlamaIndex et LangGraph. |

## 3. Tutoriels pas à pas officiels

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [LangGraph Quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart) | Débutant | EN | Un agent construit à la main avec la Graph API, puis avec la Functional API. |
| [Workflows and agents](https://docs.langchain.com/oss/python/langgraph/workflows-agents) | Intermédiaire | EN | Les motifs classiques (chaînage, routage, parallélisation, orchestrateur-travailleurs, évaluateur-optimiseur) en LangGraph. |
| [Build a custom RAG agent with LangGraph](https://docs.langchain.com/oss/python/langgraph/agentic-rag) | Intermédiaire | EN | RAG agentique : décider de chercher, noter les documents, réécrire la question. |
| [Build a semantic search engine](https://docs.langchain.com/oss/python/langchain/knowledge-base) | Débutant | EN | Chargement, découpage, embeddings et vector store : les briques du RAG. |
| [Human-in-the-loop](https://docs.langchain.com/oss/python/langchain/human-in-the-loop) | Intermédiaire | EN | Valider, modifier ou rejeter un appel d'outil avant exécution, avec le middleware HITL. |
| [Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) | Intermédiaire | EN | `interrupt()` et la reprise avec `Command(resume=...)` dans un graphe. |
| [Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) | Intermédiaire | EN | Checkpointers, threads, historique d'état, et [time-travel](https://docs.langchain.com/oss/python/langgraph/use-time-travel) pour rejouer un état passé. |
| [Structured output](https://docs.langchain.com/oss/python/langchain/structured-output) | Débutant | EN | `response_format` avec Pydantic : stratégies outil ou natif. |
| [Multi-agent](https://docs.langchain.com/oss/python/langchain/multi-agent) et [tutoriel sous-agents](https://docs.langchain.com/oss/python/langchain/multi-agent/subagents-personal-assistant) | Intermédiaire à avancé | EN | Superviseur, sous-agents, transferts : quand et comment découper en plusieurs agents. |

## 4. Exemples de code et dépôts GitHub officiels

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [langchain-ai/langgraph](https://github.com/langchain-ai/langgraph) | Avancé | EN | Code source, issues et notes de version de LangGraph. Le dossier `examples/` est archivé et n'est plus mis à jour : préférer la doc. |
| [langchain-ai/langchain](https://github.com/langchain-ai/langchain) | Avancé | EN | Code source de LangChain et de ses intégrations partenaires (dont `langchain-ollama`, `langchain-qdrant`). |
| [langchain-ai/langchain-academy](https://github.com/langchain-ai/langchain-academy) | Intermédiaire | EN | Les notebooks du cours Introduction to LangGraph, module par module, avec graphes pour Studio. |
| [langchain-ai/deepagents](https://github.com/langchain-ai/deepagents) | Intermédiaire | EN | Le harnais Deep Agents ; lire son code montre un agent de production bien structuré. |
| [langchain-ai/agents-from-scratch](https://github.com/langchain-ai/agents-from-scratch) | Avancé | EN | Assistant e-mail avec human-in-the-loop, mémoire et évaluation (support du cours Ambient Agents). |
| [langchain-ai/open_deep_research](https://github.com/langchain-ai/open_deep_research) | Avancé | EN | Agent de recherche multi-agents complet et configurable. |
| [langchain-ai/react-agent](https://github.com/langchain-ai/react-agent) et [new-langgraph-project](https://github.com/langchain-ai/new-langgraph-project) | Intermédiaire | EN | Gabarits de projet LangGraph prêts pour `langgraph dev` et Studio. |

## 5. Langfuse

Nota : la formation utilise le SDK Python v4. Au 10/11/2026, la doc Langfuse présente un SDK Python v5 (qui demande un serveur Langfuse v4 ou plus) ; consultez le guide de migration avant de monter de version.

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [Documentation Langfuse](https://langfuse.com/docs) | Débutant | EN | Point d'entrée : traces, prompts, évaluation, métriques. |
| [Intégration LangChain / LangGraph](https://langfuse.com/integrations/frameworks/langchain) | Débutant | EN | Tracer un agent LangChain ou un graphe LangGraph avec le `CallbackHandler`. |
| [SDK Python et JS/TS](https://langfuse.com/docs/observability/sdk/overview) | Intermédiaire | EN | SDK basé sur OpenTelemetry : `@observe`, spans, attributs. Guides de migration [v3 vers v4](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v3-to-v4) et [v4 vers v5](https://langfuse.com/docs/observability/sdk/upgrade-path/python-v4-to-v5). |
| [Self-hosting](https://langfuse.com/self-hosting) et [déploiement Docker Compose](https://langfuse.com/self-hosting/deployment/docker-compose) | Intermédiaire | EN | Héberger Langfuse soi-même, comme dans la formation. |
| [Evaluation overview](https://langfuse.com/docs/evaluation/overview) | Intermédiaire | EN | Vue d'ensemble : évaluation en ligne et hors ligne, scores, annotations. |
| [Datasets](https://langfuse.com/docs/evaluation/experiments/datasets) et [Experiments via SDK](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk) | Intermédiaire | EN | Constituer un jeu de test et rejouer l'agent dessus pour comparer des versions. |
| [LLM-as-a-Judge](https://langfuse.com/docs/evaluation/evaluation-methods/llm-as-a-judge) | Intermédiaire | EN | Faire noter les traces par un modèle juge, avec ses limites. |
| [Cookbook : tracer et évaluer des agents LangGraph](https://langfuse.com/guides/cookbook/example_langgraph_agents) | Intermédiaire | EN | Notebook complet de bout en bout ; d'autres recettes dans les [guides](https://langfuse.com/guides). Le [serveur MCP de la doc](https://langfuse.com/docs/docs-mcp) (`https://langfuse.com/api/mcp`) permet d'interroger la doc depuis son assistant IA. |

## 6. MCP (Model Context Protocol)

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [Qu'est-ce que MCP ? (site officiel)](https://modelcontextprotocol.io/docs/getting-started/intro) | Débutant | EN | Introduction officielle et [architecture](https://modelcontextprotocol.io/docs/learn/architecture) hôte, client, serveur. |
| [Spécification MCP (version 2026-07-28)](https://modelcontextprotocol.io/specification/2026-07-28) | Avancé | EN | Le texte normatif : outils, ressources, prompts, transports, autorisation. Version la plus récente au 10/11/2026. |
| [Build an MCP server](https://modelcontextprotocol.io/docs/develop/build-server) | Débutant | EN | Tutoriel officiel pour écrire son premier serveur. |
| [SDK Python officiel](https://github.com/modelcontextprotocol/python-sdk) | Intermédiaire | EN | Le SDK de référence pour serveurs et clients MCP en Python. |
| [FastMCP](https://gofastmcp.com/) ([dépôt](https://github.com/PrefectHQ/fastmcp)) | Intermédiaire | EN | Framework Python le plus utilisé pour écrire serveurs et clients MCP rapidement. |
| [langchain-mcp-adapters](https://github.com/langchain-ai/langchain-mcp-adapters) et [doc LangChain MCP](https://docs.langchain.com/oss/python/langchain/mcp) | Intermédiaire | EN | Charger les outils d'un serveur MCP dans un agent LangChain / LangGraph. |
| [Registre officiel des serveurs MCP](https://registry.modelcontextprotocol.io/) et [serveurs de référence](https://github.com/modelcontextprotocol/servers) | Débutant | EN | Trouver des serveurs existants et lire des implémentations exemplaires. |
| [Security Best Practices (MCP)](https://modelcontextprotocol.io/docs/tutorials/security/security_best_practices) | Avancé | EN | Attaques propres à MCP (confused deputy, passage de jeton, SSRF, détournement de session) et parades. |

## 7. RAG et Qdrant

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [Documentation Qdrant](https://qdrant.tech/documentation/) et [Local Quickstart](https://qdrant.tech/documentation/quickstart/) | Débutant | EN | Démarrer Qdrant en local avec Docker et faire ses premières requêtes. |
| [Hybrid Queries](https://qdrant.tech/documentation/search/hybrid-queries/) | Intermédiaire | EN | API Query, prefetch, fusion RRF/DBSF : la base de la recherche hybride dense + creuse. |
| [Hybrid Search in Qdrant](https://qdrant.tech/documentation/search-tuning/hybrid-search/) | Intermédiaire | EN | Pourquoi et comment combiner recherche lexicale et sémantique, avec reranking. |
| [Build a Hybrid Search API](https://qdrant.tech/documentation/tutorials-develop/hybrid-search-fastembed/) | Intermédiaire | EN | Tutoriel complet avec FastEmbed. |
| [Qdrant Essentials Course](https://qdrant.tech/course/essentials/) | Débutant à intermédiaire | EN | Cours gratuit de Qdrant sur la recherche vectorielle. |
| [Intégration Qdrant (doc LangChain)](https://docs.langchain.com/oss/python/integrations/vectorstores/qdrant) | Intermédiaire | EN | `QdrantVectorStore` : modes dense, creux et hybride côté LangChain. |
| [LangChain (doc Qdrant)](https://qdrant.tech/documentation/frameworks/langchain/) | Débutant | EN | Le même sujet vu par Qdrant. |

## 8. Modèles locaux (Ollama, vLLM)

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [Documentation Ollama](https://docs.ollama.com/) et [API](https://docs.ollama.com/api) | Débutant | EN | Installer, lancer et interroger des modèles en local. |
| [Ollama : Tool calling](https://docs.ollama.com/capabilities/tool-calling) | Intermédiaire | EN | Indispensable pour un agent : quels modèles appellent des outils et comment. |
| [Ollama : Structured Outputs](https://docs.ollama.com/capabilities/structured-outputs) | Intermédiaire | EN | Sortie contrainte par schéma JSON ; utile pour comprendre `response_format` en local. |
| [Bibliothèque de modèles Ollama](https://ollama.com/library) | Débutant | EN | Choisir un modèle (taille, capacités `tools`, `thinking`, `vision`). |
| [ChatOllama (doc LangChain)](https://docs.langchain.com/oss/python/integrations/chat/ollama) et [intégrations Ollama](https://docs.langchain.com/oss/python/integrations/providers/ollama) | Débutant | EN | Brancher Ollama dans LangChain : chat, embeddings, paramètres. |
| [Documentation vLLM](https://docs.vllm.ai/en/latest/) et [Tool Calling](https://docs.vllm.ai/en/latest/features/tool_calling/) | Avancé | EN | Servir un modèle sur GPU avec une API compatible OpenAI ; les parseurs d'appels d'outils. |
| [vLLM (doc LangChain)](https://docs.langchain.com/oss/python/integrations/chat/vllm) | Intermédiaire | EN | Brancher un serveur vLLM dans LangChain. |

## 9. Évaluation et sécurité

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [OWASP Top 10 for Agentic Applications for 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/) | Intermédiaire | EN | Les 10 risques propres aux agents (ASI01 à ASI10 : détournement d'objectif, abus d'outils, agents voyous...), publié le 09/12/2025. |
| [OWASP Top 10 for LLM Applications 2025](https://genai.owasp.org/llm-top-10/) | Intermédiaire | EN | Les risques de base hérités par tout agent, dont [LLM01 Prompt Injection](https://genai.owasp.org/llmrisk/llm01-prompt-injection/). |
| [Agentic AI : Threats and Mitigations (OWASP)](https://genai.owasp.org/resource/agentic-ai-threats-and-mitigations/) | Avancé | EN | Modèle de menaces détaillé des architectures agentiques. |
| [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html) | Intermédiaire | EN | Liste de contrôles concrets : moindre privilège des outils, validation, HITL, journalisation. |
| [OWASP LLM Prompt Injection Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/LLM_Prompt_Injection_Prevention_Cheat_Sheet.html) | Intermédiaire | EN | Techniques de défense contre l'injection directe et indirecte (documents, pages web, e-mails). |
| [Guardrails (doc LangChain)](https://docs.langchain.com/oss/python/langchain/guardrails) | Intermédiaire | EN | Garde-fous par middleware : PII, filtrage d'entrée et de sortie, validation humaine. |
| [Evaluating AI Agents (DeepLearning.AI, avec Arize)](https://www.deeplearning.ai/short-courses/evaluating-ai-agents/) | Intermédiaire | EN | Évaluer routeur, compétences et trajectoire ; LLM-as-a-judge (page mise à jour le 04/11/2026). |
| [Evaluation concepts](https://docs.langchain.com/langsmith/evaluation-concepts), [agentevals](https://github.com/langchain-ai/agentevals) et [openevals](https://github.com/langchain-ai/openevals) | Intermédiaire à avancé | EN | Vocabulaire de l'évaluation (hors ligne, en ligne, trajectoire) et évaluateurs prêts à l'emploi, utilisables aussi hors LangSmith. Voir aussi [Test](https://docs.langchain.com/oss/python/langchain/test) pour les tests d'agents. |

## 10. Vidéos et ressources en français

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [Chaîne YouTube LangChain](https://www.youtube.com/@LangChain) | Tous niveaux | EN | Annonces, tutoriels et séries officielles ; regardez la date : les vidéos d'avant fin 2025 montrent souvent l'API 0.x. |
| [Chaîne YouTube Langfuse](https://www.youtube.com/@langfuse) | Débutant à intermédiaire | EN | Démos officielles de traçage, prompts et évaluation. |
| [MCP: Build Rich-Context AI Apps with Anthropic (DeepLearning.AI)](https://www.deeplearning.ai/short-courses/mcp-build-rich-context-ai-apps-with-anthropic/) | Intermédiaire | EN | Cours vidéo de 1 h 58 : client, serveur et déploiement MCP (mis à jour le 13/08/2026). |
| [Cours MCP de Hugging Face](https://huggingface.co/learn/mcp-course/unit0/introduction) | Débutant à intermédiaire | EN | Cours gratuit sur MCP, de la théorie à la construction d'applications. |
| [Cours Agents de Hugging Face (FR)](https://huggingface.co/learn/agents-course/fr/unit0/introduction) | Débutant à avancé | FR | La ressource sérieuse et gratuite la plus complète en français sur les agents, avec une partie LangGraph. |

Nous n'avons pas trouvé de cours vidéo en français, sérieux et à jour sur LangChain 1.x : les tutos francophones repérés mélangeaient encore des versions 0.3. Pour le français, combinez le cours Hugging Face et la traduction automatique de la doc officielle.

## 11. Communautés

| Ressource | Niveau | Langue | Pourquoi |
|---|---|---|---|
| [Forum LangChain](https://forum.langchain.com/) | Tous niveaux | EN | Le lieu officiel pour poser ses questions LangChain / LangGraph, suivi par l'équipe. |
| [Communauté Slack LangChain](https://www.langchain.com/join-community) | Tous niveaux | EN | Échanges entre développeurs et annonces. |
| [GitHub Discussions Langfuse](https://github.com/orgs/langfuse/discussions) | Tous niveaux | EN | Questions, demandes de fonctionnalités, entraide, notamment sur l'auto-hébergement. |
| [Discord Langfuse](https://langfuse.com/discord) | Tous niveaux | EN | Aide rapide de la communauté et de l'équipe. |
| [Dépôt GitHub Langfuse](https://github.com/langfuse/langfuse) | Intermédiaire | EN | Issues et notes de version : à surveiller avant toute mise à jour de l'instance. |

## Méfiez-vous des tutos dépassés

Un tuto LangChain 0.x se reconnaît à ces signes :

- **`initialize_agent`, `AgentExecutor`, `AgentType.ZERO_SHOT_REACT_DESCRIPTION`** : remplacés par `create_agent` (paquet `langchain`, version 1.x).
- **`LLMChain`, `SequentialChain`, `RetrievalQA`, `ConversationalRetrievalChain`** : chaînes héritées, déplacées dans `langchain-classic` ; aujourd'hui on écrit un agent, un graphe ou une composition LCEL.
- **`ConversationBufferMemory` et les autres classes `memory`** : remplacées par les checkpointers LangGraph et un `thread_id`.
- **`from langchain.llms import ...`, `from langchain.chat_models import ChatOpenAI`, `from langchain.vectorstores import ...`** : les intégrations vivent désormais dans des paquets dédiés (`langchain-ollama`, `langchain-qdrant`, `langchain-openai`...).
- **`from langgraph.prebuilt import create_react_agent`** : encore présent pour compatibilité, mais le point d'entrée recommandé est `from langchain.agents import create_agent`.
- **`.run()`, `.predict()`, `chain(...)` appelés directement** : en 1.x on utilise `.invoke()`, `.stream()`, `.batch()`.
- **`pip install langchain==0.x` ou `langchain-core<1`** dans les prérequis, ou des liens vers `python.langchain.com/docs` ou `langchain-ai.github.io/langgraph` : documentation ancienne, désormais regroupée sur `docs.langchain.com`.
- **Langfuse : `from langfuse.callback import CallbackHandler`** ou `langfuse.decorators` : syntaxe du SDK v2 ; depuis la v3, c'est `from langfuse.langchain import CallbackHandler` et `from langfuse import observe`.
- **Une date antérieure à fin 2025** sans mention de LangChain 1.0 : vérifiez chaque import dans le [guide de migration](https://docs.langchain.com/oss/python/migrate/langchain-v1).

---

Liens vérifiés le 10/11/2026.
