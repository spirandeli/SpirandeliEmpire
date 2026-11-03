"""
SpirandeliEmpire OS - Safe Business Provisioner
Creates isolated directory trees, configuration manifests and volumes
for newly approved digital businesses without running arbitrary shell commands.
"""
import os
import json
import logging

logger = logging.getLogger("Provisioner")

BASE_STORAGE = os.getenv("STORAGE_BASE", "storage/businesses")

def provision_business(business_slug: str, template_config: dict) -> str:
    """
    Provisions a completely isolated workspace for a new business.
    """
    target_dir = os.path.join(BASE_STORAGE, business_slug)
    os.makedirs(target_dir, exist_ok=True)

    subdirs = ["content", "data", "logs", "backups", "assets"]
    for sub in subdirs:
        os.makedirs(os.path.join(target_dir, sub), exist_ok=True)

    # Save business manifest
    manifest_path = os.path.join(target_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(template_config, f, indent=2, ensure_ascii=False)

    logger.info(f"Isolated business storage provisioned at: {target_dir}")
    return target_dir

