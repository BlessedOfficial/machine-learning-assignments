"""Reuse isolated safety reviewer client (no tools)."""

from llms.safety_reviewer.client import call_safety_reviewer

__all__ = ["call_safety_reviewer"]
