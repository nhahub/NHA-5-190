# M2 sample palette review

Reviewed on 2026-10-08 by Codex using the generated image/palette contact sheet for
all 18 successful sample records. This is a prototype visual inspection, not a
ground-truth color evaluation or final team acceptance.

| Sample/group | Observations and disposition |
|---|---|
| Fashionpedia `008929`, `008930` shoes | Black/dark and red-orange clusters match the visible shoe pixels; light background also contributes. Retain with crop/background caveat. |
| Fashionpedia `008931`, `008932` trousers/belt region | Dark colors dominate. The trousers crop includes a red shoe and light background; its palette cannot be described as trousers-only. |
| Fashionpedia `002554` glasses | Dark lenses and skin tones are both represented. A box cannot isolate the glasses from the face. |
| Fashionpedia `002555` neck/tie region | Mixed collar/tie/skin colors; small crop. Review isolation before final use. |
| Fashionpedia `002557` shirt | Red and dark blue clusters match the plaid shirt; small surrounding regions remain. |
| Fashionpedia `002565` cardigan | Red/dark clusters match the cardigan, but the largest light cluster includes scenery and the crop contains the shirt. Requires a better garment mask for garment-only color. |
| Fashionpedia `006415` printed top | Dark top is represented; gray/green scenery and skin contribute additional clusters. |
| Fashionpedia `005698` vest | Light fabric is represented alongside skin and black jacket; mixed-garment crop. |
| Fashionpedia `005699` jacket | Dark jacket and tan background/skin are both visible in the palette. Existing upstream crop concern is confirmed; not an isolated jacket measurement. |
| Fashionpedia `005700` watch | The derivative is a very thin, mostly dark region. Successful decoding/extraction does not establish a useful watch palette. Flag for upstream crop review. |
| Fashionpedia `002371` top | Red/dark cloth is represented; some surrounding background/skin is included. |
| Polyvore `114380093` black bag | Dark bag colors are present, but the light background cluster is largest (about 37.5%). Retain as an explicitly unmasked product-photo palette. |
| Polyvore `156386331` sandals | Light background occupies about 57.5%; black straps and beige sole remain in smaller clusters. Needs a mask for final garment-only proportions. |
| Polyvore `138007061` metallic shoes | Light background occupies about 58.5%; metallic/dark tones are represented. White-background removal must not remove the light shoe surfaces. |
| Polyvore `50479717` shorts | Product photo includes the person, skin and white background; the palette is not shorts-only. Needs an item region/mask. |
| Polyvore `213366441` bag | Beige woven fabric dominates; darker printed areas and pink trim are represented. White background is also included. |

All 18 outputs correctly carry `background_contamination_possible=true`. The
implementation intentionally does not strip white pixels or label an unmasked crop
as mask-isolated. Numerical correctness and pixel coverage pass; semantic garment
isolation remains limited by supplied geometry.

The color component is ready for review and sample integration with these caveats.
Before final garment-only feature caching, Hanaa/Ziad should supply or review suitable
regions/masks, especially for the jacket, watch, glasses and person-containing product
photo. Final acceptance and any decision to retain fallback features belong to team
review. The supplied samples do not support a full-dataset accuracy claim.
