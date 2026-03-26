import requests

BASE_URL = "http://172.16.18.11:18081"
TOKEN = "sk-84bdefb1854334cf84dcc0b6bb2c0d530d027c48"
HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json",
}

# ---- 1. 提交预测 ----
submit_payload = {
    "id": "1aa06bcc-cd9f-46eb-bb35-5c5e607bf139",
    "question": "这是一个测试问题",
    "model_name": "test-model-v1",
    "answer": "是",
    "reason": "基于当前情报分析，事件大概率会发生",
    "confidence": 85,
    "evidence": [
        {"url": "https://example.com/news1", "content": "新闻证据1：相关报道"},
        {"url": "https://example.com/news2", "content": "新闻证据2：专家分析"},
    ],
}

resp = requests.post(f"{BASE_URL}/agent-predictions/submit", json=submit_payload, headers=HEADERS, verify=False)
print(f"[提交预测] status={resp.status_code}")
print(f"[提交预测] body={resp.json()}")
print()

# ---- 2. 重复提交（测试 upsert 更新）----
submit_payload["answer"] = "否"
submit_payload["reason"] = "经过重新分析，改变预测结果"
submit_payload["confidence"] = 70

resp = requests.post(f"{BASE_URL}/agent-predictions/submit", json=submit_payload, headers=HEADERS, verify=False)
print(f"[重复提交] status={resp.status_code}")
print(f"[重复提交] body={resp.json()}")
print()

# ---- 3. 查询该问题下的所有 Agent 预测 ----
# 注意：这个接口需要 admin JWT，API Key 不行，这里用 API Key 测试会返回 401/403
resp = requests.get(
    f"{BASE_URL}/agent-predictions/question/1aa06bcc-cd9f-46eb-bb35-5c5e607bf139",
    headers=HEADERS,
    verify=False,
)
print(f"[查询预测] status={resp.status_code}")
try:
    print(f"[查询预测] body={resp.json()}")
except Exception:
    print(f"[查询预测] body={resp.text}")
