from fastapi import HTTPException, status


def is_default_tier(llm_token: str | None) -> bool:
    """
    A request is on the default (shared, free) tier whenever the caller did not
    supply their own LLM API key, so the app's own shared key is used instead.

    This is the only gate the free tier's restrictions key off of: as soon as a
    caller sends their own llm_token (with any model, e.g. "Claude"), every
    enforce_* check below is skipped - including any usage limit configured on
    that key elsewhere (e.g. spend/rate caps set on the provider's own
    dashboard for that key). This app applies no additional token/usage cap of
    its own on top of that.
    """
    return not llm_token


def enforce_language_restriction(llm_token: str | None, language: str | None):
    """
    The shared default key has a limited quota, so non-English output is only
    allowed for users bringing their own LLM API key.
    """
    if is_default_tier(llm_token) and language and language.strip().lower() != "english":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The default shared model only supports English. Provide your own LLM API key (llm_token header) to use other languages."
        )


def enforce_multiple_choice_only(llm_token: str | None, activity_types: list[str]):
    """
    On the default tier, activity/test generation is limited to multiple-choice
    questions - the free-tier whitelist's third allowed action.
    """
    if is_default_tier(llm_token) and any(t != "multiple choice" for t in activity_types):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The default shared model only supports generating multiple-choice questions. Provide your own LLM API key to generate other activity types."
        )


def enforce_own_key_required(llm_token: str | None, action: str = "This action"):
    """
    Anything outside the free-tier whitelist (material analysis, reading-material
    generation, multiple-choice generation) requires the caller's own LLM API key.
    """
    if is_default_tier(llm_token):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{action} requires your own LLM API key. Provide one (llm_token header) to use it."
        )
