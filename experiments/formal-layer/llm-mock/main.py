"""
LLM モック: 自然言語から構造化データへの変換例

このモックは、実際の LLM API の代わりに、簡単なルールベースで
自然言語を構造化データ（JSON）に変換します。

実際の実装では、OpenAI API や Anthropic API などを使用します。
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
import re

app = FastAPI(title="LLM Mock API", version="1.0.0")


class NaturalLanguageRequest(BaseModel):
    text: str = Field(..., description="Natural language input")


class BillingQueryResponse(BaseModel):
    customerId: str
    mode: str  # "open" | "all"


class PolicyRequestResponse(BaseModel):
    customer_tier: str
    issue: str


class KGPathResponse(BaseModel):
    path_type: str  # "sla" | "contract" | "plan" | "full"


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "llm-mock"}


@app.post("/extract-billing-query", response_model=BillingQueryResponse)
async def extract_billing_query(request: NaturalLanguageRequest):
    """
    自然言語から BillingQuery を抽出
    
    例:
    - "CUST-123 の未処理請求を取得して" → {"customerId": "CUST-123", "mode": "open"}
    - "CUST-123 の全請求を見せて" → {"customerId": "CUST-123", "mode": "all"}
    """
    text = request.text.lower()
    
    # 顧客IDを抽出（簡易版）
    customer_match = re.search(r'cust-(\d+)', text, re.IGNORECASE)
    customer_id = customer_match.group(0).upper() if customer_match else "CUST-123"
    
    # モードを判定
    if any(word in text for word in ["未処理", "open", "未完了", "pending"]):
        mode = "open"
    else:
        mode = "all"
    
    return BillingQueryResponse(
        customerId=customer_id,
        mode=mode
    )


@app.post("/extract-policy-request", response_model=PolicyRequestResponse)
async def extract_policy_request(request: NaturalLanguageRequest):
    """
    自然言語から PolicyRequest を抽出
    
    例:
    - "プラチナ顧客のクリティカルな問題" → {"customer_tier": "Platinum", "issue": "Critical"}
    - "重要なお客様にとって重要度が高い問題" → {"customer_tier": "Platinum", "issue": "High"}
    """
    text = request.text.lower()
    
    # 顧客ティアを抽出
    if "platinum" in text or "プラチナ" in text:
        tier = "Platinum"
    elif "重要" in text or "vip" in text or "premium" in text:
        # 重要なお客様 → Platinum として扱う
        tier = "Platinum"
    elif "silver" in text or "シルバー" in text:
        tier = "Silver"
    else:
        tier = "Bronze"
    
    # 課題の重要度を抽出
    if "critical" in text or "クリティカル" in text or "緊急" in text:
        issue = "Critical"
    elif "high" in text or "高" in text:
        issue = "High"
    elif "medium" in text or "中" in text:
        issue = "Medium"
    else:
        issue = "Low"
    
    return PolicyRequestResponse(
        customer_tier=tier,
        issue=issue
    )


@app.post("/extract-kg-path", response_model=KGPathResponse)
async def extract_kg_path(request: NaturalLanguageRequest):
    """
    自然言語から KG の経路タイプを抽出
    
    例:
    - "顧客のSLA情報が知りたい" → {"path_type": "sla"}
    - "契約情報だけ見たい" → {"path_type": "contract"}
    - "プラン情報も含めて全部見たい" → {"path_type": "full"}
    - "SLA情報を教えて" → {"path_type": "sla"}
    """
    text = request.text.lower()
    
    # SLA関連のキーワード
    if any(word in text for word in ["sla", "優先度", "priority", "response_time", "応答時間"]):
        path_type = "sla"
    # 契約関連のキーワード
    elif any(word in text for word in ["contract", "契約", "契約情報", "契約だけ"]):
        path_type = "contract"
    # プラン関連のキーワード
    elif any(word in text for word in ["plan", "プラン", "プラン情報", "プランだけ"]):
        path_type = "plan"
    # 全部、全て、完全などのキーワード
    elif any(word in text for word in ["full", "全部", "全て", "完全", "すべて", "all"]):
        path_type = "full"
    else:
        # デフォルトはSLA（最も一般的なクエリ）
        path_type = "sla"
    
    return KGPathResponse(path_type=path_type)


@app.post("/format-response")
async def format_response(data: dict):
    """
    構造化データから自然言語の応答を生成
    
    例:
    - {"customer_id": "CUST-123", "priority": "Medium", "assigned_agent": "Agent1", "billing_count": 1}
      → "CUST-123 の優先度は Medium です。Agent1 に割り当てました（未処理請求 1 件）。"
    """
    # 簡易的なテンプレートベースの応答生成
    if "customer_id" in data and "priority" in data and "assigned_agent" in data:
        billing_suffix = ""
        if "billing_count" in data:
            try:
                count = int(data["billing_count"])
                billing_suffix = f"（未処理請求 {count} 件）"
            except (ValueError, TypeError):
                # billing_count が数値でない場合は無視
                billing_suffix = ""
        return {
            "text": f"{data['customer_id']} の優先度は {data['priority']} です。{data['assigned_agent']} に割り当てました{billing_suffix}。",
            "data": data,
        }
    elif "priority" in data:
        return {
            "text": f"優先度は {data['priority']} です。",
            "data": data
        }
    elif "results" in data:
        count = len(data["results"]) if isinstance(data["results"], list) else 0
        return {
            "text": f"{count} 件の結果が見つかりました。",
            "data": data
        }
    else:
        return {
            "text": "処理が完了しました。",
            "data": data
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

