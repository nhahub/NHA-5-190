from __future__ import annotations

import importlib
from typing import Any

IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def build_transforms(train: bool = False, image_size: tuple[int, int] = (224, 224)) -> Any:
    """Build the M1 transform; augmentation is enabled only for training."""
    transforms = importlib.import_module("torchvision.transforms")
    interpolation = transforms.InterpolationMode

    operations = [
        transforms.Resize(image_size, interpolation=interpolation.BILINEAR),
    ]
    if train:
        operations.append(transforms.RandomHorizontalFlip(p=0.5))
    operations.extend(
        [
            transforms.ToTensor(),
            transforms.Normalize(IMAGENET_MEAN, IMAGENET_STD),
        ]
    )
    return transforms.Compose(operations)
