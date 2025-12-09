"""
アンチパターン: if/else ベタ書きのポリシー判定

この実装は、ポリシーロジックを if/else で直接書いています。
問題点:
- ポリシーの変更にコード変更が必要
- テストが困難
- 複雑な条件の組み合わせでバグが発生しやすい
- 監査や検証が困難
"""
from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Unsafe Policy Layer (Anti-pattern)", version="1.0.0")


class PolicyRequest(BaseModel):
    customer_tier: str = Field(..., description="Customer tier")
    issue: str = Field(..., description="Issue severity")


@app.get("/healthz")
async def health_check():
    return {"status": "ok", "service": "unsafe-policy-layer", "warning": "This is an anti-pattern example!"}


@app.post("/evaluate")
async def evaluate_policy(request: PolicyRequest):
    """
    危険な実装: if/else ベタ書きのポリシー判定
    
    問題点:
    - ポリシーの変更にコード変更が必要
    - 条件の組み合わせが複雑になるとバグが発生しやすい
    - 監査や検証が困難
    - ルールエンジン（OPA）を使うべき
    """
    # ⚠️ 危険: if/else ベタ書き
    if request.customer_tier == "Platinum" and request.issue == "Critical":
        priority = "High"
    elif request.customer_tier == "Gold" and request.issue == "Critical":
        priority = "Medium"
    elif request.customer_tier == "Platinum" and request.issue == "High":
        priority = "Medium"
    else:
        priority = "Low"
    
    return {
        "input": {
            "customer_tier": request.customer_tier,
            "issue": request.issue
        },
        "priority": priority,
        "policy_used": "hardcoded if/else",
        "warning": "This is unsafe! Use a policy engine (OPA) instead."
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

