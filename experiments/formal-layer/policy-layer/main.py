import os
from typing import Dict, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import httpx

app = FastAPI(title="Policy Layer API", version="1.0.0")

OPA_URL = os.getenv("OPA_URL", "http://opa:8181")


class PolicyRequest(BaseModel):
    customer_tier: str = Field(..., description="Customer tier: Platinum, Gold, Silver, Bronze")
    issue: str = Field(..., description="Issue severity: Critical, High, Medium, Low")


class PolicyResponse(BaseModel):
    input: Dict[str, str]
    priority: str
    policy_used: str


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OPA_URL}/health")
            if response.status_code == 200:
                return {"status": "ok", "service": "policy-layer", "opa": "connected"}
            else:
                return {"status": "warning", "service": "policy-layer", "opa": "disconnected"}
    except Exception as e:
        return {"status": "error", "service": "policy-layer", "error": str(e)}


@app.on_event("startup")
async def startup_event():
    """Load policies into OPA on startup."""
    import asyncio
    # Wait for OPA to be ready
    await asyncio.sleep(2)
    
    try:
        # Load SLA policy from app directory
        policy_paths = [
            "/app/policies/sla.rego",
            "./policies/sla.rego",
            "policies/sla.rego"
        ]
        
        policy_content = None
        for policy_path in policy_paths:
            if os.path.exists(policy_path):
                with open(policy_path, "r") as f:
                    policy_content = f.read()
                break
        
        if policy_content:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.put(
                    f"{OPA_URL}/v1/policies/sla",
                    content=policy_content,
                    headers={"Content-Type": "text/plain"}
                )
                if response.status_code in [200, 204]:
                    print("✅ SLA policy loaded into OPA")
                else:
                    print(f"⚠️  Failed to load policy: {response.status_code} - {response.text}")
        else:
            print("⚠️  SLA policy file not found")
    except Exception as e:
        print(f"⚠️  Policy loading error (OPA may not be ready): {e}")


@app.post("/evaluate", response_model=PolicyResponse)
async def evaluate_policy(request: PolicyRequest):
    """
    Evaluate policy using OPA.
    
    Example: Determine SLA priority based on customer tier and issue severity.
    """
    try:
        input_data = {
            "customer_tier": request.customer_tier,
            "issue": request.issue
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{OPA_URL}/v1/data/sla/priority",
                json={"input": input_data}
            )
            
            if response.status_code != 200:
                raise HTTPException(
                    status_code=500,
                    detail=f"OPA evaluation failed: {response.text}"
                )
            
            result = response.json()
            priority = result.get("result", "Low")
        
        return PolicyResponse(
            input=input_data,
            priority=priority,
            policy_used="sla.rego"
        )
    except httpx.RequestError as e:
        raise HTTPException(
            status_code=503,
            detail=f"OPA connection error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/policies")
async def list_policies():
    """List available policies."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{OPA_URL}/v1/policies")
            if response.status_code == 200:
                policies = response.json()
                return {"policies": policies.get("result", [])}
            else:
                return {"policies": [], "error": "Failed to fetch policies"}
    except Exception as e:
        return {"policies": [], "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

