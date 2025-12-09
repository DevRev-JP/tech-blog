from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from ortools.sat.python import cp_model

app = FastAPI(title="Optimization Layer API", version="1.0.0")


class TaskAssignmentRequest(BaseModel):
    agents: List[str] = Field(..., description="List of agent IDs")
    tasks: List[str] = Field(..., description="List of task IDs")
    max_tasks_per_agent: int = Field(2, description="Maximum tasks per agent")
    constraints: Optional[Dict[str, Any]] = Field(None, description="Additional constraints")


class TaskAssignmentResponse(BaseModel):
    assignments: List[Dict[str, str]]
    status: str
    solver_time: float


@app.get("/healthz")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "optimization-layer"}


@app.post("/assign", response_model=TaskAssignmentResponse)
async def assign_tasks(request: TaskAssignmentRequest):
    """
    Solve task assignment problem using OR-Tools constraint solver.
    
    Constraints:
    - Each task must be assigned to exactly one agent
    - Each agent can handle at most max_tasks_per_agent tasks
    """
    try:
        model = cp_model.CpModel()
        agents = request.agents
        tasks = request.tasks
        max_tasks = request.max_tasks_per_agent
        
        # Decision variables: x[i][j] = 1 if agent i is assigned to task j
        x = {}
        for i, agent in enumerate(agents):
            for j, task in enumerate(tasks):
                x[(i, j)] = model.NewBoolVar(f"x_{agent}_{task}")
        
        # Constraint 1: Each task must be assigned to exactly one agent
        for j in range(len(tasks)):
            model.Add(sum(x[(i, j)] for i in range(len(agents))) == 1)
        
        # Constraint 2: Each agent can handle at most max_tasks tasks
        for i in range(len(agents)):
            model.Add(sum(x[(i, j)] for j in range(len(tasks))) <= max_tasks)
        
        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = 10.0  # Time limit
        
        import time
        start_time = time.time()
        status = solver.Solve(model)
        solver_time = time.time() - start_time
        
        if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
            assignments = []
            for i, agent in enumerate(agents):
                for j, task in enumerate(tasks):
                    if solver.Value(x[(i, j)]) == 1:
                        assignments.append({
                            "agent": agent,
                            "task": task
                        })
            
            status_str = "OPTIMAL" if status == cp_model.OPTIMAL else "FEASIBLE"
            return TaskAssignmentResponse(
                assignments=assignments,
                status=status_str,
                solver_time=solver_time
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Solver could not find a solution. Status: {status}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/schedule")
async def schedule_example():
    """
    Example scheduling problem: Assign 3 tasks to 2 agents.
    This demonstrates the OR-Tools constraint solver.
    """
    request = TaskAssignmentRequest(
        agents=["A", "B"],
        tasks=["T1", "T2", "T3"],
        max_tasks_per_agent=2
    )
    return await assign_tasks(request)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

