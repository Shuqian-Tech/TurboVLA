"""Trainable PyTorch TurboVLA-Lite student with fixed hardware shapes."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping

import torch
from torch import nn
from torch.nn import functional as F

from turbovla.distillation import token_relation_matrix


@dataclass(frozen=True)
class LiteStudentConfig:
    contract_version: str = "0.2.0"
    hidden_dim: int = 128
    visual_tokens: int = 32
    conv_channels: int = 16
    action_hidden: int = 64
    instruction_table_size: int = 256
    state_dim: int = 8
    action_horizon: int = 12
    action_dim: int = 7
    state_normalization: float = 1.0 / 1024.0
    fake_quant: bool = True
    action_loss_weight: float = 1.0
    teacher_action_loss_weight: float = 1.0
    feature_loss_weight: float = 0.1
    visual_encoder: str = "pointwise"

    @classmethod
    def from_contract(cls, contract: Mapping, calibration_path: Path | None = None) -> "LiteStudentConfig":
        # T015 changes the runtime/model-pack ABI; the selected checkpoint schema remains v0.2.
        if contract["contract_version"] not in {"0.2.0", "0.3.0"}:
            raise ValueError(f"unsupported contract version {contract['contract_version']!r}")
        config = cls(
            hidden_dim=int(contract["fusion"]["hidden_dim"]),
            visual_tokens=int(contract["visual_tokens"]["shape"][1]),
            state_dim=int(contract["state"]["shape"][1]),
            action_horizon=int(contract["action"]["shape"][1]),
            action_dim=int(contract["action"]["shape"][2]),
        )
        if calibration_path is not None:
            payload = json.loads(calibration_path.read_text(encoding="utf-8"))
            if not payload.get("activations") or not payload.get("weights"):
                raise ValueError("calibration metadata must contain activation and weight scales")
        return config

    def to_dict(self) -> dict:
        return asdict(self)


class SymmetricFakeQuant(nn.Module):
    """Straight-through symmetric INT8 fake quantizer."""

    def __init__(self, scale: float = 1.0 / 127.0) -> None:
        super().__init__()
        if scale <= 0:
            raise ValueError("fake quant scale must be positive")
        self.register_buffer("scale", torch.tensor(float(scale), dtype=torch.float32))

    def forward(self, value: torch.Tensor) -> torch.Tensor:
        quantized = torch.clamp(torch.round(value / self.scale), -128, 127) * self.scale
        return value + (quantized - value).detach()


class TurboVLALiteStudent(nn.Module):
    """Fixed-shape CNN, gated fusion and action MLP student."""

    def __init__(self, config: LiteStudentConfig = LiteStudentConfig(), quantization: Mapping | None = None) -> None:
        super().__init__()
        if config.visual_encoder not in {"pointwise", "depthwise_separable"}:
            raise ValueError(f"unsupported visual encoder {config.visual_encoder!r}")
        self.config = config
        self.conv = nn.Conv2d(3, config.conv_channels, kernel_size=1, bias=True)
        self.spatial_pool = nn.AdaptiveAvgPool2d((16, 16))
        self.spatial_depthwise = nn.ModuleList()
        self.spatial_pointwise = nn.ModuleList()
        if config.visual_encoder == "depthwise_separable":
            for _ in range(2):
                self.spatial_depthwise.append(
                    nn.Conv2d(
                        config.conv_channels,
                        config.conv_channels,
                        kernel_size=3,
                        padding=1,
                        groups=config.conv_channels,
                        bias=True,
                    )
                )
                pointwise = nn.Conv2d(config.conv_channels, config.conv_channels, kernel_size=1, bias=True)
                nn.init.zeros_(pointwise.weight)
                nn.init.zeros_(pointwise.bias)
                self.spatial_pointwise.append(pointwise)
        self.token_pool = nn.AdaptiveAvgPool2d((4, 8))
        self.visual_projection = nn.Linear(config.conv_channels, config.hidden_dim)
        self.instruction_embedding = nn.Embedding(config.instruction_table_size, config.hidden_dim)
        self.fusion_visual = nn.ModuleList(nn.Linear(config.hidden_dim, config.hidden_dim) for _ in range(2))
        self.fusion_language = nn.ModuleList(
            nn.Linear(config.hidden_dim, config.hidden_dim, bias=False) for _ in range(2)
        )
        self.fusion_gate = nn.ModuleList(nn.Linear(config.hidden_dim, config.hidden_dim, bias=False) for _ in range(2))
        self.state_projection = nn.Linear(config.state_dim, config.hidden_dim)
        self.action_input = nn.Linear(config.hidden_dim, config.action_hidden)
        self.action_output = nn.Linear(config.action_hidden, config.action_horizon * config.action_dim)
        scales = dict((quantization or {}).get("activations", {}))
        self.quantizers = nn.ModuleDict(
            {name: SymmetricFakeQuant(float(scales[name])) for name in scales} if config.fake_quant else {}
        )
        weight_scales = dict((quantization or {}).get("weights", {}))
        self.weight_quantizers = nn.ModuleDict(
            {name: SymmetricFakeQuant(float(weight_scales[name])) for name in weight_scales}
            if config.fake_quant
            else {}
        )

    def _fake_quant(self, name: str, value: torch.Tensor) -> torch.Tensor:
        quantizer = self.quantizers[name] if name in self.quantizers else None
        return quantizer(value) if quantizer is not None else value

    def _linear(self, module: nn.Linear, value: torch.Tensor, weight_name: str) -> torch.Tensor:
        quantizer = self.weight_quantizers[weight_name] if weight_name in self.weight_quantizers else None
        weight = quantizer(module.weight) if quantizer is not None else module.weight
        return F.linear(value, weight, module.bias)

    def _conv2d(
        self,
        module: nn.Conv2d,
        value: torch.Tensor,
        weight_name: str,
    ) -> torch.Tensor:
        quantizer = self.weight_quantizers[weight_name] if weight_name in self.weight_quantizers else None
        weight = quantizer(module.weight) if quantizer is not None else module.weight
        return F.conv2d(
            value,
            weight,
            module.bias,
            stride=module.stride,
            padding=module.padding,
            dilation=module.dilation,
            groups=module.groups,
        )

    def forward(
        self, image: torch.Tensor, state: torch.Tensor, instruction_id: torch.Tensor
    ) -> dict[str, torch.Tensor]:
        if image.shape != (image.shape[0], 1, 3, 128, 128) or image.dtype != torch.uint8:
            raise ValueError(f"image must be uint8 [B,1,3,128,128], got {image.dtype} {tuple(image.shape)}")
        if state.ndim != 2 or state.shape[1] != self.config.state_dim:
            raise ValueError(f"state must be [B,{self.config.state_dim}], got {tuple(state.shape)}")
        if instruction_id.ndim != 1 or instruction_id.shape[0] != image.shape[0]:
            raise ValueError("instruction_id must be [B] and match image batch")
        if torch.any(instruction_id < 0) or torch.any(instruction_id >= self.config.instruction_table_size):
            raise ValueError("instruction_id is outside the fixed embedding table")

        normalized = image.float() / 255.0
        mean = normalized.new_tensor([0.485, 0.456, 0.406]).view(1, 1, 3, 1, 1)
        std = normalized.new_tensor([0.229, 0.224, 0.225]).view(1, 1, 3, 1, 1)
        normalized = self._fake_quant("image_normalized", (normalized - mean) / std)
        conv_weight = self.conv.weight
        if "conv_weight" in self.weight_quantizers:
            conv_weight = self.weight_quantizers["conv_weight"](conv_weight)
        conv = torch.relu(F.conv2d(normalized[:, 0], conv_weight, self.conv.bias))
        conv = self._fake_quant("visual_conv", conv)
        spatial_outputs: list[torch.Tensor] = []
        visual_map = conv
        if self.config.visual_encoder == "depthwise_separable":
            visual_map = self.spatial_pool(visual_map)
            for layer, (depthwise, pointwise) in enumerate(
                zip(self.spatial_depthwise, self.spatial_pointwise, strict=True)
            ):
                spatial = torch.relu(self._conv2d(depthwise, visual_map, "spatial_depthwise"))
                spatial = self._conv2d(pointwise, spatial, "spatial_pointwise")
                visual_map = torch.relu(visual_map + spatial)
                visual_map = self._fake_quant(f"spatial_{layer}", visual_map)
                spatial_outputs.append(visual_map)
        pooled = self.token_pool(visual_map).flatten(2).transpose(1, 2)
        visual = torch.relu(self._linear(self.visual_projection, pooled, "visual_projection"))
        visual = self._fake_quant("visual_tokens", visual)
        language = self._fake_quant("language_embedding", self.instruction_embedding(instruction_id))

        fused = visual
        fusion_outputs: list[torch.Tensor] = []
        for layer in range(2):
            candidate = self._linear(self.fusion_visual[layer], fused, "fusion_visual")
            candidate += self._linear(self.fusion_language[layer], language, "fusion_language").unsqueeze(1)
            gate = torch.sigmoid(
                self._linear(self.fusion_gate[layer], fused, "fusion_gate")
                + self._linear(self.fusion_gate[layer], language, "fusion_gate").unsqueeze(1)
            )
            fused = (1.0 - gate) * fused + gate * torch.tanh(candidate)
            fused = self._fake_quant(f"fusion_{layer}", fused)
            fusion_outputs.append(fused)

        state_float = state.float() * self.config.state_normalization
        pooled_state = torch.relu(
            fused.mean(dim=1) + self._linear(self.state_projection, state_float, "state_projection")
        )
        pooled_state = self._fake_quant("state_projection", pooled_state)
        hidden = torch.relu(self._linear(self.action_input, pooled_state, "action_input"))
        hidden = self._fake_quant("action_hidden", hidden)
        logits = self._linear(self.action_output, hidden, "action_output").view(
            -1, self.config.action_horizon, self.config.action_dim
        )
        action = torch.tanh(logits)
        outputs = {
            "image_normalized": normalized,
            "visual_conv": conv,
            "visual_tokens": visual,
            "language_embedding": language,
            "fusion_0": fusion_outputs[0],
            "fusion_1": fusion_outputs[1],
            "state_projection": pooled_state,
            "action_hidden": hidden,
            "action": action,
        }
        outputs.update({f"spatial_{layer}": value for layer, value in enumerate(spatial_outputs)})
        return outputs


def lite_distillation_loss(
    outputs: Mapping[str, torch.Tensor],
    action_target: torch.Tensor,
    teacher_action: torch.Tensor,
    teacher_visual_relation: torch.Tensor,
    config: LiteStudentConfig,
    action_mask: torch.Tensor | None = None,
    gripper_loss_weight: float = 1.0,
) -> tuple[torch.Tensor, dict[str, float]]:
    """Combine ground-truth action, teacher action and visual feature losses."""

    action_loss = masked_action_l1(
        outputs["action"], action_target, action_mask, gripper_loss_weight
    )
    teacher_action_loss = masked_action_l1(
        outputs["action"], teacher_action, action_mask, gripper_loss_weight
    )
    student_relation = token_relation_matrix(outputs["fusion_1"])
    if teacher_visual_relation.shape != student_relation.shape:
        raise ValueError(
            "teacher visual relation must match the student's [B,32,32] relation matrix, "
            f"got {tuple(teacher_visual_relation.shape)}"
        )
    feature_loss = torch.nn.functional.mse_loss(student_relation, teacher_visual_relation.float())
    total = (
        config.action_loss_weight * action_loss
        + config.teacher_action_loss_weight * teacher_action_loss
        + config.feature_loss_weight * feature_loss
    )
    return total, {
        "loss": float(total.detach().cpu()),
        "action_l1": float(action_loss.detach().cpu()),
        "teacher_action_l1": float(teacher_action_loss.detach().cpu()),
        "feature_relation_mse": float(feature_loss.detach().cpu()),
    }


def masked_action_l1(
    prediction: torch.Tensor,
    target: torch.Tensor,
    action_mask: torch.Tensor | None = None,
    gripper_loss_weight: float = 1.0,
) -> torch.Tensor:
    if prediction.shape != target.shape or prediction.ndim != 3:
        raise ValueError("prediction and target must have matching [B,H,A] shapes")
    if gripper_loss_weight <= 0:
        raise ValueError("gripper loss weight must be positive")
    if action_mask is None:
        action_mask = torch.ones(prediction.shape[:2], device=prediction.device, dtype=prediction.dtype)
    if action_mask.shape != prediction.shape[:2]:
        raise ValueError("action mask must have shape [B,H]")
    mask = action_mask.to(device=prediction.device, dtype=prediction.dtype).unsqueeze(-1)
    weights = torch.ones(prediction.shape[-1], device=prediction.device, dtype=prediction.dtype)
    weights[-1] = gripper_loss_weight
    denominator = mask.sum() * weights.sum()
    return (torch.abs(prediction - target) * mask * weights).sum() / denominator.clamp_min(1.0)
