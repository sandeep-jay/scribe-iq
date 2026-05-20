"""Shared boto3 session and Bedrock Runtime client factory.

Encapsulates Bedrock client construction so both LLM and embedding providers go through
the same auth path (named profile, default chain, optional STS AssumeRole, region).
"""

from __future__ import annotations

from typing import Any

from app.config import Settings


def _import_boto3() -> Any:
    try:
        import boto3

        return boto3
    except ImportError as exc:
        raise RuntimeError(
            "boto3 is required for AWS Bedrock; install scribe-iq-backend with boto3."
        ) from exc


def _base_session(settings: Settings, boto3_module: Any) -> Any:
    region = (settings.aws_region or "").strip()
    if not region:
        raise RuntimeError("AWS_REGION is required for AWS Bedrock providers.")
    session_kwargs: dict[str, str] = {"region_name": region}
    profile = (settings.bedrock_profile_name or "").strip()
    if profile:
        session_kwargs["profile_name"] = profile
    return boto3_module.Session(**session_kwargs)


def _assume_role_session(
    settings: Settings,
    boto3_module: Any,
    role_arn: str,
    region: str,
    base_session: Any,
) -> Any:
    sts_client = base_session.client("sts")
    response = sts_client.assume_role(
        RoleArn=role_arn,
        RoleSessionName="scribe-iq-bedrock",
    )
    creds = response["Credentials"]
    return boto3_module.Session(
        aws_access_key_id=creds["AccessKeyId"],
        aws_secret_access_key=creds["SecretAccessKey"],
        aws_session_token=creds["SessionToken"],
        region_name=region,
    )


def bedrock_runtime_client(settings: Settings) -> Any:
    """Return a `bedrock-runtime` client.

    Auth precedence:
    1. `AWS_BEDROCK_ROLE_ARN` is assumed from the base session (named profile or default).
    2. Otherwise the base session is used directly.
    """

    boto3_module = _import_boto3()
    base_session = _base_session(settings, boto3_module)
    region = (settings.aws_region or "").strip()
    role_arn = (settings.aws_bedrock_role_arn or "").strip()
    session = (
        _assume_role_session(settings, boto3_module, role_arn, region, base_session)
        if role_arn
        else base_session
    )
    return session.client("bedrock-runtime")
