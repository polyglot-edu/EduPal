from pydantic import RootModel
from anthropic import Anthropic
from typing import Optional, List, Dict, Type, get_origin, get_args
from pydantic import BaseModel
from PIL import Image
import os
from .llm_interface import LLMInterface
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")


class ClaudeLLM(LLMInterface):
    def __init__(self, api_key: Optional[str] = None):
        api_key = api_key or ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("Anthropic API key is required to initialize ClaudeLLM")

        self.client = Anthropic(api_key=api_key)
        self.model = ANTHROPIC_MODEL

    def generate_text(
        self,
        prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
        context: Optional[str] = "",
        history: Optional[str] = "",
        options: Optional[Dict] = {"temperature": 0.0, "max_tokens": 1000},
        user_info: Optional[str] = "",
        instructions: Optional[str] = "",
        tools: Optional[List[str]] = None,
        image: Optional[Image.Image] = None,  # Not supported
    ) -> BaseModel | List[BaseModel] | str:

        # Handle list[BaseModel] response
        wrapper_model = None
        is_list_response = False
        if response_model and get_origin(response_model) is list:
            is_list_response = True
            item_model = get_args(response_model)[0]

            class WrapperModel(RootModel[List[item_model]]):
                @classmethod
                def model_validate(cls, obj):
                    if isinstance(obj, dict) and "root" in obj:
                        obj = obj["root"]
                    if isinstance(obj, list):
                        new_list = []
                        for item in obj:
                            if isinstance(item, dict) and "root" in item:
                                new_list.append(item["root"])
                            else:
                                new_list.append(item)
                        obj = new_list
                    return super().model_validate(obj)

            wrapper_model = WrapperModel
        else:
            wrapper_model = response_model

        # Build system prompt
        system_parts = []
        if instructions: system_parts.append(instructions)
        if context: system_parts.append(f"Context: {context}")
        if user_info: system_parts.append(f"User Info: {user_info}")
        if tools: system_parts.append(f"Tools: {', '.join(tools)}")
        system_prompt = "\n".join(system_parts) or "You are a helpful assistant."

        # Format messages (Claude keeps the system prompt separate from the messages array)
        messages = []
        if history:
            for turn in history.split("\n"):
                if turn.startswith("User:"):
                    messages.append({"role": "user", "content": turn[5:].strip()})
                elif turn.startswith("Assistant:"):
                    messages.append({"role": "assistant", "content": turn[10:].strip()})
        messages.append({"role": "user", "content": prompt})

        create_kwargs = dict(
            model=self.model,
            system=system_prompt,
            messages=messages,
            max_tokens=options.get("max_tokens", 1000),
            temperature=options.get("temperature", 0.0),
        )

        # For structured output, force a tool call instead of asking the model to
        # free-form emit JSON matching a schema dumped into the prompt: Claude tends
        # to echo the schema's own shape (title/type/properties) rather than an
        # instance of it. Forced tool_choice returns already-parsed, conformant JSON.
        unwrap_items = False
        tool_name = "generate_structured_response"
        if wrapper_model:
            schema = wrapper_model.model_json_schema()
            if schema.get("type") == "object":
                input_schema = schema
            else:
                # e.g. a bare array schema from RootModel[List[...]]: tool inputs must be objects
                unwrap_items = True
                # $defs must live at the schema root: nesting the whole array schema (defs
                # included) under properties.items would leave any "$ref": "#/$defs/..."
                # inside it unresolvable, since $ref is always resolved against the
                # document root, not the local nesting level.
                defs = schema.pop("$defs", None)
                input_schema = {"type": "object", "properties": {"items": schema}, "required": ["items"]}
                if defs:
                    input_schema["$defs"] = defs
            create_kwargs["tools"] = [{
                "name": tool_name,
                "description": "Return the structured response for the request above.",
                "input_schema": input_schema,
            }]
            create_kwargs["tool_choice"] = {"type": "tool", "name": tool_name}

        try:
            try:
                resp = self.client.messages.create(**create_kwargs)
            except Exception as e:
                # Some models (e.g. ones with extended thinking on by default,
                # like the one that surfaced this) reject an explicit
                # temperature outright with a 400 "`temperature` is deprecated
                # for this model" error instead of just ignoring it. Retry
                # once without it rather than failing the whole request.
                if "temperature" in create_kwargs and "temperature" in str(e).lower() and "deprecated" in str(e).lower():
                    create_kwargs.pop("temperature")
                    resp = self.client.messages.create(**create_kwargs)
                else:
                    raise

            if resp.stop_reason == "max_tokens":
                raise RuntimeError(
                    "Claude response was truncated because max_tokens was too low "
                    f"(max_tokens={create_kwargs['max_tokens']}). Increase 'max_tokens' in "
                    "the options passed to generate_text for this request."
                )

            if wrapper_model:
                tool_use_block = next((b for b in resp.content if b.type == "tool_use"), None)
                if tool_use_block is None:
                    raise RuntimeError(f"Claude did not return a tool_use block. Response: {resp.content}")
                tool_input = tool_use_block.input
                if unwrap_items:
                    tool_input = tool_input["items"]

                parsed = wrapper_model.model_validate(tool_input)

                if is_list_response:
                    if hasattr(parsed, 'root'):
                        return parsed.root
                    elif hasattr(parsed, '__root__'):
                        return parsed.__root__
                    else:
                        return parsed if isinstance(parsed, list) else [parsed]
                else:
                    return parsed

            return resp.content[0].text.strip()

        except Exception as e:
            raise RuntimeError(f"Claude generation failed: {e}") from e

    def generate_image(self, prompt: str) -> Image.Image:
        raise NotImplementedError("Claude does not support image generation.")
