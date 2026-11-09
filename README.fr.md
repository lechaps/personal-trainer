# Personal Trainer — Apple Notes ↔ Codex, sans données personnelles dans Git

[English version](README.md)

## Architecture

- **Apple Notes / Sport (iCloud)** : source de vérité ; une note `Profil & Objectifs`, une note `Programme` facultative, puis une note datée par séance. Utilise les titres exacts décrits dans la section Format des notes.
- **Git** : code source, instructions `AGENTS.md`, Skill Codex et tests. **Aucune séance réelle ni information de santé.**
- **Codex** : prépare les propositions dans un brouillon privé, puis demande validation avant publication.

## Prérequis

- Un Mac avec Notes.app synchronisé avec ton iPhone via iCloud.
- Un dossier simple nommé `Sport` directement sous le compte Notes `iCloud`, pas un dossier intelligent.
- Python 3.10+ (à vérifier avec `python3 --version`).
- `osascript` sur macOS, avec l'autorisation pour Terminal et/ou Codex de contrôler Notes dans **Automatisation → Notes**.
- Un accès local de Codex au projet et à son dossier privé `sport/`.
- Des notes textuelles dans Apple Notes : les pièces jointes, tableaux natifs, dessins et notes verrouillées ne sont pas pris en charge en V1.

## Installation

1. Ouvre le dépôt `personal-trainer` dans Codex, puis un terminal à sa racine. Aucun paquet Python supplémentaire n'est nécessaire.

```bash
python3 --version
python3 -m unittest discover -s tests -v
```

2. Dans Apple Notes, sous le compte `iCloud`, crée un dossier simple nommé `personal-trainer-Test` avec des notes fictives nommées `Profil & Objectifs` et `2026-11-09 — Test`. Configure le terminal et teste la lecture :

```bash
export PERSONAL_TRAINER_ACCOUNT="iCloud"
export PERSONAL_TRAINER_FOLDER="personal-trainer-Test"
python3 scripts/personal-trainer.py sync
```

Au premier accès, autorise Terminal ou Codex à contrôler Notes si macOS le demande. En cas de refus, vérifie **Réglages Système → Confidentialité et sécurité → Automatisation**. Arrête-toi si la synchronisation échoue.

3. Suis la section **Tests Mac** ci-dessous, y compris la publication dans le dossier de test, avant d'utiliser tes données réelles.

4. Dans Apple Notes, prépare ton dossier réel `Sport`, avec une note nommée `Profil & Objectifs` et éventuellement `Programme`. Sélectionne ce dossier et importe les notes :

```bash
export PERSONAL_TRAINER_FOLDER="Sport"
python3 scripts/personal-trainer.py sync --apply
```

Le cache est enregistré dans `sport/notes.json`, exclu de Git. L'import ne modifie pas les notes Apple. Ces variables d'environnement s'appliquent au terminal courant ; les valeurs par défaut sont `iCloud` et `Sport`.

Pour demander une analyse ou une séance à Codex, indique-lui de lire `.agents/skills/personal-trainer/SKILL.md` et d'utiliser le contexte importé. **L'analyse du contexte par Codex peut transmettre des données privées au service du modèle.** Toute publication doit attendre ta validation explicite.

L'installation ne nécessite aucun commit. Active le hook de protection pour ce dépôt :

```bash
chmod +x hooks/pre-commit
git config --local core.hooksPath hooks
```

Le hook lance `python3 scripts/git_guard.py` avant chaque commit et bloque les chemins hors liste blanche, notamment `sport/`. Il ne détecte pas les données privées copiées dans un fichier autorisé : prépare explicitement les seuls fichiers nécessaires et vérifie toujours leur contenu avec `git diff --cached`. Cette configuration est locale et doit être répétée pour chaque nouveau clone.

## Utiliser ce dépôt avec Codex

