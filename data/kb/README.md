# Base de connaissances fictive de NordTech SA

20 articles Markdown, **fictifs** (aucune donnée réelle), utilisés à partir du jour 3 (RAG sur Qdrant).

En-tête de chaque article : `id`, `titre`, `categorie` (reseau, materiel, logiciel, acces, autre), `equipe` (N1, N2-infra…),
`visibilite` (`public` : visible par l'assistant N1 ; `interne` : réservé aux équipes N2), `maj`.

Indexation : `helpdesk_ops.kb.indexer()` (voir notebook J3-02). Modifier un article puis réindexer suffit.
