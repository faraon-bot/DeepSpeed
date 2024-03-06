# Copyright (c) Microsoft Corporation.
# SPDX-License-Identifier: Apache-2.0

# DeepSpeed Team

import os

from .builder import CUDAOpBuilder, installed_cuda_version


class InferenceCoreBuilder(CUDAOpBuilder):
    BUILD_VAR = "DS_BUILD_INFERENCE_CORE_OPS"
    NAME = "inference_core_ops"

    def __init__(self, name=None):
        name = self.NAME if name is None else name
        super().__init__(name=name)

    def absolute_name(self):
        return f'deepspeed.inference.v2.kernels{self.NAME}'

    def is_compatible(self, verbose=True):
        try:
            import torch
        except ImportError:
            self.warning("Please install torch if trying to pre-compile inference kernels")
            return False

        cuda_okay = True
        if not self.is_rocm_pytorch() and torch.cuda.is_available():  #ignore-cuda
            sys_cuda_major, _ = installed_cuda_version()
            torch_cuda_major = int(torch.version.cuda.split('.')[0])
            cuda_capability = torch.cuda.get_device_properties(0).major  #ignore-cuda
            if cuda_capability < 6:
                self.warning("NVIDIA Inference is only supported on Pascal and newer architectures")
                cuda_okay = False
            if cuda_capability >= 8:
                if torch_cuda_major < 11 or sys_cuda_major < 11:
                    self.warning("On Ampere and higher architectures please use CUDA 11+")
                    cuda_okay = False
        return super().is_compatible(verbose) and cuda_okay

    def filter_ccs(self, ccs):
        ccs_retained = []
        ccs_pruned = []
        for cc in ccs:
            if int(cc[0]) >= 6:
                ccs_retained.append(cc)
            else:
                ccs_pruned.append(cc)
        if len(ccs_pruned) > 0:
            self.warning(f"Filtered compute capabilities {ccs_pruned}")
        return ccs_retained

    def get_prefix(self):
        ds_path = self.deepspeed_src_path("deepspeed")
        return "deepspeed" if os.path.isdir(ds_path) else ".."

    def sources(self):
        sources = [
            "inference/v2/kernels/core_ops/core_ops.cpp",
            "inference/v2/kernels/core_ops/bias_activations/bias_activation.cpp",
            "inference/v2/kernels/core_ops/bias_activations/bias_activation_cuda.cu",
            "inference/v2/kernels/core_ops/cuda_layer_norm/layer_norm.cpp",
            "inference/v2/kernels/core_ops/cuda_layer_norm/layer_norm_cuda.cu",
            "inference/v2/kernels/core_ops/cuda_rms_norm/rms_norm.cpp",
            "inference/v2/kernels/core_ops/cuda_rms_norm/rms_norm_cuda.cu",
            "inference/v2/kernels/core_ops/gated_activations/gated_activation_kernels.cpp",
            "inference/v2/kernels/core_ops/gated_activations/gated_activation_kernels_cuda.cu",
        ]

        # The source files with specific GPU architecture requirements.
        if not self.is_rocm_pytorch() and torch.cuda.is_available():  #ignore-cuda
            cuda_capability = torch.cuda.get_device_properties(0).major  #ignore-cuda
            if cuda_capability != 8:
                self.warning("FP6 quantization kernel is only supported on Ampere architectures")
            else:
                sources.append("inference/v2/kernels/core_ops/cuda_linear/fp6_linear.cu")
                sources.append("inference/v2/kernels/core_ops/cuda_linear/cuda_linear_kernels.cpp")

        prefix = self.get_prefix()
        sources = [os.path.join(prefix, src) for src in sources]
        return sources

    def extra_ldflags(self):
        return []

    def include_paths(self):
        sources = [
            'inference/v2/kernels/core_ops/bias_activations',
            'inference/v2/kernels/core_ops/blas_kernels',
            'inference/v2/kernels/core_ops/cuda_layer_norm',
            'inference/v2/kernels/core_ops/cuda_rms_norm',
            'inference/v2/kernels/core_ops/gated_activations',
            'inference/v2/kernels/core_ops/cuda_linear',
            'inference/v2/kernels/includes',
        ]

        prefix = self.get_prefix()
        sources = [os.path.join(prefix, src) for src in sources]

        return sources
