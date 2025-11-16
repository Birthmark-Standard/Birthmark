# Birthmark Modification Level Classification Guide

This guide defines which image editing operations belong in **Level 1 (Minor Modifications)** versus **Level 2 (Heavy Modifications)** for the Birthmark Standard.

## Philosophy

The classification system follows professional photojournalism standards and distinguishes between:

- **Level 1**: Routine adjustments that preserve substantive content (what was in the frame)
- **Level 2**: Operations that add, remove, or significantly alter content

The guiding principle: **Would this operation be acceptable in photojournalism?**

## Quick Reference Table

| Operation Category | Level 1 | Level 2 |
|-------------------|---------|---------|
| **Exposure & Tone** | ✓ Brightness, Contrast, Curves, Levels | ✗ Extreme adjustments that obscure original |
| **Color Correction** | ✓ White balance, Hue, Saturation, Color balance | ✗ Replacing colors entirely |
| **Cropping** | ✓ Any cropping amount | ✗ N/A (cropping is always Level 1) |
| **Rotation** | ✓ Straightening, 90° rotations, flipping | ✗ N/A (rotation is always Level 1) |
| **Sharpening** | ✓ Unsharp Mask, Sharpen | ✗ Oversharpening that creates artifacts |
| **Noise Reduction** | ✓ Despeckle, Denoise | ✗ Heavy smoothing that removes detail |
| **Lens Correction** | ✓ Distortion, Vignette, Chromatic aberration | ✗ N/A (lens correction is always Level 1) |
| **Cloning/Healing** | ✗ All cloning operations | ✓ Clone Stamp, Healing Brush |
| **Content-Aware** | ✗ All content-aware fills | ✓ Smart Fill, Content-Aware Scale |
| **Compositing** | ✗ All layer blending | ✓ Multiple layers, Blending modes |
| **Adding Content** | ✗ All additions | ✓ Text, Shapes, Watermarks |
| **Filters** | ⚠️ Most filters | ✓ Blur, Distort, Artistic filters |
| **AI Tools** | ✗ All AI operations | ✓ AI upscaling, AI enhancement |

✓ = Level 1 allowed
✗ = Level 2 required
⚠️ = Depends on specific use

## Level 0: Unmodified

**Definition:** The original authenticated image with no edits.

**Characteristics:**
- Exact pixel data from camera sensor
- Untouched since authentication
- Highest level of trust

**Use Cases:**
- Forensic evidence
- Scientific documentation
- Maximum authenticity requirements

**How to Maintain:**
- Don't open the image in GIMP (or any editor)
- Don't run "Initialize Tracking" until you're ready to edit
- Distribute original files only

---

## Level 1: Minor Modifications

**Definition:** Routine adjustments that don't alter substantive content.

**Standard:** Compliant with photojournalism ethics codes (AP, NPPA, Reuters).

**Philosophy:** These operations adjust how the existing scene is presented, but don't change what was in the frame.

### Always Level 1

#### 1. Exposure & Tonal Adjustments

**GIMP Menu:** Colors → Brightness-Contrast, Curves, Levels, Exposure

**Allowed:**
- Brightening underexposed images
- Darkening overexposed images
- Adjusting contrast for better visibility
- Shadow/highlight recovery
- Curves adjustments for tonal range

**Rationale:** These operations correct for camera limitations or lighting conditions. They reveal what was already there, not add new content.

**Examples:**
- Lifting shadows in a backlit subject
- Recovering blown highlights in sky
- Increasing contrast for flat lighting

#### 2. Color Correction

**GIMP Menu:** Colors → Hue-Saturation, Color Balance, Color Temperature

**Allowed:**
- White balance correction
- Color temperature adjustment
- Hue shifts to correct color casts
- Saturation adjustments (within reason)
- Removing color casts from lighting

**Rationale:** Cameras don't always capture colors accurately. These operations correct for white balance errors and color casts to represent the scene as it appeared.

**Examples:**
- Correcting tungsten orange cast to neutral
- Adjusting saturation reduced by overcast conditions
- Removing green tint from fluorescent lighting

**Boundary Case:** Extreme saturation that creates unrealistic colors should be Level 2, but moderate saturation to compensate for camera limitations is Level 1.

#### 3. Cropping

**GIMP Menu:** Image → Crop to Selection

**Allowed:**
- Any amount of cropping
- Aspect ratio changes
- Straightening via crop

**Rationale:** Framing choices happen at capture time, but final framing can be adjusted in post. Cropping removes content but doesn't add or alter it.

**Examples:**
- Removing distracting elements at frame edges
- Changing from 3:2 to 4:3 aspect ratio
- Tightening composition around subject

