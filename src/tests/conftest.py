"""Tests sans réseau : ni Ollama ni Langfuse. Le modèle est simulé, le tracing est désactivé."""
import asyncio
import os

import pytest
from pydantic import Field
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult

# Avant tout import de langfuse : aucun envoi, aucun avertissement de clés manquantes
os.environ["LANGFUSE_TRACING_ENABLED"] = "false"
os.environ.setdefault("LANGFUSE_PUBLIC_KEY", "pk-lf-tests")   # clés factices : le client reste désactivé
os.environ.setdefault("LANGFUSE_SECRET_KEY", "sk-lf-tests")


class FauxModeleOutils(BaseChatModel):
    """1er appel : demande `outil(args)` ; une fois le ToolMessage reçu : répond avec son contenu."""

    outil: str = "statut_serveur"
    args: dict = {"nom": "srv-erp-02"}
    appels: int = 0
    delai_s: float = 0.0   # > timeout du nœud agent : simule un modèle local trop lent
    vus: list = Field(default_factory=list)   # contenu des messages reçus, appel par appel

    @property
    def _llm_type(self) -> str:
        return "faux-modele"

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        self.appels += 1
        self.vus.append([getattr(m, "content", "") for m in messages])
        resultats = [m for m in messages if isinstance(m, ToolMessage)]
        if resultats:
            message = AIMessage(content=f"Réponse : {resultats[-1].content}")
        else:
            message = AIMessage(content="", tool_calls=[{"name": self.outil, "args": self.args, "id": "appel-1"}])
        return ChatResult(generations=[ChatGeneration(message=message)])

    async def _agenerate(self, messages, stop=None, run_manager=None, **kwargs):
        await asyncio.sleep(self.delai_s)
        return self._generate(messages, stop=stop, **kwargs)


@pytest.fixture
def faux_modele():
    return FauxModeleOutils()
