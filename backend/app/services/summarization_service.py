import json
import logging
from groq import Groq
from app.core.config import settings
from app.core.errors import LLMFailedException, InvalidLLMOutputException
from app.schemas.meeting import MeetingExtraction
from app.prompts.meeting_extraction import SYSTEM_PROMPT

logger = logging.getLogger("meeting_summarizer")

# JSON schema derived from MeetingExtraction for the Groq JSON mode prompt hint
_SCHEMA_HINT = """
Return ONLY a valid JSON object with this exact structure (no markdown, no prose, no code fences, just raw JSON):
{
  "meeting_title": "<concise title derived from the transcript content>",
  "summary": "<paragraph summarizing the key topics discussed>",
  "key_decisions": ["<decision 1>", ...],
  "action_items": [
    {
      "task": "<task description>",
      "owner": "<person name or null if not stated>",
      "deadline": "<deadline string or null if not stated>",
      "priority": "<high|medium|low or null if not stated>"
    }
  ],
  "open_questions": ["<question 1>", ...],
  "next_steps": ["<next step 1>", ...]
}

IMPORTANT: You MUST populate meeting_title and summary with non-empty strings derived from the transcript.
Do NOT return empty strings for meeting_title or summary.
"""

_EXTRA_USER_INSTRUCTION = (
    "\n\nAnalyze the transcript above carefully and produce the JSON extraction. "
    "The meeting_title and summary fields are mandatory — derive them from the transcript content."
)


def _strip_code_fences(text: str) -> str:
    """Remove markdown code fences that some models wrap around JSON output."""
    text = text.strip()
    if text.startswith("```"):
        # Remove opening fence (e.g. ```json or ```)
        first_newline = text.find("\n")
        if first_newline != -1:
            text = text[first_newline + 1:]
        # Remove closing fence
        if text.endswith("```"):
            text = text[: text.rfind("```")]
    return text.strip()


def _validate_non_empty_fields(extraction: MeetingExtraction) -> None:
    """
    Raise InvalidLLMOutputException if required string fields are empty.
    Pydantic allows empty strings for str fields; we enforce non-empty here.
    """
    if not extraction.meeting_title.strip():
        raise InvalidLLMOutputException(
            "Model returned an empty 'meeting_title'. The LLM did not generate content from the transcript."
        )
    if not extraction.summary.strip():
        raise InvalidLLMOutputException(
            "Model returned an empty 'summary'. The LLM did not generate content from the transcript."
        )


def summarize_transcript(transcript: str) -> MeetingExtraction:
    """Send transcript to Groq ChatCompletion API with JSON mode to generate structured summary."""
    if not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "mock-key-for-local-testing":
        logger.warning("No valid Groq API key configured. Returning mock structured extraction.")
        return MeetingExtraction(
            meeting_title="Product sync — March 18",
            summary="The team aligned on the Q2 launch sequence, with engineering prioritizing onboarding improvements before the reporting dashboard. Marketing will prepare the announcement brief once the release candidate is stable.",
            key_decisions=[
                "Ship onboarding improvements in the first Q2 release.",
                "Move reporting dashboard work to the following sprint.",
                "Use the existing customer cohort for beta feedback."
            ],
            action_items=[
                {"task": "Share the revised launch checklist with the team", "owner": "Maya Chen", "deadline": "Mar 21", "priority": "High"},
                {"task": "Create beta feedback survey", "owner": "Jordan Lee", "deadline": None, "priority": "Medium"},
                {"task": "Add analytics events to the onboarding flow", "owner": None, "deadline": "Mar 28", "priority": "Medium"}
            ],
            open_questions=[
                "Which customer segment should receive the first beta invite?",
                "Do existing customers need a migration guide?"
            ],
            next_steps=[
                "Finalize the release checklist.",
                "Confirm beta cohort and send invitations.",
                "Review onboarding analytics in the next sync."
            ]
        )

    try:
        client = Groq(api_key=settings.GROQ_API_KEY)

        system_content = (
            "Summarize the provided meeting transcript. "
            "Extract only information explicitly supported by the transcript. "
            "If a category has no information, return an empty value/list.\n\n"
            + SYSTEM_PROMPT
            + _SCHEMA_HINT
        )
        user_content = f"Transcript:\n\n{transcript}{_EXTRA_USER_INSTRUCTION}"

        logger.info(
            "Sending transcript to LLM (model=%s, transcript_length=%d chars)",
            settings.GROQ_LLM_MODEL,
            len(transcript),
        )

        completion = client.chat.completions.create(
            model=settings.GROQ_LLM_MODEL,
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
        )

        raw_content = completion.choices[0].message.content
        logger.info("Raw LLM response (first 500 chars): %s", (raw_content or "")[:500])

        if not raw_content or not raw_content.strip():
            logger.error("Groq returned an empty response.")
            raise InvalidLLMOutputException("Model returned an empty response.")

        # Strip markdown code fences in case the model wraps its output
        cleaned_content = _strip_code_fences(raw_content)

        # Validate it is parseable JSON before Pydantic validation
        try:
            raw_dict = json.loads(cleaned_content)
        except json.JSONDecodeError as json_err:
            logger.error(
                "LLM response is not valid JSON: %s\nRaw content: %s",
                json_err,
                raw_content,
            )
            raise InvalidLLMOutputException(
                f"Model response is not valid JSON: {json_err}"
            )

        logger.debug("Parsed JSON keys from LLM: %s", list(raw_dict.keys()))

        try:
            parsed_response = MeetingExtraction.model_validate(raw_dict)
        except Exception as parse_err:
            logger.error(
                "Groq response failed Pydantic validation: %s\nRaw dict: %s",
                parse_err,
                raw_dict,
                exc_info=True,
            )
            raise InvalidLLMOutputException(
                f"Failed to parse structured output from model response: {parse_err}"
            )

        # Guard against silently empty required fields
        _validate_non_empty_fields(parsed_response)

        logger.info(
            "LLM extraction succeeded: title=%r, decisions=%d, actions=%d",
            parsed_response.meeting_title,
            len(parsed_response.key_decisions),
            len(parsed_response.action_items),
        )
        return parsed_response

    except Exception as e:
        logger.error("Groq LLM structured completion failed: %s", e, exc_info=True)
        if isinstance(e, (InvalidLLMOutputException, LLMFailedException)):
            raise e
        raise LLMFailedException(f"LLM summarization failed: {str(e)}")
