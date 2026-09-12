"""AgriPilot AI — agricultural decision-support backend.

Layering rule: `agripilot.engine` is pure and deterministic. It must never
import streamlit, requests, or any LLM SDK. Everything with I/O lives in
`agripilot.services`.
"""

__version__ = "0.1.0"