**Note:** While cropping can significantly change composition, it's still considered routine in photojournalism.

#### 4. Rotation & Transformation

**GIMP Menu:** Image → Transform → Rotate, Flip, Arbitrary Rotation

**Allowed:**
- 90°, 180°, 270° rotations
- Horizontal/vertical flipping
- Straightening horizon (small angle rotations)
- Perspective correction (lens correction)

**Rationale:** Cameras don't always capture perfectly straight horizons. Small rotations correct for this.

**Examples:**
- Straightening a tilted horizon
- Rotating portrait orientation to landscape
- Correcting perspective distortion from wide-angle lens

**Boundary Case:** Extreme perspective correction that warps the image significantly should be Level 2.

#### 5. Sharpening

**GIMP Menu:** Filters → Enhance → Sharpen, Unsharp Mask

**Allowed:**
- Unsharp mask (moderate amounts)
- Sharpen for print or web
- Compensating for slight blur

**Rationale:** Digital images often benefit from sharpening, especially after resizing. Moderate sharpening enhances existing detail without creating new content.

**Examples:**
- Sharpening after downsizing for web
- Compensating for soft focus
- Unsharp mask at 0.5-1.5 radius

**Boundary Case:** Oversharpening that creates visible halos or artifacts should be Level 2.

#### 6. Noise Reduction

**GIMP Menu:** Filters → Enhance → Noise Reduction, Despeckle

**Allowed:**
- Removing sensor noise from high ISO
- Despeckle filters (moderate)
- Reducing grain

**Rationale:** High ISO images have noise that obscures detail. Moderate noise reduction recovers the underlying image.

**Examples:**
- Reducing chroma noise from ISO 6400 shot
- Despeckle for scanned film
- Luminance noise reduction

**Boundary Case:** Heavy smoothing that removes skin texture or fine detail should be Level 2.

#### 7. Lens Correction

**GIMP Menu:** Filters → Distortion → Lens Distortion

**Allowed:**
- Correcting barrel/pincushion distortion
- Vignette removal
- Chromatic aberration correction

**Rationale:** These are optical imperfections from the lens, not the scene. Correcting them reveals the true scene.

**Examples:**
- Removing barrel distortion from wide-angle lens
- Correcting vignetting from fast aperture
- Removing purple fringing from chromatic aberration

### Questionable Cases (Community Input Needed)

These operations might be Level 1 or Level 2 depending on extent:

#### Dust Spot Removal
- **Small dust spots (1-5 pixels):** Arguably Level 1 (sensor dust, not scene)
- **Larger spots:** Level 2 (becomes content removal)
- **Recommendation:** Currently Level 2 to be conservative

#### Graduated Filters
- **Digital graduated ND:** Level 1? (simulates physical filter)
- **Recommendation:** Currently Level 2 until validated

#### Selective Color Adjustments
- **Adjusting one color channel:** Level 1? (still color correction)
- **Recommendation:** Currently Level 2 to prevent selective manipulation

---

## Level 2: Heavy Modifications

**Definition:** Significant alterations to image content.

**Standard:** Not compliant with strict photojournalism standards, but still authenticated.

**Philosophy:** These operations add, remove, or significantly alter what was in the frame.

### Always Level 2

#### 1. Cloning & Healing

**GIMP Menu:** Clone Tool, Healing Tool, Perspective Clone

**Why Level 2:**
- Adds pixels from one part of image to another
- Can remove people, objects, or elements
- Can duplicate content

**Examples:**
- Removing a person from background
- Cloning out a power line
- Healing a blemish by copying nearby skin

**Photojournalism:** Prohibited in editorial contexts

#### 2. Content-Aware Operations

**GIMP Menu:** Filters → Enhance → Smart Remove (if available)

**Why Level 2:**
- Algorithm generates new pixels
- Not just copying existing content
- Can "invent" plausible replacements

**Examples:**
- Content-aware fill to remove object
- Smart sharpen with edge detection
- AI-powered enhancement

**Note:** Even when algorithm is conservative, it's still synthesizing content.

#### 3. Layer Compositing

**GIMP Menu:** Multiple layers with blending modes

**Why Level 2:**
- Combines multiple images or elements
- Creates content not in original capture
- Blending modes alter pixel values in complex ways

**Examples:**
- HDR merge from multiple exposures
- Focus stacking
- Adding a second sky from another image
- Overlay text or graphics

**Exceptions:** A single adjustment layer (curves, levels) on base image could be argued as Level 1, but conservatively mark as Level 2.

#### 4. Adding New Content

**GIMP Menu:** Text Tool, Shape Tools, Brushes

**Why Level 2:**
- Adds content not in original scene
- Even if just a watermark or signature

