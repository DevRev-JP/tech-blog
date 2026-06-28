"""共通: Neo4j / Ollama / Graphiti 接続と CLI 出力ヘルパー."""

from __future__ import annotations

import contextlib
import io
import logging
import os
import sys
import warnings
from pathlib import Path

from dotenv import load_dotenv
from langchain_ollama import ChatOllama
from neo4j import GraphDatabase

try:
    from neo4j.api import NotificationMinimumSeverity
except ImportError:  # pragma: no cover — 古い neo4j ドライバ
    NotificationMinimumSeverity = None  # type: ignore[misc, assignment]

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
DEFAULT_LLM_MODEL = "gemma2:2b"

for env_name in (".env", "env.sample"):
    env_path = ROOT / env_name
    if env_path.exists():
        load_dotenv(env_path)
        break


_BENIGN_STDERR_FRAGMENTS = (
    "EquivalentSchemaRuleAlreadyExists",
    "property key does not exist",
    "entity_edges",
    "name_embedding",
    "fact_embedding",
    "episodes",
    "Received notification from DBMS server",
    "Target entity not found in nodes",
    "Invalid duplicate_candidate_id",
    "LLM did not return resolutions",
    "Skipping invalid LLM dedupe",
    "Error executing Neo4j query",
)


def is_demo_verbose() -> bool:
    """DEMO_VERBOSE=1 のときのみ Graphiti/Neo4j の詳細ログを出す（デフォルトは抑制）."""
    if os.getenv("DEMO_VERBOSE", "").lower() in ("1", "true", "yes"):
        return True
    # 旧 .env 互換: DEMO_QUIET=0 は verbose 扱い
    return os.getenv("DEMO_QUIET", "").lower() in ("0", "false", "no")


def is_demo_quiet() -> bool:
    return not is_demo_verbose()


def is_demo_batch() -> bool:
    """run_demo.sh の part1/part2/all からの連続実行（冗長ログを抑える）."""
    return os.getenv("DEMO_BATCH", "").lower() in ("1", "true", "yes")


def configure_demo_logging() -> None:
    """デフォルトでデモ結果以外のログを抑える。DEMO_VERBOSE=1 で解除."""
    if not is_demo_quiet():
        return
    warnings.filterwarnings("ignore")
    for name in (
        "neo4j",
        "neo4j.notifications",
        "graphiti_core",
        "httpx",
        "httpcore",
        "openai",
        "urllib3",
    ):
        logging.getLogger(name).setLevel(logging.CRITICAL)


class _FilteredStderr(io.TextIOBase):
    """Graphiti / Neo4j の既知の無害メッセージだけ stderr から除外."""

    def __init__(self, underlying: io.TextIOBase, patterns: tuple[str, ...]) -> None:
        self._underlying = underlying
        self._patterns = patterns
        self._buffer = ""

    def write(self, s: str) -> int:  # type: ignore[override]
        self._buffer += s
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line and not any(p in line for p in self._patterns):
                self._underlying.write(line + "\n")
        return len(s)

    def flush(self) -> None:  # type: ignore[override]
        if self._buffer and not any(p in self._buffer for p in self._patterns):
            self._underlying.write(self._buffer)
        self._buffer = ""
        self._underlying.flush()


@contextlib.contextmanager
def demo_run_context():
    """各デモ script の main 先頭で使う（quiet 時はノイズ抑制）."""
    configure_demo_logging()
    if not is_demo_quiet():
        yield
        return
    old_stderr = sys.stderr
    sys.stderr = _FilteredStderr(old_stderr, _BENIGN_STDERR_FRAGMENTS)
    try:
        yield
    finally:
        sys.stderr.flush()
        sys.stderr = old_stderr


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
    kwargs: dict = {}
    if is_demo_quiet() and NotificationMinimumSeverity is not None:
        kwargs["notifications_min_severity"] = NotificationMinimumSeverity.OFF
    return GraphDatabase.driver(uri, auth=(user, password), **kwargs)


def get_llm():
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("OLLAMA_LLM_MODEL", DEFAULT_LLM_MODEL)
    return ChatOllama(model=model, base_url=base_url, temperature=0)


def phase(title: str, subtitle: str = "") -> None:
    """Part0 / Part1 / Part2 など大きな区切り."""
    print()
    print("━" * 56)
    print(f"  {title}")
    if subtitle:
        print(f"  {subtitle}")
    print("━" * 56)


def step_print(step: int, total: int, message: str) -> None:
    if is_demo_verbose():
        print(f"\n[Step {step}/{total}] {message}")
    elif is_demo_batch():
        return
    else:
        print(f"\n→ {message}")


def section(title: str) -> None:
    print(f"\n── {title} ──")


def checkpoint(title: str, bullets: list[str]) -> None:
    """手作業確認用 — このステップで何を見ればよいか."""
    if is_demo_batch() and not is_demo_verbose():
        return
    section(f"確認 — {title}")
    for item in bullets:
        print(f"  • {item}")


def milestone(message: str) -> None:
    """バッチ実行時の1行サマリ."""
    print(f"  ✓ {message}")


def demo_summary(title: str, lines: list[str]) -> None:
    """all / full 終了時の総括."""
    print()
    print("━" * 56)
    print(f"  {title}")
    print("━" * 56)
    for line in lines:
        print(f"  {line}")
    print()


def result_line(label: str, value: str) -> None:
    """結果サマリを揃えて表示."""
    print(f"  {label}: {value}")


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
