
uvicorn chat311.app.app:app --port 5555

curl -X POST -H "Content-Type: application/json" -d '{"question":"Are iguanas illegal as pets in Miami?"}' localhost:5555/api/ask; echo

watch -n 0.5  -exec bash -c 'curl localhost:5555/api/poll?session_id=1ebf8f98-3469-4006-9892-bc4252e1f15b | jq'