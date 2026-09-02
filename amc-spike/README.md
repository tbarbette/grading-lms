# Spike : AMC dockerisé + interface web d'évaluation

Conteneurise [Auto Multiple Choice](https://www.auto-multiple-choice.net/)
(AMC, outil desktop Perl/GTK **sans interface web native**) et l'entoure d'un
wrapper web FastAPI jetable pour piloter son pipeline CLI, avec 3
personnalisations pour évaluer les points différenciants du projet final :
variables/seed par copie, correction assistée par LLM, rubrique à la volée.

## Lancer

```bash
docker compose build
docker compose up -d amc
# UI sur http://localhost:8000
```

Pour activer la personnalisation LLM avec un modèle Ollama local :

```bash
docker compose --profile llm up -d
docker exec -it amc-spike-ollama-1 ollama pull qwen2.5vl:3b
```

(ou pointer `OPENAI_BASE_URL`/`OPENAI_API_KEY`/`LLM_MODEL` + `LLM_PROVIDER=openai`
vers un endpoint distant compatible OpenAI dans `docker-compose.yml`.)

## Utilisation (via l'UI web)

1. Créer un projet.
2. Coller une source LaTeX AMC (voir `test-data/source.tex`, validée) ou
   utiliser la personnalisation "variables/seed" pour en générer une à partir
   d'un template Jinja2 + expressions (`randint(a,b)`, arithmétique).
3. "Prepare" → génère sujet.pdf/corrige.pdf/catalog.pdf et importe le
   catalogue de positions des zones de réponse.
4. Uploader une liste d'étudiants (CSV `id,name`) et des scans des copies
   remplies.
5. Lancer Analyse → (Associate) → Note → Export → Annotate.
6. Page **Correction** (lien "6. Correction assistée par LLM" sur la page
   projet) : pour chaque étudiant × question capturée automatiquement par AMC
   (voir plus bas), l'image recadrée par AMC lui-même s'affiche directement,
   avec un bouton "Transcrire avec le LLM" et l'ajout/application de rubrique
   juste à côté. L'upload manuel d'image reste disponible en repli, seulement
   pour les questions `questionouverte` (non trackées par AMC, cf. limitations).

## Ce qui a été validé de bout en bout (dans ce spike)

Toutes les commandes ci-dessous ont été exécutées réellement en conteneur, pas
seulement lues dans la doc :

- `auto-multiple-choice prepare --mode sb ...` : génère sujet/corrigé/catalogue
  **et** la base de notation (mode `b`, indispensable pour `note`/`annotate` —
  absent, ils tournent silencieusement sur une base de notation vide).
- `auto-multiple-choice meptex --src calage.xy --data ...` : **étape non
  documentée dans le pipeline évident**, indispensable pour importer les
  positions des zones de réponse dans `layout.sqlite` avant `analyse` (sans
  elle, `analyse` échoue avec `ERR: Scan : No layout`).
- `auto-multiple-choice analyse --data ... --cr ... scan1.png scan2.png` :
  OMR sur des scans simulés (rendu du sujet.pdf via `pdftoppm`), corner-marks
  détectées, aucune erreur.
- `auto-multiple-choice note` puis `export --module CSV` : produit un
  `results.csv` avec une note réelle par question et par copie.
- `auto-multiple-choice annotate` : génère les PDF annotés par copie sans
  erreur (une fois la base de notation présente).
- **La transcription LLM lit directement l'image qu'AMC a déjà recadrée/alignée**
  (table `capture_zone` de `capture.sqlite`, colonne `imagedata` — un BLOB PNG
  par zone de case à cocher, rempli automatiquement pendant `analyse`, que la
  case soit cochée ou non). Aucun upload manuel, aucun calcul de perspective
  refait à la main : `wrapper/zones.py` lit directement ce BLOB. Validé de
  bout en bout : `prepare` → `analyse` → page `/projects/{id}/grading` → image
  servie par `/projects/{id}/zone-image/{student}/{question}` → transcription.
- **Une question "ouverte" peut être capturée par AMC** en la définissant comme
  un choix unique (`\correctchoice{}`) dont on agrandit la case à cocher via
  `\AMCboxDimensions{width=...,height=...}` (voir `test-data/source.tex`,
  question `explain`) : AMC la traite alors comme n'importe quelle case, avec
  le même recadrage/capture automatique que pour un QCM.
- **"Grande case" fiable : plusieurs cases étroites juxtaposées, recollées en
  une image côté wrapper.** Le détecteur OMR d'AMC plante seulement si une
  case est trop **large** (largeur, pas hauteur ni surface — voir limitation
  2). Solution retenue et validée : la question `explain` est composée de 3
  cases de 3cm × 4cm juxtaposées horizontalement (`choiceshoriz`), chacune
  sous le seuil de largeur qui plante AMC. `wrapper/zones.py` (fonction
  `get_combined_image`) récupère les crops des 3 cases dans `capture.sqlite`
  et les recolle côte à côte (Pillow) en une seule image large (validé :
  651×277px à partir de 3 cases de ~199×277px chacune) avant de l'envoyer au
  LLM. Aucune modification du code AMC, juste de la composition côté wrapper.

## Limitations connues (découvertes pendant le spike, pas supposées)

1. **`association-auto` a échoué** avec notre source de test minimale : elle
   exige une question "code" dédiée (boîtes à chiffres, `--notes-id`) pour
   apparier automatiquement une copie à un étudiant. Notre exemple n'a qu'un
   `\namefield` (nom manuscrit), donc l'association automatique par code
   n'est pas applicable telle quelle — à reprendre avec une vraie question de
   code, ou en association manuelle (`auto-multiple-choice association
   --student ... --copy ...`, non implémentée ici).
2. **Cause précise du plantage du détecteur OMR d'AMC sur une grande case**
   (pas de rapport de bug trouvé en ligne pour ce cas précis ; le code source
   réel a été lu directement : [`AMC-detect.cc`](https://github.com/AnirvanSarkar/auto-multiple-choice/blob/master/AMC-detect.cc),
   fonction qui sauvegarde le "zoom" de la case, calcule un rectangle à
   partir des coins transformés en pixels + une marge, puis fait
   `illustr(cv::Rect(...))` — hors-limites pour certaines dimensions).
   **Bissection empirique faite dans ce spike** (pas une supposition) :
   c'est la **largeur** qui plante, pas la hauteur ni la surface.
   - Largeur ≤ 3.5cm : toujours OK, quelle que soit la hauteur (testé
     jusqu'à 3cm × 8cm, capture réussie, `total` de pixels ~53k).
   - Largeur ≥ 4cm : plante systématiquement (`cv::Exception ... roi.x +
     roi.width <= m.cols`), testé à 4cm, 4.5cm, 6cm, indépendamment de la
     hauteur ou du ratio largeur/hauteur.
   - **Solution retenue** (voir plus haut) : juxtaposer plusieurs cases
     étroites (`choiceshoriz`) au lieu d'une seule grande case, et recoller
     les images côté wrapper. Ça marche et donne une vraie grande zone
     d'écriture (validé avec 3 cases de 3cm de large).
3. `export --fich-noms students.csv` produit des avertissements Perl non
   bloquants (colonnes CSV/association-key à affiner) ; le CSV généré reste
   correct mais la colonne "Name" n'est pas renseignée sans association
   réussie (cf. limitation 1).
4. Le recadrage automatique décrit ci-dessus ne fonctionne que pour les zones
   de type case (`ZONE_BOX`). Un vrai `\questionouverte` n'est toujours pas
   suivi géométriquement par AMC ; l'upload manuel reste le seul repli pour
   ce cas précis. Avec la juxtaposition de cases, ce repli devrait rarement
   être nécessaire en pratique.

## Bilan pour la décision "construire notre propre outil" (Plan 1)

- AMC couvre déjà très bien : génération LaTeX de sujets multi-copies,
  détection de corner-marks, OMR sur cases à cocher, catalogue de positions
  déterministe (`layout.sqlite`), export CSV, annotation PDF par copie, **et**
  (découverte de cette itération) le recadrage/alignement automatique des
  zones de réponse — on peut brancher le LLM directement sur ces crops, sans
  ré-implémenter la correction de perspective nous-mêmes, au moins pour des
  réponses courtes.
- Ce qu'il ne fait pas nativement (confirme le besoin du Plan 1) : variables
  algébriques par copie (mélange de questions/choix seulement), correction
  LLM de texte libre pour des réponses longues (limité par le plafond de
  taille de case ci-dessus), rubrique interactive à la volée, association
  d'identité flexible sans question-code dédiée.
- Le pipeline CLI réel est plus subtil que la documentation ne le laisse
  penser (`meptex` manquant, mode `b` manquant) : si le Plan 1 réutilise un
  jour AMC comme moteur bas niveau plutôt que de tout réécrire, prévoir ce
  temps de découverte.
