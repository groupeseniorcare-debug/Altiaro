#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Reprise de projet (état des lieux + fix gating étape 1 + audits chantiers 5/6/7).
  Bug rapporté : "étape 1 complète mais étape 2 bloquée" malgré analyse pricing effectuée.

backend:
  - task: "Fix gating étape 1 (pricing) — reconnaître pricing_analysis ET quick_scans"
    implemented: true
    working: true
    file: "backend/routes/journey_gating.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
      - working: true
        agent: "main"
        comment: |
          Fix validé : _check_pricing accepte site.design.pricing_analysis.generated_at
          OU ≥1 quick_scan avec site_id (peu importe verdict).

  - task: "Chantier 5 — seo_countries dissocié des ads_countries"
    implemented: true
    working: true
    file: "backend/seo_constants.py + routes/sites.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          - backend/seo_constants.py : source unique (ALL_SUPPORTED_COUNTRIES=11,
            ALL_SUPPORTED_LANGS=6, LANG_BY_COUNTRY, CURRENCY_BY_COUNTRY,
            get_seo_countries(), get_seo_langs(), filter_supported()).
          - sites.py : seo_countries ajouté dans SiteCreateInput/SiteUpdateInput.
            Défaut à la création = ALL_SUPPORTED_COUNTRIES (11 pays).
            Endpoints GET /sites/{id}/seo-settings et PATCH /sites/{id}/seo-settings
            (concepteur & admin). PATCH avec null = reset au défaut.
          - Fallback runtime : anciens sites sans seo_countries → get_seo_countries()
            renvoie ALL_SUPPORTED_COUNTRIES. Aucune migration DB nécessaire.
          Tests curl OK sur site Fauteuil releveur (ads DE/FR, mais SEO
          passe de 2 hreflang à 6 hreflang automatiquement).

  - task: "Chantier 5 — Sitemap + hreflang + llms.txt multi-langue"
    implemented: true
    working: true
    file: "backend/routes/seo.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          - sitemap.xml itère sur get_seo_langs(site) au lieu de selected_countries.
            Site Fauteuil releveur (ads DE/FR) passe de 2 hreflang à 6 hreflang.
          - robots.txt liste maintenant llms.txt + llms-full.txt pour chaque langue
            non-FR en plus des defaults.
          - llms.txt supporte ?lang=fr|de|en|nl|it|es via LLMS_LABELS dict avec
            6 traductions complètes des sections génériques (summary, keys, FAQ).
            URL des pages + produits incluent ?lang=xx pour guider les moteurs IA.
          - llms-full.txt supporte ?lang=xx avec lookup dans post.translations[lg]
            pour les articles traduits (sinon fallback contenu source).
          - merchant-feed.xml reste volontairement sur ads_countries (quotas
            Google Merchant). Utilise CURRENCY_BY_COUNTRY centralisé.
          Tests curl OK : langues DE/FR/NL/IT/ES/EN servies correctement.

  - task: "Chantier 5 — Blog i18n (translations + auto-translate background)"
    implemented: true
    working: "NA"
    file: "backend/routes/blog_posts.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: "NA"
        agent: "main"
        comment: |
          - BlogPostInput.translations = Optional[dict] (structure
            {lang: {title, excerpt, body, translated_at}}).
          - POST /sites/{id}/blog-posts/{slug}/translate : endpoint manuel
            (data.langs optionnel, data.overwrite pour retraduire).
          - create_blog_post + update_blog_post : BackgroundTasks.add_task
            pour auto-translate en background sur TOUTES les langues seo_countries
            manquantes. Content changed (title/excerpt/body) → invalide les
            translations existantes et retranslate.
          - Throttling via asyncio.Semaphore(1) pour ne pas exploser Claude.
          - Best-effort : si EMERGENT_LLM_KEY manquant ou erreur Claude, log + skip.
          Non-testé en live (pas d'article actuellement en DB). À vérifier
          par le user à la 1re création d'article en prod.

  - task: "Chantier 5 — Alignement sourcing.py (_translate_product → seo_countries)"
    implemented: true
    working: true
    file: "backend/routes/sourcing.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: true
        agent: "main"
        comment: |
          Import route utilise désormais get_seo_langs(site) pour déterminer
          les langues cibles de _translate_product (au lieu de dériver depuis
          selected_countries). Conséquence : import d'un produit traduit
          directement dans les 6 langues SEO, pas seulement les langues Ads.

metadata:
  created_by: "main_agent"
  version: "1.2"
  test_sequence: 0
  run_ui: false

test_plan:
  current_focus:
    - "Chantier 5 — seo_countries dissocié des ads_countries"
    - "Chantier 5 — Sitemap + hreflang + llms.txt multi-langue"
    - "Chantier 5 — Blog i18n (translations + auto-translate background)"
    - "Chantier 5 — Alignement sourcing.py (_translate_product → seo_countries)"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: |
      Chantier 5 livré. Tests curl manuels OK (sitemap 6 hreflang, robots multi-lang,
      llms.txt?lang=de allemand valide, PATCH seo-settings + reset OK).
      Tests Claude translate non-exécutés (pas d'article en DB, coût LLM).
      En attente validation user avant Chantier 6.
