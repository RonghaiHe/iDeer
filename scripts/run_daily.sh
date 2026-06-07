#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

if [ -f .env ]; then
  set -a
  . ./.env
  set +a
fi

if [ -n "${PYTHON_BIN:-}" ]; then
  PYTHON_BIN="$PYTHON_BIN"
elif [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python3)"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="$(command -v python)"
else
  echo "No usable Python interpreter found." >&2
  exit 1
fi
# resolve weekly / daily sources based on current day of week
WEEKLY_DAY="${WEEKLY_DAY:-Monday}"
WEEKLY_SOURCES="${WEEKLY_SOURCES:-}"

# map day name -> number (1=Monday .. 7=Sunday)
day_of_week() {
  case "$(echo "$1" | tr '[:upper:]' '[:lower:]')" in
    monday)    echo 1 ;;
    tuesday)   echo 2 ;;
    wednesday) echo 3 ;;
    thursday)  echo 4 ;;
    friday)    echo 5 ;;
    saturday)  echo 6 ;;
    sunday)    echo 7 ;;
    *)         echo 1 ;;
  esac
}

TODAY_NUM=$(date +%u)
WEEKLY_NUM=$(day_of_week "$WEEKLY_DAY")

if [ -n "$WEEKLY_SOURCES" ] && [ "$TODAY_NUM" -eq "$WEEKLY_NUM" ]; then
  DAILY_SOURCES="${DAILY_SOURCES:-arxiv semanticscholar huggingface rss}"
  SOURCES=(${DAILY_SOURCES} ${WEEKLY_SOURCES})
  echo "[Schedule] Weekly day ($WEEKLY_DAY) — running daily + weekly sources"
else
  SOURCES=(${DAILY_SOURCES:-arxiv semanticscholar huggingface rss})
  echo "[Schedule] Non-weekly day — running daily sources only"
fi
ARXIV_CATEGORIES=(${ARXIV_CATEGORIES:-cs.AI cs.CL cs.LG})
GH_LANGUAGES=(${GH_LANGUAGES:-all})
HF_CONTENT_TYPES=(${HF_CONTENT_TYPES:-papers})
RSS_URLS=(${RSS_URLS:-https://imjuya.github.io/juya-ai-daily/rss.xml})
IDEA_ARGS=()
REPORT_ARGS=()
SS_QUERY_ARGS=()
SS_FIELD_ARGS=()
SOURCE_EMAIL_ARGS=()

if [ -n "${SS_QUERIES:-}" ]; then
  IFS='|' read -r -a SS_QUERY_VALUES <<< "${SS_QUERIES}"
  SS_QUERY_ARGS=(--ss_queries "${SS_QUERY_VALUES[@]}")
fi

if [ -n "${SS_FIELDS_OF_STUDY:-Computer Science}" ]; then
  IFS='|' read -r -a SS_FIELD_VALUES <<< "${SS_FIELDS_OF_STUDY:-Computer Science}"
  SS_FIELD_ARGS=(--ss_fields_of_study "${SS_FIELD_VALUES[@]}")
fi

if [ "${GENERATE_IDEAS:-0}" = "1" ]; then
  IDEA_ARGS+=(
    --generate_ideas
    --researcher_profile "${RESEARCHER_PROFILE:-profiles/researcher_profile.md}"
    --idea_min_score "${IDEA_MIN_SCORE:-7}"
    --idea_max_items "${IDEA_MAX_ITEMS:-15}"
    --idea_count "${IDEA_COUNT:-5}"
  )
fi

if [ "${GENERATE_REPORT:-0}" = "1" ]; then
  REPORT_ARGS+=(--generate_report)
  if [ -n "${REPORT_PROFILE_FILE:-}" ]; then
    REPORT_ARGS+=(--report_profile "${REPORT_PROFILE_FILE}")
  fi
  if [ -n "${REPORT_TITLE:-}" ]; then
    REPORT_ARGS+=(--report_title "${REPORT_TITLE}")
  fi
  REPORT_ARGS+=(
    --report_min_score "${REPORT_MIN_SCORE:-4.0}"
    --report_max_items "${REPORT_MAX_ITEMS:-18}"
    --report_theme_count "${REPORT_THEME_COUNT:-4}"
    --report_prediction_count "${REPORT_PREDICTION_COUNT:-4}"
    --report_idea_count "${REPORT_IDEA_COUNT:-4}"
  )
  if [ "${SEND_REPORT_EMAIL:-0}" = "1" ]; then
    REPORT_ARGS+=(--send_report_email)
  fi
fi

if [ "${SKIP_SOURCE_EMAILS:-0}" = "1" ]; then
  SOURCE_EMAIL_ARGS+=(--skip_source_emails)
fi

ZOTERO_ARGS=()
if [ "${ZOTERO_ASSIST_SELECT:-0}" = "1" ]; then
  ZOTERO_ARGS+=(--zotero_assist_select)
fi

"$PYTHON_BIN" main.py \
  --sources "${SOURCES[@]}" \
  --description "${DESCRIPTION_FILE:-profiles/description.txt}" \
  --num_workers "${NUM_WORKERS:-8}" \
  --temperature "${TEMPERATURE:-0.5}" \
  --save \
  --arxiv_categories "${ARXIV_CATEGORIES[@]}" \
  --arxiv_max_entries "${ARXIV_MAX_ENTRIES:-100}" \
  --arxiv_max_papers "${ARXIV_MAX_PAPERS:-60}" \
  --ss_max_results "${SS_MAX_RESULTS:-60}" \
  --ss_max_papers "${SS_MAX_PAPERS:-30}" \
  --ss_year "${SS_YEAR:-}" \
  --ss_api_key "${SS_API_KEY:-}" \
  "${SS_QUERY_ARGS[@]}" \
  "${SS_FIELD_ARGS[@]}" \
  --gh_languages "${GH_LANGUAGES[@]}" \
  --gh_since "${GH_SINCE:-daily}" \
  --gh_max_repos "${GH_MAX_REPOS:-30}" \
  --hf_content_type "${HF_CONTENT_TYPES[@]}" \
  --hf_max_papers "${HF_MAX_PAPERS:-30}" \
  --hf_max_models "${HF_MAX_MODELS:-15}" \
  --rss_urls "${RSS_URLS[@]}" \
  --rss_max_items "${RSS_MAX_ITEMS:-30}" \
  "${SOURCE_EMAIL_ARGS[@]}" \
  "${REPORT_ARGS[@]}" \
  "${IDEA_ARGS[@]}" \
  "${ZOTERO_ARGS[@]}"
