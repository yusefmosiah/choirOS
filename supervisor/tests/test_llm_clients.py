import json
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from supervisor.llm import (
    AnthropicClient,
    BedrockConverseClient,
    GoogleClient,
    LLMResponse,
    Message,
    OpenAIClient,
)
from supervisor.llm import anthropic_client as anthropic_module
from supervisor.llm import bedrock_client as bedrock_module
from supervisor.llm import google_client as google_module
from supervisor.llm import openai_client as openai_module


class FakeAnthropicBlock:
    def __init__(self, block_type: str, text: str | None = None, name: str | None = None, input=None, id=None):
        self.type = block_type
        self.text = text
        self.name = name
        self.input = input or {}
        self.id = id


class FakeAnthropicMessages:
    def __init__(self, content):
        self.content = content
        self.stop_reason = "end_turn"


def test_anthropic_client_converts_messages(monkeypatch):
    created_kwargs = {}

    class FakeMessagesAPI:
        def create(self, **kwargs):
            nonlocal created_kwargs
            created_kwargs = kwargs
            return FakeAnthropicMessages([
                FakeAnthropicBlock("text", text="hello"),
                FakeAnthropicBlock("tool_use", name="read_file", input={"path": "README.md"}, id="tool-1"),
            ])

    class FakeAnthropicSDK:
        def __init__(self, api_key=None):
            self.messages = FakeMessagesAPI()

    monkeypatch.setattr(anthropic_module.anthropic, "Anthropic", lambda api_key=None: FakeAnthropicSDK(api_key))

    client = AnthropicClient(api_key="test")
    messages: list[Message] = [
        {"role": "system", "content": "sys"},
        {"role": "user", "content": "hi"},
    ]
    response: LLMResponse = client.chat(messages=messages, model="claude-test", tools=[{"name": "read_file", "input_schema": {}}])

    assert created_kwargs["system"] == "sys"
    assert created_kwargs["messages"][0]["role"] == "user"
    assert response["content"] == "hello"
    assert response["tool_calls"][0]["name"] == "read_file"
    assert response["tool_calls"][0]["arguments"] == {"path": "README.md"}


def test_bedrock_client_maps_content(monkeypatch):
    captured_kwargs = {}

    class FakeBedrockClient:
        def converse(self, **kwargs):
            nonlocal captured_kwargs
            captured_kwargs = kwargs
            return {
                "output": {
                    "message": {
                        "content": [
                            {"text": "hello"},
                            {"toolUse": {"toolUseId": "t1", "name": "bash", "input": {"command": "ls"}}},
                        ]
                    }
                },
                "stopReason": "tool_use",
            }

    monkeypatch.setattr(bedrock_module.boto3, "client", lambda service_name, region_name=None: FakeBedrockClient())

    client = BedrockConverseClient(region="us-west-2")
    messages: list[Message] = [{"role": "user", "content": "say hi"}]
    response = client.chat(messages=messages, model="bedrock-model", tools=[{"name": "bash", "description": "run", "input_schema": {}}])

    assert captured_kwargs["modelId"] == "bedrock-model"
    assert captured_kwargs["toolConfig"]["tools"][0]["toolSpec"]["inputSchema"]["json"] == {}
    assert response["content"] == "hello"
    assert response["tool_calls"][0]["name"] == "bash"
    assert response["tool_calls"][0]["arguments"] == {"command": "ls"}


def test_openai_client_parses_tool_calls(monkeypatch):
    captured_kwargs = {}

    class FakeFunction:
        def __init__(self, name, arguments):
            self.name = name
            self.arguments = arguments

    class FakeToolCall:
        def __init__(self):
            self.id = "call-1"
            self.type = "function"
            self.function = FakeFunction("read_file", json.dumps({"path": "file.txt"}))

    class FakeMessage:
        def __init__(self):
            self.content = ""
            self.tool_calls = [FakeToolCall()]

    class FakeChoice:
        def __init__(self):
            self.message = FakeMessage()
            self.finish_reason = "tool_calls"

    class FakeCompletionsAPI:
        def create(self, **kwargs):
            nonlocal captured_kwargs
            captured_kwargs = kwargs
            return type("Resp", (), {"choices": [FakeChoice()]})

    class FakeChatAPI:
        def __init__(self):
            self.completions = FakeCompletionsAPI()

    class FakeOpenAIClient:
        def __init__(self, api_key=None):
            self.chat = FakeChatAPI()

    monkeypatch.setattr(openai_module, "OpenAI", lambda api_key=None: FakeOpenAIClient(api_key))

    client = OpenAIClient(api_key="key")
    messages: list[Message] = [{"role": "user", "content": [{"type": "text", "text": "hi"}, {"type": "tool_result", "tool_use_id": "t1", "content": "done", "status": "success"}]}]

    response = client.chat(messages=messages, model="gpt-test", tools=[{"name": "read_file", "input_schema": {}}])

    assert captured_kwargs["model"] == "gpt-test"
    assert captured_kwargs["tools"][0]["function"]["name"] == "read_file"
    assert response["tool_calls"][0]["name"] == "read_file"
    assert response["tool_calls"][0]["arguments"] == {"path": "file.txt"}


def test_google_client_uses_system_instruction(monkeypatch):
    configured_keys = {}

    def fake_configure(api_key=None):
        configured_keys["api_key"] = api_key

    class FakeModel:
        def __init__(self, *args, **kwargs):
            self.kwargs = kwargs

        def generate_content(self, gen_messages, generation_config=None):
            self.gen_messages = gen_messages
            self.generation_config = generation_config
            return type("Resp", (), {"text": "hi", "finish_reason": "stop"})

    monkeypatch.setattr(google_module.genai, "configure", fake_configure)
    monkeypatch.setattr(google_module.genai, "GenerativeModel", lambda *args, **kwargs: FakeModel(*args, **kwargs))

    client = GoogleClient(api_key="google-key", default_model="gemini-pro")
    messages: list[Message] = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "hello"},
    ]
    response = client.chat(messages=messages, model="gemini-pro")

    assert configured_keys["api_key"] == "google-key"
    assert response["content"] == "hi"
