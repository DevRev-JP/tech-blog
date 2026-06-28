"""共通: Neo4j / Ollama / Graphiti 接続と CLI 出力ヘルパー."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from neo4j import GraphDatabase

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULT_LLM_MODEL = "gemma2:2b"

for env_name in (".env", "env.sample"):
    env_path = ROOT / env_name
    if env_path.exists():
        load_dotenv(env_path)
        break


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        print(f"エラー: 環境変数 {name} が未設定です。env.sample を .env にコピーしてください。", file=sys.stderr)
        sys.exit(1)
    return value


def get_neo4j_driver():
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = require_env("NEO4J_PASSWORD")
    return GraphDatabase.driver(uri, auth=(user, password))


def get_llm():
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_LLM_MODEL", DEFAULT_LLM_MODEL)
    return ChatOllama(model=model, base_url=base_url, temperature=0)


def step_print(step: int, total: int, message: str) -> None:
    print(f"\n[Step {step}/{total}] {message}")


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def create_graphiti_client():
    from graphiti_core import Graphiti
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.llm_client.config import DEFAULT_MAX_TOKENS, LLMConfig, ModelSize
    from graphiti_core.llm_client.errors import EmptyResponseError, RateLimitError
    from graphiti_core.llm_client.openai_generic_client import OpenAIGenericClient
    from graphiti_core.prompts.models import Message
    from openai.types.chat import ChatCompletionMessageParam
    import json
    import openai
    import typing
    from pydantic import BaseModel

    class OllamaGraphitiClient(OpenAIGenericClient):
        """Ollama 向け: thinking 無効化 + 空応答時の4回リトライを省略（ローカルでは時間の無駄）."""

        async def generate_response(
            self,
            messages: list[Message],
            response_model: type[BaseModel] | None = None,
            max_tokens: int | None = None,
            model_size: ModelSize = ModelSize.medium,
            group_id: str | None = None,
            prompt_name: str | None = None,
            *,
            attribute_extraction: bool = False,
        ) -> dict[str, typing.Any]:
            from graphiti_core.llm_client.client import get_extraction_language_instruction

            self._apply_attribute_extraction_preamble(messages, attribute_extraction)
            if max_tokens is None:
                max_tokens = self.max_tokens
            if response_model is not None and self.structured_output_mode == "json_object":
                serialized_model = json.dumps(response_model.model_json_schema())
                messages[-1].content += (
                    f"\n\nRespond with a JSON object in the following format:\n\n{serialized_model}"
                )
            messages[0].content += get_extraction_language_instruction(group_id)
            with self.tracer.start_span("llm.generate") as span:
                attributes = {
                    "llm.provider": "openai",
                    "model.size": model_size.value,
                    "max_tokens": max_tokens,
                }
                if prompt_name:
                    attributes["prompt.name"] = prompt_name
                span.add_attributes(attributes)
                try:
                    return await self._generate_response(
                        messages, response_model, max_tokens=max_tokens, model_size=model_size
                    )
                except Exception as e:
                    span.set_status("error", str(e))
                    span.record_exception(e)
                    raise

        async def _generate_response(
            self,
            messages: list[Message],
            response_model: type[BaseModel] | None = None,
            max_tokens: int = DEFAULT_MAX_TOKENS,
            model_size: ModelSize = ModelSize.medium,
        ) -> dict[str, typing.Any]:
            openai_messages: list[ChatCompletionMessageParam] = []
            for m in messages:
                m.content = self._clean_input(m.content)
                if m.role == "user":
                    openai_messages.append({"role": "user", "content": m.content})
                elif m.role == "system":
                    openai_messages.append({"role": "system", "content": m.content})
            disable_think = os.getenv("OLLAMA_DISABLE_THINKING", "true").lower() in (
                "1",
                "true",
                "yes",
            )
            try:
                kwargs: dict = {
                    "model": self.model or "gpt-4.1-mini",
                    "messages": openai_messages,
                    "temperature": self.temperature,
                    "max_tokens": max_tokens,
                    "response_format": self._build_response_format(response_model),
                }
                if disable_think:
                    kwargs["extra_body"] = {"think": False}
                response = await self.client.chat.completions.create(**kwargs)  # type: ignore[arg-type]
                result = response.choices[0].message.content or ""
                if not result:
                    raise EmptyResponseError("LLM returned an empty response")
                return json.loads(self._strip_code_fences(result))
            except openai.RateLimitError as e:
                raise RateLimitError from e
            except Exception as e:
                import logging

                logging.getLogger(__name__).error(f"Error in generating LLM response: {e}")
                raise

    base = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").rstrip("/") + "/v1"
    llm_model = os.getenv("OLLAMA_GRAPHITI_MODEL") or os.getenv(
        "OLLAMA_LLM_MODEL", DEFAULT_LLM_MODEL
    )
    structured_mode = os.getenv("GRAPHITI_STRUCTURED_OUTPUT_MODE", "json_schema")

    llm_config = LLMConfig(
        api_key="ollama",
        model=llm_model,
        small_model=llm_model,
        base_url=base,
    )
    llm_client = OllamaGraphitiClient(
        config=llm_config,
        structured_output_mode=structured_mode,
        max_tokens=int(os.getenv("OLLAMA_GRAPHITI_MAX_TOKENS", str(DEFAULT_MAX_TOKENS))),
    )
    embedder = OpenAIEmbedder(
        config=OpenAIEmbedderConfig(
            api_key="ollama",
            embedding_model=os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text"),
            embedding_dim=int(os.getenv("OLLAMA_EMBEDDING_DIM", "768")),
            base_url=base,
        )
    )
    return Graphiti(
        require_env("NEO4J_URI"),
        require_env("NEO4J_USER"),
        require_env("NEO4J_PASSWORD"),
        llm_client=llm_client,
        embedder=embedder,
        cross_encoder=OpenAIRerankerClient(client=llm_client, config=llm_config),
    )
