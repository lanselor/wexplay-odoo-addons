# Filerobot Image Editor 4.8.1
Source: https://scaleflex.cloudimg.io/v7/plugins/filerobot-image-editor/4.8.1/filerobot-image-editor.min.js
Upstream: https://github.com/scaleflex/filerobot-image-editor/tree/v4.8.1
License: MIT (see LICENSE). Bundled React/Konva dependencies included by upstream.
Local modification: restrict TABS_TOOLS Adjust to Crop and Annotate to Pen.
The two tool-list replacements are documented above.
Additional local adaptation: PenOptions keeps its original useAnnotation and pointer handlers,
but replaces the AnnotationOptions view with a stable wexPenControls component.
Native color/range inputs call the existing immediate annotation updater. Opacity is fixed
at 1 and shadows disabled. A stable component identity preserves range dragging across renders.
The exact guarded patch is reproducible with pen_controls_patch.py, applied AFTER the tool-list restrictions.
The library engine, crop, undo/redo and pointer handling are otherwise unchanged.
Backend translations and cloud processing are disabled by the integration.

Crop preview adaptation: crop_overlay_patch.py replaces only the blurred original-image overlay in CropTransformer with an opaque Rect using the theme bg-secondary color. The existing destination-out crop window remains unchanged. Crop geometry, original file, export and undo/redo are unchanged. Apply once to pinned bundle; independent of pen_controls_patch.py.
