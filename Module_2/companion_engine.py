"""
companion_engine.py
Module 2, Engine 5: Companion AI Engine

Generates emotionally supportive, personalized responses using
Memory Engine context.

HONEST SCOPE NOTE: true conversational AI needs a real language model
(like Gemini/GPT via API, or a local LLM). This is a lightweight,
rule-based MVP -- pattern-matches a small set of known emotional/
informational cues and responds using stored memory. It's designed to
be swapped out for a real LLM call later without changing how the
rest of the system uses it (same input/output shape).
"""

import random


class CompanionEngine:
    def __init__(self, memory_engine):
        self.memory = memory_engine

    def generate_response(self, user_text):
        """
        user_text: what the person said (from speech-to-text, or typed
        in for testing).
        Returns: a response string, personalized using memory when possible.
        """
        text = user_text.lower()

        # Log this exchange in short-term memory regardless of pattern match
        self.memory.add_conversation_turn("user", user_text)

        # Check if this statement teaches us something new to remember
        remembered = self.memory.extract_and_remember(user_text)

        response = None

        # Emotional support pattern: missing a family member
        if "miss" in text and self.memory.get_family_members():
            family = self.memory.get_family_members()
            person = family[0]  # simplistic: refers to the first known family member
            response = (
                f"I know you miss {person['name']}. Would you like me to play "
                f"their latest voice message, or should I remind them to call?"
            )

        # Medication reminder pattern
        elif "medicine" in text or "medication" in text:
            meds = self.memory.get_medications()
            if meds:
                med_list = ", ".join(f"{m['name']} at {m['times']}" for m in meds)
                response = f"Your medications are: {med_list}. Would you like a reminder?"
            else:
                response = "I don't have any medications noted yet. Would you like to tell me one?"

        # Greeting
        elif any(word in text for word in ["hello", "hi ", "good morning", "good evening"]):
            greetings = [
                "Hello! It's good to hear from you.",
                "Hi there! How are you feeling today?",
                "Good to see you! What's on your mind?",
            ]
            response = random.choice(greetings)

        # If we just learned something new, acknowledge it warmly
        elif remembered:
            response = f"Got it, I'll remember that. {remembered}."

        # Fallback: general supportive acknowledgment
        else:
            response = "I'm here with you. Tell me more, or let me know if you need anything."

        self.memory.add_conversation_turn("robot", response)
        return response
