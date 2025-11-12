# Codex v2.2

Codex is a risk and news intelligence module that validates trading features, aggregates sentiment, and requests
LLM verdicts with a strict JSON contract. This repository contains the reference implementation for version 2.2 of the
service, including configuration, prompts, and automated tests that cover the major acceptance criteria.

The service is model-agnostic and ships with Claude Sonnet as the primary provider. Alternative providers can be
configured without code changes.
