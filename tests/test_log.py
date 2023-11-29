import pytest
import time

import phospho
from openai.types.chat import ChatCompletion, ChatCompletionMessage, ChatCompletionChunk
from openai.types.completion_usage import CompletionUsage

from openai.types.chat.chat_completion import Choice

from openai.types.chat.chat_completion_chunk import ChoiceDelta
from openai.types.chat.chat_completion_chunk import Choice as chunk_Choice

MOCK_OPENAI_QUERY = {
    "messages": [{"role": "user", "content": "Say hi !"}],
    "model": "gpt-3.5-turbo",
}

MOCK_OPENAI_RESPONSE = ChatCompletion(
    id="chatcmpl-8ONC0iiWZXmkddojmWfR6w3aHdTsu",
    choices=[
        Choice(
            finish_reason="stop",
            index=0,
            message=ChatCompletionMessage(
                content="Hello! How can I assist you today?",
                role="assistant",
                function_call=None,
                tool_calls=None,
            ),
        )
    ],
    created=1700819716,
    model="gpt-3.5-turbo-0613",
    object="chat.completion",
    system_fingerprint=None,
    usage=CompletionUsage(completion_tokens=9, prompt_tokens=10, total_tokens=19),
)

MOCK_OPENAI_STREAM_RESPONSE = [
    ChatCompletionChunk(
        id="chatcmpl-8PWAOdCT73H5XUum52ny3NHnw2ZQx",
        choices=[
            chunk_Choice(
                delta=ChoiceDelta(
                    content="Hello", function_call=None, role=None, tool_calls=None
                ),
                finish_reason=None,
                index=0,
            )
        ],
        created=1701092540,
        model="gpt-3.5-turbo-0613",
        object="chat.completion.chunk",
        system_fingerprint=None,
    ),
    ChatCompletionChunk(
        id="chatcmpl-8PWAOdCT73H5XUum52ny3NHnw2ZQx",
        choices=[
            chunk_Choice(
                delta=ChoiceDelta(
                    content=" you",
                    function_call=None,
                    role=None,
                    tool_calls=None,
                ),
                finish_reason=None,
                index=0,
            )
        ],
        created=1701092540,
        model="gpt-3.5-turbo-0613",
        object="chat.completion.chunk",
        system_fingerprint=None,
    ),
    ChatCompletionChunk(
        id="chatcmpl-8PWAOdCT73H5XUum52ny3NHnw2ZQx",
        choices=[
            chunk_Choice(
                delta=ChoiceDelta(
                    content="!", function_call=None, role=None, tool_calls=None
                ),
                finish_reason=None,
                index=0,
            )
        ],
        created=1701092540,
        model="gpt-3.5-turbo-0613",
        object="chat.completion.chunk",
        system_fingerprint=None,
    ),
    ChatCompletionChunk(
        id="chatcmpl-8PWAOdCT73H5XUum52ny3NHnw2ZQx",
        choices=[
            chunk_Choice(
                delta=ChoiceDelta(
                    content=None, function_call=None, role=None, tool_calls=None
                ),
                finish_reason="stop",
                index=0,
            )
        ],
        created=1701092540,
        model="gpt-3.5-turbo-0613",
        object="chat.completion.chunk",
        system_fingerprint=None,
    ),
]


def test_openai_sync():
    phospho.init(api_key="test", project_id="test", tick=0.05)

    query = MOCK_OPENAI_QUERY
    response = MOCK_OPENAI_RESPONSE

    log_content = phospho.log(input=query, output=response)

    assert log_content["input"] == "Say hi !"
    assert log_content["output"] == "Hello! How can I assist you today?"
    assert log_content["session_id"] is not None, "default session_id should be created"
    old_session_id = log_content["session_id"]

    log_content = phospho.log(input=query, output=response)
    new_session_id = log_content["session_id"]
    assert (
        new_session_id == old_session_id
    ), "session_id should be preserved between 2 continuous calls"
    time.sleep(0.1)
    # TODO : Validate that the connection was successful


def test_openai_stream():
    phospho.init(api_key="test", project_id="test", tick=0.05)

    query = MOCK_OPENAI_QUERY
    stream_response = MOCK_OPENAI_STREAM_RESPONSE
    expected_outputs = ["Hello", "Hello you", "Hello you!", "Hello you!"]
    assert len(stream_response) == len(expected_outputs)
    # Verify that the extractor matches the output
    for i, response, expected_output in zip(
        range(len(expected_outputs)), stream_response, expected_outputs
    ):
        log_content = phospho.log(input=query, output=response)
        assert (
            log_content["output"] == expected_output
        ), f"Expected output from extractor '{expected_output}' but instead got: {log_content['output']}"
        if i + 1 < len(expected_outputs):
            assert (
                phospho.log_queue.events[
                    "chatcmpl-8PWAOdCT73H5XUum52ny3NHnw2ZQx"
                ].to_log
                == False
            ), f"First (i={i}) log events should be set as to_log=False"
        else:
            # Last call, we want the output to be marked as "to log"
            assert (
                phospho.log_queue.events[
                    "chatcmpl-8PWAOdCT73H5XUum52ny3NHnw2ZQx"
                ].to_log
                == True
            ), f"Last (i={i}) log event should be set as to_log=True"
    time.sleep(0.1)
    # TODO : Validate that the connection was successful


def test_wrap():
    phospho.init(api_key="test", project_id="test", verbose=True)

    # No streaming
    def fake_openai_call_no_stream(model, messages, stream: bool = False):
        return MOCK_OPENAI_RESPONSE

    response = phospho.wrap(fake_openai_call_no_stream)(
        model=MOCK_OPENAI_QUERY["model"],
        messages=MOCK_OPENAI_QUERY["messages"],
    )
    assert response == MOCK_OPENAI_RESPONSE
    response = phospho.wrap(fake_openai_call_no_stream)(
        model=MOCK_OPENAI_QUERY["model"],
        messages=MOCK_OPENAI_QUERY["messages"],
        stream=False,
    )
    assert response == MOCK_OPENAI_RESPONSE

    # Streaming

    def fake_openai_call_stream(model, messages, stream: bool = True):
        for stream_response in MOCK_OPENAI_STREAM_RESPONSE:
            yield stream_response

    response = phospho.wrap(fake_openai_call_stream)(
        model=MOCK_OPENAI_QUERY["model"],
        messages=MOCK_OPENAI_QUERY["messages"],
        stream=True,
    )
    # Streamed content should be the same
    for r, groundtruth_r in zip(response, MOCK_OPENAI_STREAM_RESPONSE):
        assert r == groundtruth_r
    # TODO : Validate that the connection was successful
