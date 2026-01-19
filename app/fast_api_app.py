# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import google.auth
from fastapi import FastAPI, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from google.adk.cli.fast_api import get_fast_api_app
from google.cloud import logging as google_cloud_logging

from app.app_utils.telemetry import setup_telemetry
from app.app_utils.typing import Feedback

setup_telemetry()
_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)
allow_origins = (
    os.getenv("ALLOW_ORIGINS", "").split(",") if os.getenv("ALLOW_ORIGINS") else None
)

# Artifact bucket for ADK (created by Terraform, passed via env var)
logs_bucket_name = os.environ.get("LOGS_BUCKET_NAME")

AGENT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# In-memory session configuration - no persistent storage
session_service_uri = None

artifact_service_uri = f"gs://{logs_bucket_name}" if logs_bucket_name else None

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    web=True,
    artifact_service_uri=artifact_service_uri,
    allow_origins=allow_origins,
    session_service_uri=session_service_uri,
    session_service_uri=session_service_uri,
    otel_to_cloud=True,
)

# --- 新增：挂载静态文件（你的漂亮前端）---
# 确保目录存在
os.makedirs(os.path.join(AGENT_DIR, "app/static"), exist_ok=True)
app.mount("/static", StaticFiles(directory=os.path.join(AGENT_DIR, "app/static")), name="static")

@app.get("/chat")
async def read_chat_ui():
    return FileResponse(os.path.join(AGENT_DIR, "app/static/index.html"))

# --- 新增：Agent 列表接口（给前端下拉框用）---
@app.get("/available_agents")
def get_available_agents():
    # 动态获取 root_agent 下的子代理
    # 注意：这里我们手动返回一些元数据，为了 Demo 好看
    return [
        {"name": "lingxing_expert", "description": "领星 ERP 财务分析专家", "icon": "📊"},
        {"name": "search_agent", "description": "实时联网信息检索专家", "icon": "🔍"},
        {"name": "database_agent", "description": "MongoDB 数据库操作专家", "icon": "💾"},
        {"name": "root_agent", "description": "总控助手", "icon": "🤖"}
    ]

# --- 新增：简化的运行接口（为了给前端 fetch 用）---
from google.adk.runner import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from app.agent import root_agent

# 简单的内存 Session，生产环境建议用 Redis/Firestore
ui_session_service = InMemorySessionService()

class ChatRequest(BaseModel):
    user_id: str
    session_id: str
    input: str

@app.post("/chat/run")
async def run_chat(request: ChatRequest = Body(...)):
    # 1. 确保 Session 存在
    try:
        await ui_session_service.get_session(request.session_id)
    except Exception:
        await ui_session_service.create_session(
            app_name="app", user_id=request.user_id, session_id=request.session_id
        )

    # 2. 初始化 Runner
    runner = Runner(
        agent=root_agent, 
        app_name="app", 
        session_service=ui_session_service
    )

    # 3. 运行并等待最终结果
    final_text = ""
    async for event in runner.run_async(
        user_id=request.user_id,
        session_id=request.session_id,
        new_message=genai_types.Content(
            role="user", 
            parts=[genai_types.Part.from_text(text=request.input)]
        ),
    ):
        if event.is_final_response():
            final_text = event.content.parts[0].text
            
    return {"output": final_text}
app.title = "my-agent"
app.description = "API for interacting with the Agent my-agent"


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    """Collect and log feedback.

    Args:
        feedback: The feedback data to log

    Returns:
        Success message
    """
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}


# Main execution
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
