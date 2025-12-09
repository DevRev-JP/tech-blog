"""
ルールエンジン（ポリシーレイヤ）の最小構成例

記事「LLM/RAG の曖昧性を抑える『形式レイヤ』の実装ガイド」の
ハンズオンセクション「OPA（Open Policy Agent）の最小例」に対応する例です。

実行方法:
    # OPA サーバーを起動（別ターミナル）
    docker run -p 8181:8181 -v $(pwd):/policies openpolicyagent/opa:latest run --server --addr 0.0.0.0:8181 /policies
    
    # このスクリプトを実行
    python query.py
"""

import json
import httpx

OPA_URL = "http://localhost:8181"

def evaluate_policy():
    """記事で説明されているポリシー評価を実行"""
    # 記事の例: input.json の内容
    input_data = {
        "customer_tier": "Platinum",
        "issue": "Critical"
    }
    
    # OPA にポリシーを評価してもらう
    response = httpx.post(
        f"{OPA_URL}/v1/data/sla/priority",
        json={"input": input_data}
    )
    
    result = response.json()
    priority = result.get("result", "Low")
    
    print("入力:", json.dumps(input_data, indent=2, ensure_ascii=False))
    print("判定結果:", priority)

if __name__ == "__main__":
    evaluate_policy()

