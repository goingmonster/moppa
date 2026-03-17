import requests
import json

url = "http://192.168.1.218:1007/api/generate"

headers = {
    "accept": "application/json",
    "Content-Type": "application/json"
}

payload = {
    "sources": [
      {
        "id":"1122",
        "title": "伊朗新总统上任后首次对以色列发表强硬声明",
        "content": "2026年3月，伊朗新任总统在就职典礼上发表讲话，称将坚决捍卫国家利益，并对以色列发出严厉警告。他表示伊朗不会在核问题上做出让步，同时呼吁地区国家团结一致对抗外部干涉。",
        "input_type": "news",
        "url": "https://example.com/article/123"
      }
    ],
    "question_templates": [
      {
        "domain": "军事行动",
        "templates": [
          {
            "id": "M01-L2",
            "template": "{行为体} 在 {截止日期} 前对 {目标} 最可能采取以下哪种打击方式？",
            "level": "L2",
            "candidate_answers": "A. 有人/无人航空器空袭 B. 远程导弹精确打击 C. 无人机群饱和攻击 D. 特种部队地面破坏",
            "options_type": "fixed",
            "event_type": "军事打击"
          }
        ]
      },
      {
        "domain": "外交",
        "templates": [
          {
            "id": "D01-L1",
            "template": "{国家A}是否会在{截止日期}前与{国家B}进行直接外交对话？",
            "level": "L1",
            "candidate_answers": "A:是 B:否",
            "options_type": "fixed",
            "event_type": "外交对话"
          }
        ]
      }
    ],
    "skip_filter": False,
    "skip_dedup": False
  }

try:
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()  # 如果请求失败会抛异常

    print("Status Code:", response.status_code)
    print("Response JSON:")
    print(json.dumps(response.json(), ensure_ascii=False, indent=2))

except requests.exceptions.RequestException as e:
    print("Request failed:", e)