Ouvre ce dépôt dans Codex et formule tes demandes en langage naturel, en français ou en anglais. Demande à Codex d'utiliser le Skill `personal-trainer` dans `.agents/skills/personal-trainer/SKILL.md`. Il utilise ta note `Profil & Objectifs` et les séances récentes pour proposer un entraînement ou analyser ta progression. Avant une nouvelle analyse, actualise l'historique depuis Apple Notes ; arrête-toi si la synchronisation échoue. Pour une demande d'entraînement, précise ta fatigue actuelle, les douleurs éventuelles, le temps disponible et le matériel. Confirme clairement les séances réalisées : une note prévue n'est pas une séance terminée.

Prompts utiles :

- **Actualiser l'historique :** « Importe les dernières notes Apple dans le cache privé sans modifier les notes originales. »
- **Prochaine séance :** « Utilise le Skill personal-trainer pour préparer ma prochaine séance à partir de mon historique actualisé. J'ai 60 minutes en salle, une énergie normale et aucune douleur. Inclus les charges de départ lorsque mon historique le permet, les séries, répétitions, repos et l'effort cible. »
- **Programme de la semaine :** « Utilise le Skill personal-trainer pour organiser cette semaine. Je peux m'entraîner mardi et jeudi pendant une heure et dimanche pendant 90 minutes. Équilibre musculation, endurance et récupération. Pas de VTT cette semaine. »
- **Bilan des performances :** « Utilise le Skill personal-trainer pour analyser mes quatre dernières semaines. Compare les résultats confirmés, relève les progrès et la fatigue, et précise ce que les données disponibles ne permettent pas de conclure. »
- **Compte rendu de séance :** « J'ai terminé la séance du jour. Voici mes séries, répétitions, charges, durée, effort global /10 et douleurs éventuelles : […]. Compare le prévu et le réalisé, sans préparer la prochaine séance pour le moment. »
- **Enregistrer un brouillon :** « Enregistre cette proposition dans un brouillon privé sous sport/drafts/, sans la publier. »
- **Publier une séance validée :** « Je valide cette séance. Publie-la dans Apple Notes. »

Codex peut demander les précisions indispensables manquantes. Relis la séance complète avant d'autoriser sa publication. La publication crée une nouvelle note ; elle ne met pas à jour une note existante. Saisis tes résultats réels dans Apple Notes et indique `Statut: terminée`, puis actualise l'historique. Le contexte privé lu par Codex peut être transmis au service du modèle, même si `sport/` est exclu de Git.

## Commandes quotidiennes

```bash
# Lire toutes les notes du dossier (simulation : ne sauvegarde pas le cache)
python3 scripts/personal-trainer.py sync

# Actualiser le cache privé dans sport/notes.json (exclu de Git)
python3 scripts/personal-trainer.py sync --apply

# Contexte privé pour Codex ; conserver toute copie dans sport/
python3 scripts/personal-trainer.py context --last 10

# Créer une proposition dans sport/drafts/ et afficher son chemin
python3 scripts/personal-trainer.py new-draft --date 2026-11-10 --type "Haut du corps"

# Modifier ce brouillon PRIVÉ avec Codex, puis vérifier son format
python3 scripts/personal-trainer.py publish --draft "/CHEMIN/PRIVE/brouillon.txt"

# Après validation explicite, publier dans Apple Notes
python3 scripts/personal-trainer.py publish --draft "/CHEMIN/PRIVE/brouillon.txt" --apply
```

Si tu modifies la note publiée sur iPhone (`Statut: terminée` et résultats), le prochain `sync --apply` détecte le changement. Le script **ne remplace jamais** une note Apple existante. Publier à nouveau le même brouillon avec `--apply` renvoie `already_exists` lorsque son SC-ID est trouvé.

## Format des notes

Les noms et valeurs de statut ci-dessous restent en français, car le code les attend ainsi. Traduire la documentation ne modifie pas le mécanisme de lecture.

### Profil et objectifs

