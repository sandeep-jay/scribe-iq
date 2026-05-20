"""Unit tests for the shared Bedrock session helper."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock, patch

import pytest

from app.config import Settings


def _settings(**kwargs):
    return Settings(
        _env_file=None,
        embedding_provider="bedrock",
        aws_region="us-west-2",
        aws_bedrock_chat_model_id="anthropic.claude-3-5-haiku-20241022-v1:0",
        aws_bedrock_role_arn=kwargs.pop("aws_bedrock_role_arn", ""),
        **kwargs,
    )


@pytest.fixture(autouse=True)
def _reload_module():
    sys.modules.pop("app.aws.bedrock_session", None)
    yield
    sys.modules.pop("app.aws.bedrock_session", None)


def test_session_uses_named_profile_when_set():
    mock_boto3 = MagicMock()
    mock_session = MagicMock()
    mock_session.client.return_value = "runtime-client"
    mock_boto3.Session.return_value = mock_session

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from app.aws.bedrock_session import bedrock_runtime_client

        client = bedrock_runtime_client(_settings(bedrock_profile_name="dev"))

    assert client == "runtime-client"
    mock_boto3.Session.assert_called_once_with(region_name="us-west-2", profile_name="dev")
    mock_session.client.assert_called_once_with("bedrock-runtime")


def test_session_assumes_role_when_arn_set():
    mock_boto3 = MagicMock()
    base_session = MagicMock(name="base")
    assumed_session = MagicMock(name="assumed")
    assumed_session.client.return_value = "assumed-runtime"
    base_sts = MagicMock()
    base_sts.assume_role.return_value = {
        "Credentials": {
            "AccessKeyId": "AKIA",
            "SecretAccessKey": "secret",
            "SessionToken": "token",
        }
    }
    base_session.client.return_value = base_sts
    mock_boto3.Session.side_effect = [base_session, assumed_session]

    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from app.aws.bedrock_session import bedrock_runtime_client

        client = bedrock_runtime_client(
            _settings(aws_bedrock_role_arn="arn:aws:iam::123456789012:role/scribe")
        )

    assert client == "assumed-runtime"
    base_session.client.assert_called_once_with("sts")
    base_sts.assume_role.assert_called_once()
    assumed_session.client.assert_called_once_with("bedrock-runtime")
    second_kwargs = mock_boto3.Session.call_args_list[1].kwargs
    assert second_kwargs["aws_access_key_id"] == "AKIA"
    assert second_kwargs["region_name"] == "us-west-2"


def test_session_requires_region():
    mock_boto3 = MagicMock()
    with patch.dict(sys.modules, {"boto3": mock_boto3}):
        from app.aws.bedrock_session import bedrock_runtime_client

        with pytest.raises(RuntimeError, match="AWS_REGION"):
            bedrock_runtime_client(Settings(_env_file=None, embedding_provider="bedrock", aws_region=""))
