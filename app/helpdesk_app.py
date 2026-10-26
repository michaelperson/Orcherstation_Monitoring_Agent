"""Interface Streamlit de HelpDesk-Ops (jour 5), branchée sur le jalon J5.

    uv run --project infrastructure streamlit run app/helpdesk_app.py      # depuis la racine du cours

La racine contient .streamlit/config.toml : écoute sur 127.0.0.1 et statistiques d'usage coupées (actives par défaut).

Ce que l'interface ajoute au graphe : l'information « vous parlez à une IA » visible en permanence (AI Act
art. 50), une session Langfuse par conversation, le 👍/👎 attaché à la trace de la réponse, et un bouton
d'effacement (RGPD art. 17) qui supprime la conversation ET ses traces. Démonstration locale : la persistance
est en mémoire (perdue au redémarrage) ; en production, un checkpointer durable et une authentification.
"""
import uuid

import streamlit as st
from langgraph.checkpoint.memory import InMemorySaver

from helpdesk_ops.conformite import MESSAGE_IA
from helpdesk_ops.config import creer_llm
from helpdesk_ops.jalons.j5 import VERSION, construire_helpdesk_j5, repondre_avec_trace
from helpdesk_ops.observabilite import effacer_session, init_observabilite

st.set_page_config(page_title="HelpDesk-Ops", page_icon="🎧")


@st.cache_resource
def ressources():
    """Une fois par processus : client Langfuse, checkpointer, graphe (le chargement des modèles est long)."""
    langfuse, handler = init_observabilite()
    saver = InMemorySaver()
    llm = creer_llm("agent")
    return langfuse, handler, saver, construire_helpdesk_j5(llm, checkpointer=saver, modele=llm.model)


langfuse, handler, saver, graphe = ressources()
etat = st.session_state
etat.setdefault("thread_id", f"web-{uuid.uuid4().hex[:12]}")
etat.setdefault("historique", [])

# ------------------------------------------------------------------ barre latérale
with st.sidebar:
    st.header("🎧 HelpDesk-Ops")
    user_id = st.text_input("Identifiant (pseudonyme)", value="collab-demo",
                            help="Jamais un e-mail ni un nom : c'est lui qui est envoyé à Langfuse.")
    if "@" in user_id or " " in user_id.strip():
        st.error("Un pseudonyme, pas un e-mail ni un nom (minimisation, RGPD art. 5).")
        st.stop()
    st.caption(f"Conversation `{etat.thread_id}` · {VERSION}")
    if st.button("Nouvelle conversation"):
        etat.thread_id, etat.historique = f"web-{uuid.uuid4().hex[:12]}", []
        st.rerun()
    if st.button("🗑️ Effacer cette conversation et ses traces", type="secondary"):
        connues = [t["trace_id"] for t in etat.historique if t.get("trace_id")]
        with st.spinner("Effacement en cours (attente de l'enregistrement des dernières traces)…"):
            traces, introuvables = effacer_session(langfuse, etat.thread_id, traces_connues=connues)
        saver.delete_thread(etat.thread_id)
        etat.thread_id, etat.historique = f"web-{uuid.uuid4().hex[:12]}", []
        if introuvables:   # ne jamais annoncer un effacement complet qui ne l'est pas
            st.warning(f"Conversation effacée, mais {len(introuvables)} trace(s) introuvable(s) dans Langfuse : "
                       "réessayez dans une minute ou signalez-le au help-desk.")
        else:
            st.success(f"Conversation effacée ({len(traces)} trace(s) supprimée(s) dans Langfuse).")

# ------------------------------------------------------------------ conversation
st.info(MESSAGE_IA, icon="🤖")   # AI Act art. 50 : l'information reste visible pendant tout l'échange


def afficher(i: int, tour: dict) -> None:
    with st.chat_message(tour["role"]):
        st.markdown(tour["contenu"])
        if tour["role"] != "assistant" or not tour.get("trace_id"):
            return
        if tour.get("bloquees"):
            st.caption("⚠️ Réponse remplacée par le contrôle de sortie.")
        st.caption(f"Réponse générée par IA · {tour.get('modele', '?')}")
        avis = st.feedback("thumbs", key=f"avis-{i}")
        if avis is not None and not tour.get("note"):
            langfuse.create_score(trace_id=tour["trace_id"], name="pouce", value=bool(avis), data_type="BOOLEAN")
            langfuse.flush()
            tour["note"] = True


for i, tour in enumerate(etat.historique):
    afficher(i, tour)

if question := st.chat_input("Décrivez votre problème informatique"):
    etat.historique.append({"role": "user", "contenu": question})
    afficher(len(etat.historique) - 1, etat.historique[-1])
    with st.spinner("HelpDesk-Ops consulte ses spécialistes…"):
        message, trace_id = repondre_avec_trace(graphe, question, thread_id=etat.thread_id, user_id=user_id,
                                                langfuse=langfuse, handler=handler)
    marque = message.response_metadata.get("ia_act_art50", {})
    bloquees = graphe.get_state({"configurable": {"thread_id": etat.thread_id}}).values.get("bloquees")
    etat.historique.append({"role": "assistant", "contenu": message.content.removeprefix(MESSAGE_IA).lstrip(),
                            "trace_id": trace_id, "modele": marque.get("modele"), "bloquees": bool(bloquees)})
    st.rerun()
