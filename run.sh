export CUSTOM_OPENAI_API_BASE="http://127.0.0.1:8000/v1"
export OPENAI_API_BASE="http://127.0.0.1:8000/v1"
export OPENAI_BASE_URL="http://127.0.0.1:8000/v1"
export OPENAI_API_KEY="dummy"

tau2 run \
  --domain airline \
  --agent-llm "openai//home/ayohanes/models/qwen3.6-35b-a3b" \
  --user-llm "openai//home/ayohanes/models/qwen3.6-35b-a3b" \
  --num-trials 1 \
  --num-tasks 1
