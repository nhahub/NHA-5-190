# Evidence corrections for the Notion page

## Fashionpedia

- **Decision:** Provisionally selected until training annotations are downloaded and checked.
- **Validation scope:** 1,158 images and 8,781 annotations in the locally inspected official validation JSON. The official project documents 48,825 total images, 27 main apparel categories, 19 apparel-part categories and 294 attributes. [Official project](https://fashionpedia.github.io/home/)
- **Attribute coverage:** 5,259 of 8,781 validation annotations contain one or more `attribute_ids` (**59.89%**), so detailed attributes are **Partial**. This was computed across the complete local validation JSON.
- **Public test labels:** the official download list provides `test_images_info2020` but no labeled test annotation file, so public test annotations are **Unavailable**. [Official repository downloads](https://github.com/cvdfoundation/fashionpedia#download)
- **Resolution:** validation images cover 182 size pairs; width ranges from 415–1,024 px and height from 471–1,024 px. The most common size is 682×1,024 (306 images). These values were computed from the complete local validation JSON.
- **Taxonomy decision:** use the 27 main apparel categories for primary garment tasks. Keep the 19 apparel-part categories as secondary localized features; do not treat parts as standalone garments.

## DeepFashion scope

“DeepFashion” is a family, not one release. The original DeepFashion site lists four benchmarks: Category and Attribute Prediction, In-shop Clothes Retrieval, Consumer-to-shop Clothes Retrieval, and Fashion Landmark Detection. It documents more than 800,000 images, 50 categories and 1,000 attributes, with access governed by a research agreement. [Original DeepFashion](https://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html)

DeepFashion-MultiModal is a separate 2022 release with 44,096 high-resolution images and a 12,701-image full-body subset containing 24-class parsing masks, keypoints and DensePose; it also documents shape, texture and text annotations. It is the **backup** only for future full-body parsing, pose and text work. Its annotations are **Documented, not verified locally**. [DeepFashion-MultiModal](https://github.com/yumingj/DeepFashion-MultiModal)

The original Category/Attribute and retrieval subsets were considered for item categories, attributes and retrieval. They were not selected for M1 because Fashionpedia already covers the core garment annotation need, access requires the DeepFashion agreement, and adding them would create another taxonomy before the primary loaders are stable. [Original DeepFashion](https://mmlab.ie.cuhk.edu.hk/projects/DeepFashion.html)

## Polyvore evidence and size

- **Access:** approved and downloaded on 2026-09-21.
- **Local validation:** the disjoint validation parquet has 14,657 rows. Rows 0–4 were opened; image content matched the metadata category in all five cases, and every item had validation outfit membership. [Local report](../../data/samples/polyvore_outfits/inspection_report.md)
- **Storage:** use **4.3 GB** for the current Hugging Face repack. [Current dataset page](https://huggingface.co/datasets/mvasil/polyvore-outfits)
- **Why 6 GB also appeared:** the older fashion-compatibility README labels its historical download archive as 6G. [Older implementation README](https://github.com/mvasil/fashion-compatibility)
- **Source separation:** list `xthan/polyvore-dataset` as the official source for the original Polyvore dataset. List `mvasil/polyvore-outfits` only in the Polyvore Outfits section. [Original Polyvore](https://github.com/xthan/polyvore-dataset) · [Polyvore Outfits](https://huggingface.co/datasets/mvasil/polyvore-outfits)

## Page cleanup

1. Delete the stray “Official source” line, “COVERAGE AND FORMAT” line, and empty `#` / `##` headings.
2. Move **Decision: Backup** directly under the DeepFashion-MultiModal section, before the Polyvore section.
3. Replace unsupported availability labels with **Documented, not verified locally**.
4. Keep every factual claim beside its official link or the local evidence path above.
