#!/usr/bin/env python3
"""Transient-only Local Facial Extractor token instrumentation v1.

This module has no top-level torch or model import. It captures `[1,32,2048]`
LFE outputs in process memory and intentionally provides no tensor serializer.
"""
from __future__ import annotations

from collections import defaultdict
from typing import Any

import token_resolved_lfe_direction_protocol_v1 as protocol


class TokenInstrumentationError(RuntimeError):
    """Raised for shape, determinism, equivalence, or panel violations."""


def _torch():
    try:
        import torch
    except ImportError as error:
        raise TokenInstrumentationError("torch is required only during transient capture") from error
    return torch


def _cpu_token_tensor(value: Any, expected_dim: int) -> Any:
    torch = _torch()
    tensor = value.detach().float().cpu()
    if tuple(tensor.shape) != (1, protocol.LFE_TOKENS, expected_dim):
        raise TokenInstrumentationError(f"unexpected LFE tensor shape: {tuple(tensor.shape)}")
    if not bool(torch.isfinite(tensor).all()):
        raise TokenInstrumentationError("nonfinite LFE tensor")
    return tensor[0].clone()


def within_frozen_tolerance(left: Any, right: Any) -> bool:
    torch = _torch()
    if tuple(left.shape) != tuple(right.shape):
        return False
    difference = torch.abs(left - right)
    tolerance = 1e-6 + 1e-5 * torch.maximum(torch.abs(left), torch.abs(right))
    return bool(torch.all(difference <= tolerance))


def direct_lfe_tokens(transformer: Any, id_cond: Any, id_vit_hidden: list[Any]) -> Any:
    """Call the frozen LFE module directly; caller owns model/runtime gates."""
    return transformer.local_facial_extractor(id_cond, id_vit_hidden)


class OneShotLfeHook:
    """Capture exactly one hooked LFE output for an engineering comparison."""

    def __init__(self, expected_dim: int = protocol.LFE_DIM):
        self.expected_dim = expected_dim
        self.tokens = None

    def __call__(self, module: Any, inputs: tuple, output: Any) -> None:
        del module, inputs
        if self.tokens is not None:
            raise TokenInstrumentationError("one-step LFE hook fired more than once")
        self.tokens = _cpu_token_tensor(output, self.expected_dim)

    def require_tokens(self) -> Any:
        if self.tokens is None:
            raise TokenInstrumentationError("one-step LFE hook did not fire")
        return self.tokens


class TransientLfeTokenCollector:
    """Validate engineering controls and retain one transient tensor per unit."""

    def __init__(self, expected_dim: int = protocol.LFE_DIM):
        self.expected_dim = expected_dim
        self._engineering_direct: dict[str, dict[int, Any]] = defaultdict(dict)
        self._engineering_hook: dict[str, Any] = {}
        self._scientific_tokens: dict[str, Any] = {}
        self._scientific_seeds: dict[str, set[str]] = defaultdict(set)
        self._metadata: dict[str, dict[str, str]] = {}

    def add_engineering_direct(self, unit: str, repeat: int, output: Any) -> None:
        if repeat not in (1, 2) or repeat in self._engineering_direct[unit]:
            raise TokenInstrumentationError("engineering direct repeat drift or duplicate")
        self._engineering_direct[unit][repeat] = _cpu_token_tensor(output, self.expected_dim)

    def add_engineering_hook(self, unit: str, output: Any) -> None:
        if unit in self._engineering_hook:
            raise TokenInstrumentationError("duplicate engineering hook result")
        self._engineering_hook[unit] = _cpu_token_tensor(output, self.expected_dim)

    def validate_engineering(self) -> dict:
        units = set(self._engineering_direct)
        if len(units) != 8 or units != set(self._engineering_hook):
            raise TokenInstrumentationError("engineering unit universe is not eight complete units")
        for unit in sorted(units):
            direct = self._engineering_direct[unit]
            if set(direct) != {1, 2}:
                raise TokenInstrumentationError(f"engineering direct repeats incomplete: {unit}")
            if not within_frozen_tolerance(direct[1], direct[2]):
                raise TokenInstrumentationError(f"engineering direct determinism failed: {unit}")
            if not within_frozen_tolerance(direct[1], self._engineering_hook[unit]):
                raise TokenInstrumentationError(f"direct/hook equivalence failed: {unit}")
        return {
            "status": "PASS_LFE_DIRECT_REPEAT_AND_HOOK_EQUIVALENCE",
            "engineering_units": 8,
            "direct_passes": 16,
            "hook_controls": 8,
            "raw_tokens_persisted": False,
        }

    def add_scientific(self, task: dict[str, str], output: Any) -> None:
        required = {
            "formal_unit_id", "formal_pair_id", "attribute", "role", "seed_index", "seed"
        }
        if not required.issubset(task):
            raise TokenInstrumentationError("scientific task metadata incomplete")
        unit = task["formal_unit_id"]
        seed = task["seed"]
        if seed not in protocol.FORMAL_SEEDS:
            raise TokenInstrumentationError("scientific seed drift")
        if seed in self._scientific_seeds[unit]:
            raise TokenInstrumentationError("duplicate scientific seed-labelled record")
        meta = {key: task[key] for key in ("formal_pair_id", "attribute", "role")}
        if unit in self._metadata and self._metadata[unit] != meta:
            raise TokenInstrumentationError("scientific metadata changed within unit")
        if meta["attribute"] not in protocol.ATTRIBUTES or meta["role"] not in protocol.ROLES:
            raise TokenInstrumentationError("scientific attribute or role drift")
        tokens = _cpu_token_tensor(output, self.expected_dim)
        if unit in self._scientific_tokens:
            if not within_frozen_tolerance(tokens, self._scientific_tokens[unit]):
                raise TokenInstrumentationError(f"LFE token changed across seed labels: {unit}")
        else:
            self._scientific_tokens[unit] = tokens
            self._metadata[unit] = meta
        self._scientific_seeds[unit].add(seed)

    def finalize_scientific(self) -> tuple[dict[str, Any], dict[str, dict[str, str]]]:
        if len(self._scientific_tokens) != 40 or set(self._scientific_tokens) != set(self._metadata):
            raise TokenInstrumentationError("scientific unit universe is not 40")
        expected = set(protocol.FORMAL_SEEDS)
        for unit, seeds in self._scientific_seeds.items():
            if seeds != expected:
                raise TokenInstrumentationError(f"four seed-labelled records incomplete: {unit}")
        pair_roles: dict[tuple[str, str], set[str]] = defaultdict(set)
        for meta in self._metadata.values():
            pair_roles[(meta["attribute"], meta["formal_pair_id"])].add(meta["role"])
        if len(pair_roles) != 20 or any(roles != set(protocol.ROLES) for roles in pair_roles.values()):
            raise TokenInstrumentationError("scientific matched-pair universe drift")
        return dict(self._scientific_tokens), dict(self._metadata)

    @property
    def raw_tensor_serialization_supported(self) -> bool:
        return False
