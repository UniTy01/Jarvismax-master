# JarvisMax v3 : Le Blueprint "OpenDevin"

## 🎯 Objectif Cible
Transformer JarvisMax d'un système multi-agents statique (où les agents s'exécutent de manière séquentielle ou conditionnelle) en un **Véritable Ingénieur Logiciel Autonome (Devin-like)**. 

Pour atteindre le niveau d'OpenDevin, JarvisMax doit acquérir 5 piliers fondamentaux :
1. **Une Boucle d'Agent Continu (Agent Loop)** : Penser → Agir → Observer → Réfléchir (ReAct), sans limite de tours prédéfinie.
2. **Une Architecture Event-Sourced** : Tout ce qui se passe est un événement. Cela permet le rejeu (Time-Travel) et le streaming temps réel.
3. **Un Environnement d'Exécution Stateful (Sandbox)** : Un terminal persistant (les variables d'environnement et les processus en tâche de fond survivent entre deux commandes) isolé dans un conteneur Docker.
4. **Outils d'Édition et de Navigation Avancés** : Pas de simples `read_file`/`write_file`, mais un véritable éditeur interactif (scroll, goto line, search/replace) et un navigateur (Playwright).
5. **Une Interface Temps Réel (UI)** : Un frontend réactif (WebSockets) affichant le terminal en live, le Workspace et les pensées de l'agent.

---

## 🏗️ Architecture Cible v3

