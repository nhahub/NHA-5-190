# Dataset-to-task matrix

Status vocabulary: **Supported**, **Unavailable**, **Requires investigation**, or **Documented, not verified locally**.

| Intended use | Fashionpedia | Polyvore Outfits | Fashion-MNIST | DeepFashion-MultiModal |
|---|---|---|---|---|
| Garment detection / boxes | **Supported** — boxes exist in COCO-style annotations. [Source](https://github.com/cvdfoundation/fashionpedia) | **Unavailable** — item images and outfit links, no boxes. [Source](https://huggingface.co/datasets/mvasil/polyvore-outfits) | **Unavailable** — centered 28×28 classification images. [Source](https://github.com/zalandoresearch/fashion-mnist) | **Documented, not verified locally** — full-body parsing/keypoint subset, not item-box benchmark. [Source](https://github.com/yumingj/DeepFashion-MultiModal) |
| Instance segmentation | **Supported** — masks exist in validation annotations. [Source](https://github.com/cvdfoundation/fashionpedia) | **Unavailable**. [Source](https://huggingface.co/datasets/mvasil/polyvore-outfits) | **Unavailable**. [Source](https://github.com/zalandoresearch/fashion-mnist) | **Documented, not verified locally** — 24-class human parsing is documented. [Source](https://github.com/yumingj/DeepFashion-MultiModal) |
| Garment category labels | **Supported** — 27 main apparel categories and 19 apparel-part categories. [Source](https://fashionpedia.github.io/home/) | **Supported** — item metadata includes semantic categories; verified in five local validation records. [Local evidence](../data/samples/polyvore_outfits/inspection_report.md) | **Supported for basic checks only** — 10 coarse classes. [Source](https://github.com/zalandoresearch/fashion-mnist) | **Documented, not verified locally**. [Source](https://github.com/yumingj/DeepFashion-MultiModal) |
| Fine-grained attributes | **Supported with partial coverage** — 5,259 of 8,781 validation annotations contain at least one attribute ID (59.89% local full-split check). [Local evidence](review_corrections.md) | **Unavailable as structured attributes**; free-text metadata may exist. [Source](https://huggingface.co/datasets/mvasil/polyvore-outfits) | **Unavailable**. [Source](https://github.com/zalandoresearch/fashion-mnist) | **Documented, not verified locally** — shape, texture and text descriptions are documented. [Source](https://github.com/yumingj/DeepFashion-MultiModal) |
| Outfit compatibility / recommendation | **Unavailable**. [Source](https://github.com/cvdfoundation/fashionpedia) | **Supported** — outfit membership and compatibility splits are present; five validation images were checked locally. [Source](https://huggingface.co/datasets/mvasil/polyvore-outfits) · [Local evidence](../data/samples/polyvore_outfits/inspection_report.md) | **Unavailable**. [Source](https://github.com/zalandoresearch/fashion-mnist) | **Unavailable for labeled compatibility**. [Source](https://github.com/yumingj/DeepFashion-MultiModal) |
| Loader / preprocessing smoke tests | **Supported**. [Local sample](../data/samples/fashionpedia/inspection_report.md) | **Supported**. [Local sample](../data/samples/polyvore_outfits/inspection_report.md) | **Supported; intended role**. [Local sample](../data/samples/fashion_mnist/) | **Requires investigation** after access and sample verification. [Source](https://github.com/yumingj/DeepFashion-MultiModal) |

## Dataset decisions

| Dataset | Decision | Reason |
|---|---|---|
| Fashionpedia | **Provisionally selected** | Best current source for garment boxes, masks, categories and attributes; training annotations still need local verification. |
| Polyvore Outfits | **Selected** | Access was approved and the disjoint-validation file passed a five-image metadata, label and outfit-membership check. |
| Fashion-MNIST | **For basic checks only** | Useful for deterministic loader and preprocessing checks; classes do not map to Fashionpedia or DeepFashion. |
| DeepFashion-MultiModal | **Backup** | Useful for later full-body parsing, pose, texture and text experiments; not locally verified. |

## Open decisions

| Decision | Owner | Needed by | Current default |
|---|---|---|---|
| Approve Fashionpedia's 27 garment categories as the primary taxonomy and keep its 19 part categories as secondary localized features. | Project lead with ML team | Before unified label schema | Use the proposed split; do not treat parts as standalone garments. |
| Confirm Fashionpedia training annotations after download. | Dataset owner | Before model training | Keep selection provisional. |
| Decide whether DeepFashion-MultiModal adds enough value for M1. | Project lead | Before any large download | Keep as backup; do not block core work. |
| Approve any cross-dataset category mapping. | Project lead with ML team | After per-dataset loaders work | No mapping in M1. |
| Confirm official repository paths when the instructor sends the repository. | Repository owner | On repository receipt | Copy this convention unchanged, then update paths. |

## Polyvore fallback

Access is currently approved. If access is later revoked or the data cannot be used, continue metadata-only exploration with the original Polyvore release and remove compatibility-model training from M1; the project lead owns that scope decision. [Original dataset](https://github.com/xthan/polyvore-dataset)
