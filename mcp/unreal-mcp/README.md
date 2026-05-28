# Unreal MCP

Unreal MCP will execute controlled Unreal Engine automation for project setup, validation, and packaging.

Initial scope:

- Create generated `.uproject`, `Config`, content folders, setup script, and content manifest.
- Reference Blender import manifests for later Unreal Python import.
- Prepare and run asset ingest scripts for Blender meshes and reviewed ComfyUI references.
- Run allowlisted validation commandlets after explicit confirmation.
- Package development builds after QA gates pass.

Side effects must be explicit and logged.
