"""Base de connaissances NordTech sur Qdrant : ingestion et recherche hybride (jalon J3).

    data/kb/*.md ──découpage par section──▶ embeddings denses (HF multilingue)
                                          + vecteurs creux BM25 (fastembed, français)
                                          ──▶ collection Qdrant hybride (fusion RRF)

Trois choix vérifiés en préparant le cours (20/10/2026) :
- la collection est créée **ici**, avec `Modifier.IDF` sur le vecteur creux : celle que crée
  `QdrantVectorStore.from_documents` n'a pas de modificateur, et BM25 perd sa pondération IDF ;
- BM25 en **français** (`language="french"`) : racinisation et mots vides français ;
- identifiants de points **stables** (uuid5 de l'article et du morceau) : réindexer remplace au lieu
  de dupliquer.
"""
import os
import uuid
from functools import lru_cache
from pathlib import Path

from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient, models

from helpdesk_ops.config import charger_env, trouver_env

VECTEUR_CREUX = "langchain-sparse"   # nom attendu par QdrantVectorStore
ESPACE_IDS = uuid.UUID("6f0c3a2e-5b1d-4e8a-9c7f-2d4b8e1a0c55")


def dossier_kb() -> Path:
    return trouver_env().parent.parent / "data" / "kb"


# --------------------------------------------------------------------------- lecture
def lire_article(chemin: Path) -> Document:
    """Un article Markdown avec en-tête `---` (id, titre, categorie, equipe, visibilite, maj)."""
    texte = chemin.read_text(encoding="utf-8")
    _, entete, corps = texte.split("---", 2)
    meta = dict(ligne.split(":", 1) for ligne in entete.strip().splitlines())
    meta = {cle.strip(): valeur.strip() for cle, valeur in meta.items()}
    return Document(page_content=corps.strip(), metadata=meta)


def charger_articles(dossier: Path | None = None) -> list[Document]:
    dossier = dossier or dossier_kb()
    return [lire_article(p) for p in sorted(dossier.glob("KB-*.md"))]


def decouper(articles: list[Document], taille: int = 700) -> list[Document]:
    """Un morceau par section ## (le titre de l'article et de la section restent dans le texte indexé)."""
    sections = MarkdownHeaderTextSplitter([("#", "titre_h1"), ("##", "section")], strip_headers=False)
    garde_fou = RecursiveCharacterTextSplitter(chunk_size=taille, chunk_overlap=80)
    morceaux = []
    for article in articles:
        for i, section in enumerate(garde_fou.split_documents(sections.split_text(article.page_content))):
            meta = {**article.metadata, "section": section.metadata.get("section", ""), "morceau": i}
            texte = f"{article.metadata['titre']}\n{section.page_content}"
            morceaux.append(Document(page_content=texte, metadata=meta))
    return morceaux


# --------------------------------------------------------------------------- modèles et client
@lru_cache(maxsize=1)
def embeddings_denses():
    from langchain_huggingface import HuggingFaceEmbeddings
    charger_env()
    return HuggingFaceEmbeddings(model_name=os.environ["EMBEDDING_MODEL"])


@lru_cache(maxsize=1)
def embeddings_creux():
    from langchain_qdrant import FastEmbedSparse
    charger_env()  # FASTEMBED_CACHE_PATH éventuel (kit USB), sinon cache dans /tmp
    return FastEmbedSparse(model_name="Qdrant/bm25", language="french")


def precharger_modeles() -> None:
    """À lancer la veille (réseau requis une fois) : ensuite tout fonctionne hors ligne."""
    embeddings_denses().embed_query("préchargement")
    embeddings_creux().embed_query("préchargement")


@lru_cache(maxsize=1)
def client_qdrant() -> QdrantClient:
    charger_env()
    return QdrantClient(url=os.environ["QDRANT_URL"], api_key=os.environ["QDRANT_API_KEY"])


def nom_collection() -> str:
    charger_env()
    return os.environ.get("QDRANT_COLLECTION", "kb_nordtech")


