"""Prompt templates for the Nano Banana Pro nail try-on PoC.

Every change to a prompt is a new VERSION entry so a run's meta.json can say
exactly which wording produced which image.
"""

PROMPT_VERSION = "v1"

# Image order sent to the model: [hand photo, reference photo]; the prompt
# refers to them as Image 1 / Image 2 in that order.
BASE = """\
Image 1 is a customer's hand photographed in a nail salon. Image 2 is a reference photo of a nail design the customer wants.

Task: apply the nail design from Image 2 onto every visible fingernail in Image 1.

Rules:
- Match finger by finger. If the reference uses different art on different fingers (accent nails), put each design on the same finger as in the reference.
- Reproduce the design faithfully: base colour, finish (glossy gel, cat-eye, chrome, matte, jelly), French tips, patterns, foil, glitter, rhinestones and charms, in the same positions and amounts as the reference.
- Keep everything in Image 1 that is not a nail surface completely unchanged: hand pose, finger count and proportions, skin tone and texture, rings, sleeves, lighting direction, shadows, background, framing and camera angle.
- {shape_rule}
- Render photorealistically: the polish must follow the curvature of each nail with correct specular highlights consistent with the light in Image 1, a clean natural cuticle line, a visible free edge, and the slightly translucent look of real gel. No sticker-like flat colour.
- Output only the edited photograph. No text, no watermark, no extra jewellery, no collage.
"""

SHAPE_KEEP = (
    "Keep the customer's own nail length and nail shape exactly as in Image 1; "
    "only the surface design changes."
)
SHAPE_ADOPT = (
    "Give the nails the length and shape shown in Image 2 (as if extensions were applied), "
    "blended naturally into the customer's fingers."
)


def build(adopt_shape: bool = False, notes: str = "") -> str:
    text = BASE.format(shape_rule=SHAPE_ADOPT if adopt_shape else SHAPE_KEEP)
    if notes:
        text += "\nAdditional instructions from the nail technician:\n" + notes.strip() + "\n"
    return text
