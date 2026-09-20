"""
MARSHALL - AI Router Module
Routes requests to Groq (fast inference) for all intelligence tasks.
Models: groq/compound for chat, whisper-large-v3-turbo for voice.
"""
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

GROK_API_KEY = os.getenv("GROK_API_KEY")

client = OpenAI(
    api_key=GROK_API_KEY,
    base_url="https://api.groq.com/openai/v1",
)

MARSHALL_SYSTEM_PROMPT = """You are MARSHALL - an advanced personal AI assistant controlling a Windows PC system.
You are sharp, intelligent, and direct. You can:
- Control the PC (lock/unlock, launch apps, browse files)
- Carry out deep research and study requests  
- Answer questions across any domain: science, tech, history, coding, mathematics, etc.
- Analyze documents and images
- Help with creative writing, planning, and problem solving

You speak like JARVIS from Iron Man - calm, precise, confident, slightly witty.
Always address the user as "Sir" or by name if you learn it.
When executing system commands, confirm what you are doing briefly, then do it.
Keep responses concise unless the user asks for detail."""

conversation_history = []


def chat(user_message: str, reset: bool = False) -> str:
    """Send a message to Grok and get a response."""
    global conversation_history

    if reset:
        conversation_history = []

    conversation_history.append({"role": "user", "content": user_message})

    # Keep history to last 20 exchanges to avoid token limits
    if len(conversation_history) > 40:
        conversation_history = conversation_history[-40:]

    messages = [{"role": "system", "content": MARSHALL_SYSTEM_PROMPT}] + conversation_history

    try:
        response = client.chat.completions.create(
            model="groq/compound",
            messages=messages,
            max_tokens=2048,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        conversation_history.append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        # Fallback to qwen
        try:
            response = client.chat.completions.create(
                model="qwen/qwen3.8-27b",
                messages=messages,
                max_tokens=2048,
                temperature=0.7,
            )
            reply = response.choices[0].message.content
            conversation_history.append({"role": "assistant", "content": reply})
            return reply
        except Exception as e2:
            return f"MARSHALL AI error: {str(e2)}"


def research(topic: str) -> str:
    """Deep research request - uses Grok with extended context."""
    prompt = f"""Conduct thorough research on the following topic and provide a comprehensive, well-structured response:

TOPIC: {topic}

Structure your response with:
- Overview/Summary
- Key findings / facts
- Detailed explanation
- Practical applications or implications
- Sources / references (if known)"""

    try:
        response = client.chat.completions.create(
            model="grok-3",
            messages=[
                {"role": "system", "content": MARSHALL_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            max_tokens=4096,
            temperature=0.5,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Research error: {str(e)}"


def clear_history():
    global conversation_history
    conversation_history = []
    return {"status": "cleared"}