# --------------------------------------------------------------------------- indexation
def creer_collection(client: QdrantClient, nom: str, dimension: int, *, recreer: bool = False) -> None:
    if client.collection_exists(nom):
        if not recreer:
            return
        client.delete_collection(nom)
    client.create_collection(
        nom,
        vectors_config=models.VectorParams(size=dimension, distance=models.Distance.COSINE),
        sparse_vectors_config={VECTEUR_CREUX: models.SparseVectorParams(modifier=models.Modifier.IDF)},
    )
    # Index de payload : filtres rapides (et indispensables à grande échelle)
    for champ in ("categorie", "visibilite", "equipe", "id"):
        client.create_payload_index(nom, f"metadata.{champ}", models.PayloadSchemaType.KEYWORD)


def indexer(*, recreer: bool = False, dossier: Path | None = None) -> int:
    """Indexe (ou réindexe) la KB. Renvoie le nombre de morceaux."""
    from langchain_qdrant import QdrantVectorStore, RetrievalMode
    client, nom = client_qdrant(), nom_collection()
    dense = embeddings_denses()
    creer_collection(client, nom, len(dense.embed_query("dimension")), recreer=recreer)
    morceaux = decouper(charger_articles(dossier))
    ids = [str(uuid.uuid5(ESPACE_IDS, f"{m.metadata['id']}#{m.metadata['morceau']}#{m.metadata['section']}")) for m in morceaux]
    QdrantVectorStore(client=client, collection_name=nom, embedding=dense, sparse_embedding=embeddings_creux(),
                      retrieval_mode=RetrievalMode.HYBRID).add_documents(morceaux, ids=ids)
    magasin.cache_clear()   # la collection a pu être recréée
    return len(morceaux)


# --------------------------------------------------------------------------- recherche
@lru_cache(maxsize=4)
def magasin(mode: str = "hybrid"):
    """Mis en cache : construire le magasin (client, vérification de version, validation de la collection)
    coûtait ~5 s à CHAQUE recherche sur le poste de préparation, contre 30 ms pour l'embedding."""
    from langchain_qdrant import QdrantVectorStore, RetrievalMode
    return QdrantVectorStore(client=client_qdrant(), collection_name=nom_collection(),
                             embedding=embeddings_denses(), sparse_embedding=embeddings_creux(),
                             retrieval_mode=RetrievalMode(mode))


def filtre(*, public_seulement: bool = True, categorie: str | None = None) -> models.Filter | None:
    conditions = []
    if public_seulement:   # l'assistant N1 ne voit jamais les procédures internes N2
        conditions.append(models.FieldCondition(key="metadata.visibilite", match=models.MatchValue(value="public")))
    if categorie:
        conditions.append(models.FieldCondition(key="metadata.categorie", match=models.MatchValue(value=categorie)))
    return models.Filter(must=conditions) if conditions else None


def rechercher(question: str, *, k: int = 3, public_seulement: bool = True, categorie: str | None = None,
               mode: str = "hybrid", un_par_article: bool = True) -> list[Document]:
    """Les k meilleurs morceaux ; `un_par_article` : le meilleur morceau de k articles DIFFÉRENTS
    (sinon les sections d'un même article occupent toutes les places et masquent les autres)."""
    candidats = magasin(mode).similarity_search(question, k=k * 3 if un_par_article else k,
                                                filter=filtre(public_seulement=public_seulement, categorie=categorie))
    if not un_par_article:
        return candidats
    vus, resultats = set(), []
    for doc in candidats:
        if doc.metadata["id"] not in vus:
            vus.add(doc.metadata["id"])
            resultats.append(doc)
    return resultats[:k]


def formater(documents: list[Document]) -> str:
    """Texte pour le LLM : chaque extrait porte sa référence [KB-xxx] pour être cité."""
    if not documents:
        return "Aucun article pertinent dans la base de connaissances."
    return "\n\n".join(f"[{d.metadata['id']}] {d.page_content}" for d in documents)