**Examples:**
- Copyright watermark
- Text overlay for infographic
- Logo placement
- Drawing or painting on image

**Rationale:** Anything added to the image that wasn't captured is Level 2.

#### 5. Selective Masking/Local Adjustments

**GIMP Menu:** Layer masks, Selection tools + adjustment

**Why Level 2:**
- Allows different adjustments to different areas
- Can selectively alter reality
- Not a global adjustment

**Examples:**
- Darkening only the sky
- Brightening only the subject's face
- Selective color (keeping one color, desaturating others)

**Rationale:** While photojournalists debate this, selective adjustments can mislead by emphasizing some areas over others.

**Note:** Some argue this should be Level 1 if adjustments themselves are minor. Conservative approach: Level 2.

#### 6. Filters with Significant Alteration

**GIMP Menu:** Filters → Blur, Distort, Artistic, Light & Shadow

**Why Level 2:**
- Significantly change appearance
- Add effects not in original scene
- Creative rather than corrective

**Examples:**
- Blur filter (except very slight)
- Lens flare addition
- Artistic filters (oil paint, cartoon, etc.)
- Distortion filters (ripple, wave, etc.)

**Exceptions:** Subtle blur for privacy (e.g., blurring a face) is still Level 2.

#### 7. AI-Powered Tools

