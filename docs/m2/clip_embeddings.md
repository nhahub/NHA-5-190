\# M2 CLIP Image Embeddings



\## Purpose and status



This document describes WARDIQ's CLIP image-embedding extraction component, implemented in `src/wardiq/representation/clip\_embeddings.py`.



\*\*Status: prototype implemented; full M2 acceptance is not established.\*\*



The current prototype produces normalized CLIP image embeddings and an item inventory. It does not establish full accepted-dataset coverage, a completed model comparison, or final M2 representation integration.



\## Environment setup



Run commands from the repository root with a supported Python environment.



Install the project's ML dependencies:



```powershell

python -m pip install -e ".\[ml]"

```



For development and testing, install the relevant additional dependencies:



```powershell

python -m pip install -e ".\[dev,data,ml]"

```



The project declares Python 3.10 or newer. Use the dependency constraints in `pyproject.toml` rather than relying on versions installed in an individual environment.



\## Implementation



The extraction module provides:



\- `load\_usable\_manifest()` — loads the manifest, validates required columns, filters usable derivatives, checks item IDs, and resolves image paths.

\- `normalize\_embeddings()` — validates and normalizes embedding vectors.

\- `validate\_embedding\_artifact()` — checks the embedding artifact's expected properties.

\- `extract\_clip\_embeddings()` — extracts image embeddings and saves the prototype artifacts.



The model identifier is `openai/clip-vit-base-patch32`. The expected embedding dimension is 512, the output dtype is `float32`, and vectors are L2-normalized.



The current code does not pin `CLIP\_MODEL\_REVISION`. Metadata records a revision only when one is supplied or resolved from the loaded model configuration. Reproducible comparisons should record and pin the exact model revision.



\## Prototype artifacts



The verified prototype output directory is:



`artifacts/m2/clip\_embeddings\_prototype/`



It contains:



| File | Purpose |

|---|---|

| `clip\_embeddings.npy` | Numerical embedding matrix |

| `clip\_inventory.csv` | Item metadata and embedding-row mapping |

| `metadata.json` | Model and extraction metadata |



The output directory is generated locally and is not intended to be committed to Git.



The prototype metadata records:



\- Model identifier and embedding version

\- Embedding dimension, dtype, and normalization status

\- Image size and execution device

\- Model revision information, when available

\- Item count, source manifest, and output filenames

\- A `prototype\_only` flag



\## Verified prototype results



The inspected prototype contains 23 items:



| Dataset | Split | Items |

|---|---|---:|

| Fashion-MNIST | train | 5 |

| Fashionpedia | validation | 13 |

| Polyvore Outfits | disjoint/validation | 5 |

| \*\*Total\*\* | | \*\*23\*\* |



Local checks confirmed 23 inventory rows, 23 unique item IDs, sequential embedding-row indices from 0 through 22, and the existence of the source manifest referenced in the metadata.



The local test command is:



```powershell

python -m pytest tests/test\_clip\_embeddings.py -v

```



The latest recorded result was six passing tests. These tests cover embedding normalization and validation, manifest filtering and path resolution, and missing-image handling. They do not constitute a full end-to-end extraction test.



\## Reproduction status and limitation



The extraction function currently exists as a Python API; no CLIP-specific command-line entry point or documented invocation was found in the inspected repository files.



The prototype was generated using the repository's local M1 garment manifest. Its 23-item output is not evidence that the complete accepted M1 population has been embedded.



Before claiming reproducible full-scale extraction, the team must document and verify:



1\. The canonical input manifest and its expected item population.

2\. The exact invocation, including output directory and batch size.

3\. The pinned model revision and relevant environment versions.

4\. The expected item count, embedding shape, and inventory schema.

5\. That every inventory row maps to the correct embedding row and accepted M1 item.

6\. The documented exclusions and dataset/split provenance.



Generated embeddings and other caches should remain outside version control.



\## Remaining M2 work



The following work is not established as complete by the prototype:



\- Full accepted-population embedding extraction and inventory reconciliation.

\- A pinned model revision and reproducible experiment configuration.

\- End-to-end tests covering extraction and saved-artifact consistency.

\- Documented CLIP experiments and comparison results using approved splits and metrics.

\- Final representation integration and agreement on the cache/schema contract with the relevant M2 owners.



The 23-item prototype demonstrates that the core extraction and normalization path works on the tested samples. It should not be treated as proof that all M2 acceptance criteria have been met.