Pour ne pas casser la v2 (qui est une excellente base d'orchestration de tâches), nous allons ajouter une **couche supérieure** dédiée à l'autonomie prolongée.

### Le Flux d'Exécution (Event Stream)
Au lieu d'un `JarvisSession` avec un dictionnaire statique `outputs`, le cœur devient l'`EventStream`.
- **Action** : L'agent décide de faire quelque chose (ex: `TerminalAction(cmd="npm install")`, `EditAction(file="main.py", replace...)`).
- **Observation** : Le système exécute l'action et retourne le résultat (ex: `TerminalObservation(stdout="...", exit_code=0)`).
- **L'Agent** prend l'historique complet des événements et génère la prochaine `Action` jusqu'à émettre une `FinishAction`.

---

## 🗺️ Plan d'Implémentation (Précision Chirurgicale)

Voici les 5 phases d'implémentation ordonnées, conçues pour être intégrées étape par étape.

### Phase 1 : Le Cœur Événementiel (Event Stream & State)
*L'objectif est de remplacer l'état mutable par un flux immuable, pré-requis pour les WebSockets et le Time-Travel.*

1. **Créer `core/events.py`** (Pydantic)
   - Définir `Event` (base), `Action(Event)`, `Observation(Event)`, `StateUpdate(Event)`.
   - Modéliser les actions spécifiques : `TerminalAction`, `BrowserAction`, `FileEditAction`, `TalkAction`.
2. **Créer `core/event_stream.py`**
   - Une classe `EventStream` qui stocke la liste en `append-only`.
   - Méthodes : `add_event()`, `get_events()`, `subscribe(callback)`.
3. **Adapter `JarvisSession` (Backward Compatibility)**
   - Rendre `JarvisSession` capable de proxy-fier ses données vers et depuis l'`EventStream`.

### Phase 2 : Le Sandbox Stateful (Docker PTY)
*Exécuter du code sur l'hôte en production est impensable. Il faut un environnement isolé et persistant.*

1. **Créer `executor/desktop_env/` (Le Sandbox)**
   - Utiliser la librairie Docker (`pip install docker`) pour lancer dynamiquement un conteneur (ex: `python:3.11-slim-bookworm`) par mission.
   - Monter un volume `workspace/` de l'hôte vers `/workspace/` dans le conteneur.
2. **Créer `executor/desktop_env/terminal.py`**
   - Mettre en place une connexion terminal persistante via `pexpect` ou un socket direct.
   - *Important* : Si l'agent tape `cd src`, la prochaine commande doit s'exécuter dans `src` (ce qui n'est pas le cas avec les exécutions `subprocess` isolées actuelles).
   - Capturer le `stdout`, `stderr` et le code de retour pour créer une `TerminalObservation`.
3. **Créer `executor/desktop_env/editor.py`**
   - Implémenter des commandes d'édition chirurgicales (str_replace, insert_at_line, eof_append) plutôt que de réécrire le fichier entier à chaque fois (économie de tokens et réduction d'erreurs).

### Phase 3 : L'Agent Autonome (Devin Loop)
*Remplacer l'exécution en cascade statique par une boucle infinie de réflexion.*

1. **Créer `agents/autonomous/devin_agent.py`**
   - Un prompt système radicalement différent : l'agent reçoit la liste des outils (Terminal, Editor, Browser) sous forme de JSON Schema (Function Calling).
   - L'agent doit **toujours** répondre avec une balise `<thought>...</thought>` suivie d'un appel d'outil JSON.
2. **Créer `core/agent_loop.py`**
   - `while not type(action) is FinishAction and step < max_steps:`
   - Étape A : Appeler le LLM avec l'historique de l'`EventStream`.
   - Étape B : Parser l'`Action`.
   - Étape C : Envoyer au `Sandbox`, récupérer l'`Observation`.
   - Étape D : Ajouter l'`Observation` à l'`EventStream`.
3. **Puglin RAG / Lexical Search (Repo Map)**
   - Donner à l'agent un outil `read_repo_map` qui lui renvoie l'arborescence complète et les signatures de fonctions principales, généré via `tree-sitter`. (Inspiré de Aider / SWE-agent).

### Phase 4 : Interface Utilisateur Temps Réel (WebSockets)
*Sans UI, l'agent opère dans le noir. Il faut pouvoir l'interrompre et le suivre.*

1. **Créer `api/ws.py` (FastAPI WebSockets)**
   - Endpoint `/api/v3/mission/{id}/stream`.
   - Connexion et diffusion (Broadcast) de chaque nouvel événement ajouté à l'`EventStream` vers le client.
2. **Endpoint pour Time-Travel**
   - `POST /api/v3/mission/{id}/rewind` : Troncature de l'`EventStream` jusqu'à un timestamp précis et réinitialisation de l'état du Sandbox au dernier backup connu.
3. **(Optionnel dans l'agent) Créer un Frontend Vite/React**
   - Split screen : À gauche le composant `<Terminal />` branché sur le WS, au centre le `<MonacoEditor />` montrant les fichiers modifiés, à droite le `<Chat />` et les `<thoughts>`.

### Phase 5 : Auto-Évaluation et Handoffs Dynamiques
*Permettre à l'agent principal de déléguer si la tâche est trop pointue.*

1. **Intégration du `MonitoringAgent`**
   - Si l'`AgentLoop` détecte que le Sandbox consomme trop de CPU/RAM, il peut s'auto-réguler.
2. **Dynamic Delegation (Handoff)**
   - Mettre à jour l'agent principal pour qu'il puisse émettre une `DelegateAction(target="scout-research", task="Trouve la documentation de cette lib")`.
   - La sous-tâche ouvre un `EventStream` enfant. Une fois finie, un `DelegationObservation` (le résumé) revient au parent.

---

## 🛠️ Stack Technique Recommandée pour v3

| Composant | Technologie | Justification |
|-----------|-------------|---------------|
| **Event Stream** | Pydantic + SQLite/JSONL | JSONL parfait pour le streaming et le Time-Travel append-only. |
| **Sandbox** | Docker SDK Python (`docker`) | Permet de spin-up/teardown l'environnement en 2 secondes au format IaaS. |
| **Terminal State** | `pexpect` / `ptyprocess` | Conserve l'état (répertoire courant, env vars) entre les frappes. |
| **WebSockets** | FastAPI `WebSocket` | Natif et déjà inclus dans l'architecture v2. |
| **Repo Map** | `tree-sitter` (Python bindings) | Essentiel pour que l'agent comprenne le code sans lire 100% des fichiers. |
| **Model Router** | `litellm` | Standard de l'industrie pour router entre Claude 3.5 Sonnet, GPT-4o, etc. |

---

## 🚦 Critères de Succès pour la v3

Le projet sera officiellement au niveau d'OpenDevin lorsque vous pourrez lancer la commande suivante dans l'API :
`"input": "Crée un projet React avec Vite, ajoute Tailwind, installe un routeur, crée deux pages, lance le serveur et vérifie que tout marche sans erreurs."`

Et que l'agent exécutera de manière autonome :
1. `Terminal`: `npm create vite@latest...` (et attendra que ça finisse)
2. `Terminal`: `cd my-project && npm install`
3. `Editor`: Modification des fichiers pour configurer Tailwind.
4. `Terminal`: Lancement de `npm run dev &`.
5. `Browser`: Visite de `http://localhost:5173` pour vérifier s'il voit la page.
6. `Finish`: "La tâche est terminée avec succès."
