#!/usr/bin/env python3
"""Transient-only LFE projection-exchange math and output-hook instrumentation.

There are deliberately no top-level ML imports and no tensor serializers.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Self

import controlled_lfe_projection_exchange_protocol_v1 as protocol


class ControlledInterventionInstrumentationError(RuntimeError):
    """Raised on tensor, direction, sham, crossing, or hook failure."""


def _torch():
    try:
        import torch
    except ImportError as error:
        raise ControlledInterventionInstrumentationError("torch is required for transient tensor math") from error
    return torch


def _as_cpu_float(value: Any, expected_dim: int) -> Any:
    torch = _torch()
    tensor = value.detach().float().cpu().contiguous()
    if tuple(tensor.shape) != (1, protocol.LFE_TOKENS, expected_dim):
        raise ControlledInterventionInstrumentationError(f"unexpected LFE shape: {tuple(tensor.shape)}")
    if not bool(torch.isfinite(tensor).all()):
        raise ControlledInterventionInstrumentationError("non-finite LFE tensor")
    return tensor.clone()


def within_frozen_tolerance(left: Any, right: Any) -> bool:
    torch = _torch()
    a = left.detach().float().cpu()
    b = right.detach().float().cpu()
    if tuple(a.shape) != tuple(b.shape) or not bool(torch.isfinite(a).all() and torch.isfinite(b).all()):
        return False
    return bool((torch.abs(a - b) <= 1e-6 + 1e-5 * torch.maximum(torch.abs(a), torch.abs(b))).all())


def sham_displacement_direction_dot(sham: Any, base: Any, direction: Any) -> Any:
    """Evaluate the frozen dot(X_sham - X, u) invariant without projection cancellation."""
    torch = _torch()
    if tuple(sham.shape) != tuple(base.shape) or tuple(direction.shape) != tuple(base.shape):
        raise ControlledInterventionInstrumentationError("sham displacement invariant shape drift")
    displacement = sham - base
    if not bool(torch.isfinite(displacement).all() and torch.isfinite(direction).all()):
        raise ControlledInterventionInstrumentationError("non-finite sham displacement invariant")
    return torch.dot(displacement, direction)


def constructed_displacement_direction_dot(displacement: Any, direction: Any) -> Any:
    """Evaluate the explicitly constructed delta*q displacement without add/subtract loss."""
    torch = _torch()
    if tuple(displacement.shape) != tuple(direction.shape):
        raise ControlledInterventionInstrumentationError("constructed displacement invariant shape drift")
    if not bool(torch.isfinite(displacement).all() and torch.isfinite(direction).all()):
        raise ControlledInterventionInstrumentationError("non-finite constructed displacement invariant")
    return torch.dot(displacement, direction)


def _unit_vector(vector: Any, label: str) -> tuple[Any, float]:
    torch = _torch()
    norm = float(torch.linalg.vector_norm(vector).item())
    if not torch.isfinite(torch.tensor(norm)) or norm <= protocol.NORM_FLOOR:
        raise ControlledInterventionInstrumentationError(f"degenerate vector: {label}")
    result = vector / norm
    observed = float(torch.linalg.vector_norm(result).item())
    if abs(observed - 1.0) > protocol.DIRECTION_ATOL:
        raise ControlledInterventionInstrumentationError(f"unit norm failure: {label}")
    return result, norm


def deterministic_sham_direction(attribute: str, pair_id: str, token_index: int, direction: Any) -> tuple[Any, int]:
    torch = _torch()
    if tuple(direction.shape) != (direction.numel(),) or not 0 <= token_index < protocol.LFE_TOKENS:
        raise ControlledInterventionInstrumentationError("invalid sham direction input")
    for attempt in range(16):
        namespace = f"{protocol.NAMESPACE}|{attribute}|{pair_id}|{token_index}|{attempt}"
        raw = hashlib.shake_256(namespace.encode("utf-8")).digest(direction.numel())
        dense = torch.tensor([1.0 if byte & 1 else -1.0 for byte in raw], dtype=torch.float32)
        orthogonal = dense - torch.dot(dense, direction) * direction
        norm = float(torch.linalg.vector_norm(orthogonal).item())
        if torch.isfinite(torch.tensor(norm)) and norm > protocol.NORM_FLOOR:
            sham = orthogonal / norm
            if abs(float(torch.dot(sham, direction).item())) > protocol.DIRECTION_ATOL:
                raise ControlledInterventionInstrumentationError("sham orthogonality failure")
            return sham, attempt
    raise ControlledInterventionInstrumentationError("no valid sham direction in 16 deterministic attempts")


@dataclass
class TransientInterventionBundle:
    """In-memory-only tensors; callers must never serialize this object."""

    unmodified: dict[str, Any]
    selected: dict[tuple[str, str], Any]
    directions: dict[tuple[str, str, int], Any]
    sham_directions: dict[tuple[str, str, int], Any]
    diagnostics: list[dict[str, object]]


def build_transient_interventions(
    tensors: dict[str, Any], metadata: dict[str, dict[str, str]], *, expected_dim: int = protocol.LFE_DIM
) -> TransientInterventionBundle:
    torch = _torch()
    if set(tensors) != set(metadata) or len(tensors) != 40:
        raise ControlledInterventionInstrumentationError("expected exactly 40 metadata-bound unit tensors")
    unmodified = {unit: _as_cpu_float(value, expected_dim) for unit, value in tensors.items()}
    pair_roles: dict[tuple[str, str], dict[str, str]] = defaultdict(dict)
    for unit, meta in metadata.items():
        attribute, pair_id, role = meta.get("attribute"), meta.get("formal_pair_id"), meta.get("role")
        if attribute not in protocol.ATTRIBUTES or pair_id not in protocol.pair_ids(attribute) or role not in protocol.ROLES:
            raise ControlledInterventionInstrumentationError(f"invalid metadata: {unit}")
        key = (attribute, pair_id)
        if role in pair_roles[key]:
            raise ControlledInterventionInstrumentationError(f"duplicate pair role: {key}/{role}")
        pair_roles[key][role] = unit
    expected_pairs = {(attribute, pair) for attribute in protocol.ATTRIBUTES for pair in protocol.pair_ids(attribute)}
    if set(pair_roles) != expected_pairs or any(set(value) != set(protocol.ROLES) for value in pair_roles.values()):
        raise ControlledInterventionInstrumentationError("complete pair-role crossing missing")

    normalized = {}
    for unit, tensor in unmodified.items():
        values = tensor[0]
        norms = torch.linalg.vector_norm(values, dim=1)
        if not bool(torch.isfinite(norms).all()):
            raise ControlledInterventionInstrumentationError(f"non-finite token norms: {unit}")
        normalized[unit] = values / torch.clamp(norms, min=protocol.NORM_FLOOR).unsqueeze(1)

    directions: dict[tuple[str, str, int], Any] = {}
    sham_directions: dict[tuple[str, str, int], Any] = {}
    diagnostics: list[dict[str, object]] = []
    for attribute in protocol.ATTRIBUTES:
        pairs = protocol.pair_ids(attribute)
        for held_pair in pairs:
            training_pairs = tuple(pair for pair in pairs if pair != held_pair)
            if len(training_pairs) != 9 or held_pair in training_pairs:
                raise ControlledInterventionInstrumentationError("held-pair-out partition drift")
            for token_index in range(protocol.LFE_TOKENS):
                differences = []
                for training_pair in training_pairs:
                    roles = pair_roles[(attribute, training_pair)]
                    differences.append(
                        normalized[roles["positive"]][token_index] - normalized[roles["control"]][token_index]
                    )
                mean_direction = torch.stack(differences).mean(dim=0)
                direction, pre_norm = _unit_vector(mean_direction, f"{attribute}/{held_pair}/{token_index}")
                sham, attempt = deterministic_sham_direction(attribute, held_pair, token_index, direction)
                key = (attribute, held_pair, token_index)
                directions[key] = direction
                sham_directions[key] = sham
                diagnostics.append({
                    "attribute": attribute, "formal_pair_id": held_pair, "token_index": token_index,
                    "training_pairs": 9, "held_pair_excluded": True,
                    "pre_normalization_direction_norm": pre_norm,
                    "unit_direction_norm": float(torch.linalg.vector_norm(direction).item()),
                    "sham_attempt": attempt,
                    "sham_direction_norm": float(torch.linalg.vector_norm(sham).item()),
                    "direction_sham_dot": float(torch.dot(direction, sham).item()),
                })
    if len(directions) != 640 or len(sham_directions) != 640 or len(diagnostics) != 640:
        raise ControlledInterventionInstrumentationError("direction family count drift")

    selected: dict[tuple[str, str], Any] = {}
    for (attribute, pair_id), roles in sorted(pair_roles.items()):
        for role in protocol.ROLES:
            unit, other = roles[role], roles["control" if role == "positive" else "positive"]
            base = unmodified[unit][0]
            counterpart = unmodified[other][0]
            target_tokens, sham_tokens = [], []
            for token_index in range(protocol.LFE_TOKENS):
                direction = directions[(attribute, pair_id, token_index)]
                sham_direction = sham_directions[(attribute, pair_id, token_index)]
                delta = torch.dot(counterpart[token_index] - base[token_index], direction)
                target_displacement_vector = delta * direction
                sham_displacement_vector = delta * sham_direction
                target = base[token_index] + target_displacement_vector
                sham = base[token_index] + sham_displacement_vector
                target_projection = torch.dot(target, direction)
                counterpart_projection = torch.dot(counterpart[token_index], direction)
                target_displacement = torch.linalg.vector_norm(target_displacement_vector)
                sham_displacement = torch.linalg.vector_norm(sham_displacement_vector)
                if not within_frozen_tolerance(target_projection, counterpart_projection):
                    raise ControlledInterventionInstrumentationError("target projection exchange failure")
                sham_direction_dot = constructed_displacement_direction_dot(
                    sham_displacement_vector, direction
                )
                if abs(float(sham_direction_dot.item())) > protocol.DIRECTION_ATOL:
                    raise ControlledInterventionInstrumentationError("sham displacement is not orthogonal")
                if not within_frozen_tolerance(target_displacement, sham_displacement):
                    raise ControlledInterventionInstrumentationError("target/sham displacement mismatch")
                target_tokens.append(target)
                sham_tokens.append(sham)
            selected[(unit, "baseline")] = unmodified[unit].clone()
            selected[(unit, "target_projection_exchange")] = torch.stack(target_tokens).unsqueeze(0)
            selected[(unit, "orthogonal_sham")] = torch.stack(sham_tokens).unsqueeze(0)
    if len(selected) != 120:
        raise ControlledInterventionInstrumentationError("condition tensor family count drift")
    return TransientInterventionBundle(unmodified, selected, directions, sham_directions, diagnostics)


class LFEOutputOverride:
    """Replace every LFE forward output with one selected in-memory condition tensor."""

    def __init__(self, module: Any, direct_tensor: Any, selected_tensor: Any, *, expected_dim: int = protocol.LFE_DIM):
        self.module = module
        self.direct = _as_cpu_float(direct_tensor, expected_dim)
        self.selected = _as_cpu_float(selected_tensor, expected_dim)
        self.expected_dim = expected_dim
        self.calls = 0
        self.handle = None

    def _hook(self, _module: Any, _inputs: tuple[Any, ...], output: Any) -> Any:
        torch = _torch()
        if not isinstance(output, torch.Tensor) or output.ndim != 3:
            raise ControlledInterventionInstrumentationError("LFE hook output is not a rank-3 tensor")
        if tuple(output.shape[1:]) != (protocol.LFE_TOKENS, self.expected_dim):
            raise ControlledInterventionInstrumentationError(f"hook output shape drift: {tuple(output.shape)}")
        direct = self.direct.to(device=output.device, dtype=output.dtype).expand(output.shape[0], -1, -1)
        if not within_frozen_tolerance(output, direct):
            raise ControlledInterventionInstrumentationError("direct-versus-baseline-hook mismatch")
        replacement = self.selected.to(device=output.device, dtype=output.dtype).expand(output.shape[0], -1, -1)
        if not bool(torch.isfinite(replacement).all()):
            raise ControlledInterventionInstrumentationError("non-finite selected hook tensor")
        self.calls += 1
        return replacement

    def __enter__(self) -> Self:
        if self.handle is not None:
            raise ControlledInterventionInstrumentationError("hook already installed")
        self.handle = self.module.register_forward_hook(self._hook)
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:  # noqa: PYI036
        del exc_type, exc, traceback
        if self.handle is not None:
            self.handle.remove()
            self.handle = None

    def verify_calls(self, expected: int) -> None:
        if self.handle is not None:
            raise ControlledInterventionInstrumentationError("hook must be removed before call verification")
        if self.calls != expected:
            raise ControlledInterventionInstrumentationError(f"expected {expected} hook calls, observed {self.calls}")


class TransformerInputInvariantRecorder:
    """Hash first-step denoising and spatial inputs without persisting tensors."""

    def __init__(self, transformer: Any):
        self.transformer = transformer
        self.handle = None
        self.calls = 0
        self.first: dict[str, object] | None = None

    @staticmethod
    def _digest(tensor: Any) -> str:
        value = tensor.detach().float().cpu().contiguous()
        return hashlib.sha256(value.numpy().tobytes()).hexdigest()

    def _hook(self, _module: Any, args: tuple[Any, ...], kwargs: dict[str, Any]) -> None:
        hidden = kwargs.get("hidden_states")
        if hidden is None and args:
            hidden = args[0]
        torch = _torch()
        if not isinstance(hidden, torch.Tensor) or hidden.ndim != 5 or hidden.shape[2] % 2:
            raise ControlledInterventionInstrumentationError("unexpected Transformer hidden_states for route invariant")
        if self.calls == 0:
            channels = hidden.shape[2] // 2
            self.first = {
                "initial_denoising_input_sha256": self._digest(hidden[0:1, :, :channels]),
                "spatial_reference_route_sha256": self._digest(hidden[0:1, :, channels:]),
                "hidden_shape": "x".join(str(int(value)) for value in hidden.shape),
                "hidden_dtype": str(hidden.dtype),
                "hidden_device_type": hidden.device.type,
            }
        self.calls += 1

    def __enter__(self) -> Self:
        if self.handle is not None:
            raise ControlledInterventionInstrumentationError("Transformer input recorder already installed")
        self.handle = self.transformer.register_forward_pre_hook(self._hook, with_kwargs=True)
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:  # noqa: PYI036
        del exc_type, exc, traceback
        if self.handle is not None:
            self.handle.remove()
            self.handle = None

    def finish(self, expected_calls: int) -> dict[str, object]:
        if self.handle is not None or self.calls != expected_calls or self.first is None:
            raise ControlledInterventionInstrumentationError(
                f"Transformer input recorder expected {expected_calls} calls, observed {self.calls}"
            )
        return dict(self.first)
