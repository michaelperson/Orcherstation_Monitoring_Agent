---
description: Relire le diff courant avec la grille LangChain/LangGraph du cours
---
Lis `git diff` (et `git diff --staged`). Passe chaque point de la grille ci-dessous et réponds OUI / NON / SANS OBJET avec la ligne concernée. Ne corrige rien : propose seulement.
- Imports actuels (create_agent, StateGraph, langfuse.langchain.CallbackHandler, observe/propagate_attributes/get_client) ; aucun initialize_agent, AgentExecutor, LLMChain, langfuse.decorators, langfuse.callback
- Aucune version modifiée dans pyproject.toml / uv.lock
- Aucun secret dans le code ni dans les logs
- Aucun effet de bord avant interrupt() ; actions idempotentes
- Outils au moindre privilège ; MCP filtré par liste blanche
- Consignes au modèle dans le prompt (pas seulement dans Field(description))
- Règles métier en Python, appliquées après le modèle ET dans l'évaluation
- Erreurs journalisées (pas seulement un message aimable)
- Timeouts mesurés sur le matériel cible
- Traces Langfuse : session, tags, aucune donnée personnelle en clair
