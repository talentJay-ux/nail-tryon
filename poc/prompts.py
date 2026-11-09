"""Prompt templates for the Nano Banana Pro nail try-on PoC.

Every change to a prompt is a new VERSION entry so a run's meta.json can say
exactly which wording produced which image.
"""

PROMPT_VERSION = "v2.2"  # v2.2: explicit opaque free-edge rule  # v2: design-spec block from extract.py; v2.1: base no longer asks for a visible free edge / translucency

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
- Render photorealistically: the polish must follow the curvature of each nail with correct specular highlights consistent with the light in Image 1, a clean natural cuticle line and the depth of real gel. Coverage (opaque vs sheer) follows the design specification below when present, otherwise the reference. No sticker-like flat colour.
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


SPEC_BLOCK = """
Design specification extracted from Image 2 (authoritative; where the photo is ambiguous, follow this):
- Body colour: {base_color_hex} ({base_color_name}). Match this colour closely. Keep the lighting of Image 1, but do not shift the hue, do not make the polish paler, greyer or more washed out than this.
- Coverage: {opacity}. {coverage_rule}
- Finish: {finish}; sheen: {sheen}. Do not add stronger pearl, cat-eye or chrome effects than described.
- Nail art: {art_summary}
- Per finger: {fingers}
- Reproduction notes: {render_notes}
"""

COVERAGE = {
    "opaque": ("Full, even coverage like thick opaque enamel: the natural nail plate must not show through. "
               "The FREE EDGE (the part of the nail that extends past the fingertip) must be painted in exactly the same "
               "opaque colour and brightness as the rest of the nail: not lighter, not whiter, not translucent, not backlit; "
               "no light passes through it and nothing is visible behind it."),
    "semi-sheer": "Slightly translucent body, but no distinct whitish free edge.",
    "sheer": "Translucent glaze through which the natural nail and tip show softly.",
}


def spec_block(spec: dict) -> str:
    o = spec["overall"]
    fingers = "; ".join(f"{f['finger']}: {f['design']}" for f in spec.get("fingers", [])) or "all the same"
    return SPEC_BLOCK.format(
        base_color_hex=o["base_color_hex"], base_color_name=o["base_color_name"],
        opacity=o["opacity"], coverage_rule=COVERAGE.get(o["opacity"], ""),
        finish=o["finish"], sheen=o["sheen"], art_summary=o["art_summary"],
        fingers=fingers, render_notes=spec.get("render_notes", ""),
    )


def build(adopt_shape: bool = False, notes: str = "", spec: dict | None = None) -> str:
    text = BASE.format(shape_rule=SHAPE_ADOPT if adopt_shape else SHAPE_KEEP)
    if spec:
        text += spec_block(spec)
    if notes:
        text += "\nAdditional instructions from the nail technician:\n" + notes.strip() + "\n"
    return text