Crée une note nommée exactement `Profil & Objectifs`. Une note `Programme` est facultative. Inclus uniquement les données personnelles nécessaires.

### Séance

Le titre doit commencer par une date ISO, par exemple `2026-11-10 — Haut du corps`. Pour les nouvelles séances créées par Codex, conserve la ligne `SC-ID: sc-...` inchangée.

Après avoir terminé une séance prévue, saisis les résultats et remplace `Statut: prévue` par `Statut: terminée` **dans Apple Notes**.

Les anciennes notes sans statut sont marquées `non_confirmee`. Le système ne suppose pas qu'elles ont été réalisées.

## Configuration

Variables d'environnement :

```bash
export PERSONAL_TRAINER_ACCOUNT="iCloud"
export PERSONAL_TRAINER_FOLDER="Sport"
# Par défaut : sport/ à la racine du projet ; un emplacement hors dépôt est possible
# export PERSONAL_TRAINER_PRIVATE_DIR="$HOME/Library/Application Support/personal-trainer"
```

## Tests Mac — indispensables avant utilisation réelle

1. Dans Apple Notes (compte iCloud), crée `personal-trainer-Test` avec deux notes fictives : `Profil & Objectifs` et `2026-11-09 — Test`.
2. Dans Terminal, lance `export PERSONAL_TRAINER_FOLDER=personal-trainer-Test`.
3. Lance `sync --apply` deux fois et vérifie que la deuxième exécution indique `unchanged`.
4. Modifie la note de test sur iPhone, attends la synchronisation iCloud, puis vérifie qu'un nouvel import indique `changed`.
5. Crée un brouillon avec `new-draft`, modifie-le localement, puis publie dans le dossier de test **après validation**.
6. Relance `publish --apply` pour le même brouillon : il doit renvoyer `already_exists`, sans doublon.
7. Relis la note publiée sur iPhone et vérifie les sauts de ligne et les caractères accentués. Le pont JXA peut nécessiter des adaptations selon la version de Notes/macOS.
8. Une fois les tests réussis, rétablis `PERSONAL_TRAINER_FOLDER=Sport`.

## Confidentialité et limites

- Les imports sont stockés dans `sport/notes.json` et les brouillons dans `sport/drafts/`. Git ignore `sport/` et le garde de commit le refuse.
- Les anciens fichiers dans `~/Library/Application Support/personal-trainer/` ne sont pas déplacés automatiquement. Le prochain `sync --apply` crée le cache au nouvel emplacement, sauf si `PERSONAL_TRAINER_PRIVATE_DIR` est défini.
- Le hook Git utilise une liste blanche de chemins, mais ne peut pas empêcher de copier du contenu sensible dans un fichier source autorisé. Vérifie toujours `git diff --cached`.
- Le cache local est un instantané : il conserve les notes disparues, les marque `missing` et les exclut du contexte actif. Une suppression définitive nécessite aussi de traiter les copies locales et sauvegardes.
- Le cache est en clair dans `sport/` par défaut (permissions des fichiers 0600, des dossiers 0700). Utilise FileVault et une politique de sauvegarde adaptée.
- Faire analyser le contexte par Codex peut transmettre les données au fournisseur du modèle. Garder les données hors de Git ne les garde pas hors du service d'IA.
- L'accès à Apple Notes via JXA n'est pas une API officielle stable. Vérifie les permissions, les comptes, les notes verrouillées et le comportement sur ta version de macOS.
- Le script renvoie uniquement du texte ; les contenus enrichis nécessiteraient une V2.
- La détection des doublons lors de la publication dépend du marqueur `SC-ID`. Si tu le modifies ou le supprimes dans Apple Notes, cette détection n'est plus garantie.
- Les délais de synchronisation iCloud peuvent donner l'impression qu'une note existante est absente. Ne tente pas de la créer à nouveau avant la fin de la synchronisation de Notes sur le Mac.