**GIMP Menu:** Any AI plugin (G'MIC, etc.)

**Why Level 2:**
- Neural networks generate pixels
- Not deterministic from original content
- Can hallucinate details

**Examples:**
- AI upscaling
- AI noise reduction
- Style transfer
- Deepfake-style face swapping

**Rationale:** Even when results look plausible, AI tools synthesize content that wasn't in the original capture.

#### 8. Resynthesis & Reconstruction

**GIMP Menu:** Resynthesizer plugin

**Why Level 2:**
- Generates texture and patterns
- Fills in missing areas
- Not just copying existing pixels

**Examples:**
- Texture synthesis for large area removal
- Seam carving for content-aware scaling
- Reconstructing occluded areas

---

## Special Cases & Edge Cases

### Case 1: Extreme Cropping

**Question:** Is cropping 90% of the image still Level 1?

**Answer:** Yes, cropping is always Level 1 regardless of amount. Rationale: It only removes content, doesn't add or alter it.

**Note:** Some may argue this changes the story, but it's still accepted in photojournalism.

### Case 2: Dodging & Burning

**Question:** Traditional darkroom techniques - Level 1 or 2?

**Current Recommendation:** Level 2 (selective adjustment)

**Debate:** Photojournalists used dodging/burning for decades. Should it be Level 1?

**Rationale for Level 2:** Selective adjustments can mislead. Better to be conservative in digital realm.

**Community Input Needed:** This is a hot topic.

### Case 3: Panorama Stitching

**Question:** Stitching multiple captures into one image - what level?

**Current Recommendation:** Level 2 (compositing multiple captures)

**Debate:** Is this "one capture" if done in-camera? What about software stitching?

**Rationale:** Multiple frames combined = compositing = Level 2, even if of same scene.

### Case 4: HDR Merge

**Question:** Merging multiple exposures for dynamic range - Level 1 or 2?

**Current Recommendation:** Level 2 (compositing)

**Debate:** Is this revealing detail that was there, or creating new content?

**Rationale:** While HDR reveals more than single exposure, it's combining multiple captures, so Level 2.

### Case 5: Black & White Conversion

**Question:** Converting color to monochrome - Level 1 or 2?

**Current Recommendation:** Level 1 (color adjustment)

**Rationale:** Removes color information but doesn't add content. Accepted in photojournalism.

**Exception:** Creative B&W conversions with heavy channel mixing might be Level 2.

### Case 6: Sensor Dust Removal

**Question:** Clone stamp to remove sensor dust - Level 1 or 2?

**Current Recommendation:** Level 2 (cloning)

**Debate:** Sensor dust wasn't in the scene, so removing it is corrective, not manipulative.

**Rationale:** Where do we draw the line? Better to be conservative and mark cloning as Level 2.

**Alternative View:** Could argue small dust spots (1-5 pixels) are Level 1, larger spots Level 2.

### Case 7: Skin Retouching

**Question:** Smoothing skin or removing blemishes - Level 1 or 2?

**Current Recommendation:** Level 2 (healing/cloning)

**Context:**
- **News/documentary:** Level 2, prohibited in photojournalism
- **Portrait/commercial:** Level 2, but expected in that genre

**Rationale:** Changes the subject's appearance, even if subtly.

---

## Decision Framework

When unsure about an operation, ask these questions:

### Question 1: Does it add or remove content?
- **Yes:** Level 2
- **No:** Continue to Question 2

### Question 2: Does it change what was in the frame?
- **Yes:** Level 2
- **No:** Continue to Question 3

### Question 3: Would it be acceptable in photojournalism?
- **No:** Level 2
- **Yes:** Likely Level 1

### Question 4: Is the adjustment selective/local?
- **Yes:** Probably Level 2 (conservative)
- **No:** Likely Level 1

### Question 5: Does it use AI or synthesis?
- **Yes:** Level 2
- **No:** Apply other questions

### Final Check: When in doubt, choose Level 2
Better to over-classify than under-classify. Level 2 doesn't mean "bad" or "fake" - it just means "heavily modified."

---

## GIMP-Specific Mappings

This section maps common GIMP operations to modification levels.

### Colors Menu

| Operation | Level |
|-----------|-------|
| Brightness-Contrast | 1 |
| Curves | 1 |
| Levels | 1 |
| Exposure | 1 |
| Shadows-Highlights | 1 |
| Hue-Saturation | 1 |
| Color Balance | 1 |
| Color Temperature | 1 |
| Desaturate (B&W) | 1 |
| Posterize | 2 |
| Threshold | 2 |
| Color to Alpha | 2 |
| Colorize | 2 |

### Image Menu

| Operation | Level |
|-----------|-------|
| Crop to Selection | 1 |
| Rotate 90°/180°/270° | 1 |
| Flip Horizontal/Vertical | 1 |
| Scale Image | 1* |
| Canvas Size | 1 |

*Scaling up significantly may be Level 2 if it uses AI upscaling.

### Filters → Enhance

| Operation | Level |
|-----------|-------|
| Sharpen | 1 |
| Unsharp Mask | 1 |
| Noise Reduction | 1 |
| Despeckle | 1 |
| Deinterlace | 1 |
| Red Eye Removal | 2 |

### Filters → Distorts

| Operation | Level |
|-----------|-------|
| Lens Distortion | 1 |
| All others (Ripple, Wave, etc.) | 2 |

### Filters → Blur

| Operation | Level |
|-----------|-------|
| All blur operations | 2 |

**Exception:** Tiny blur (radius < 2px) for noise reduction might be Level 1.

### Tools

| Tool | Level |
|------|-------|
| Crop Tool | 1 |
| Rotate Tool | 1 |
| Flip Tool | 1 |
| Clone Tool | 2 |
| Healing Tool | 2 |
| Perspective Clone | 2 |
| Dodge/Burn | 2 |
| Smudge | 2 |
| Text Tool | 2 |
| All painting tools | 2 |

### Layers

| Operation | Level |
|-----------|-------|
| Single layer, no blending | 1 |
| Multiple layers | 2 |
| Layer masks | 2 |
| Blending modes (other than Normal) | 2 |
| Merge down (after Level 1 adjustments) | 1 |

---

## Community Validation

This classification is based on:
- Professional photojournalism standards (AP, NPPA, Reuters)
- Digital photography best practices
- Conservative interpretation for credibility

**We need community validation for:**
- Dodging & burning (currently Level 2, debate for Level 1)
- Sensor dust removal (currently Level 2, debate for Level 1 if small)
- Selective adjustments (currently Level 2, some argue Level 1 if minor)
- Panorama stitching (currently Level 2, debate if in-camera stitching)
- HDR merge (currently Level 2, debate for Level 1 as "corrective")

**Feedback channels:**
- GitHub Issues: https://github.com/Birthmark-Standard/Birthmark/issues
- Community forums (r/photojournalism, NPPA)
- Direct feedback to foundation

---

## Version History

**v1.0.0 (November 2025)**
- Initial classification based on Phase 3 plan
- Conservative approach: when uncertain, choose Level 2
- Based on photojournalism standards

**Future versions:**
- Incorporate community feedback
- Add new operations as editing software evolves
- Refine edge cases based on real-world usage

---

## Additional Resources

- **AP Photojournalism Standards:** [AP Stylebook - Photo Ethics](https://www.apstylebook.com/)
- **NPPA Code of Ethics:** [NPPA Ethics Guide](https://nppa.org/code-ethics)
- **Reuters Photo Guidelines:** [Reuters Handbook of Journalism](https://handbook.reuters.com/)
- **Birthmark Phase 3 Plan:** `docs/phase-plans/Birthmark_Phase_3_Plan_Image_Editor_Wrapper_SSA.md`

---

**Remember:** The modification level doesn't judge the quality or ethics of your edit - it simply informs viewers about what level of editing was performed. Level 2 images can still be valuable, artistic, and authentic. The system exists to provide transparency, not to restrict creativity.
