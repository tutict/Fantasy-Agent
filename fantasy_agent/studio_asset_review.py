"""Content-bound user reviews shared by external jobs and engine ingest.

The immutable plan stays unchanged. The established approval manifest and
resource pipeline are projections of durable user decisions, so grants still
refer to the exact plan version the user approved.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from fantasy_agent.approval_manifest import load_asset_approval_manifest
from fantasy_agent.artifact_identity import compute_artifact_identity
from fantasy_agent.atomic_write import write_atomic
from fantasy_agent.contracts import (
    ArtifactIdentity,
    AssetApprovalDecision,
    AssetApprovalManifest,
    CreativeReviewItem,
    CreativeReviewReport,
    DirectorBuildPlan,
)
from fantasy_agent.path_safety import resolve_workspace_path
from fantasy_agent.production_spec_runtime import sync_bundle_with_approval_manifest
from fantasy_agent.studio_projects import ProjectResource, ProjectSnapshot, StudioProjectStore


class ProjectAssetReview:
    def __init__(self, projects: StudioProjectStore) -> None:
        self.projects = projects

    @staticmethod
    def active_assets(snapshot: ProjectSnapshot, version: int) -> list[ProjectResource]:
        # Keep old references, but gate the most recently registered content
        # for a logical asset. Older records without a key retain path identity.
        by_path = {}
        for resource in snapshot.resources:
            if resource.plan_version == version and resource.kind == "asset":
                by_path[resource.asset_key or resource.path] = resource
        return list(by_path.values())

    def path(self, project_id: str, version: int, resource: ProjectResource) -> Path:
        project_root = self.projects.production_workspace(project_id)
        path = resolve_workspace_path(resource.path, workspace_root=project_root)
        resolve_workspace_path(
            str(path), workspace_root=project_root / "versions" / f"v{version}", allow_absolute=True
        )
        if not path.is_file() or compute_artifact_identity(path).digest != resource.sha256:
            raise ValueError("资产版本已变化，请重新生成并审阅当前产物。")
        return path

    @staticmethod
    def decision(snapshot: ProjectSnapshot, resource: ProjectResource) -> str:
        matching = [
            item
            for item in snapshot.decisions.values()
            if item.get("kind") == "asset_review"
            and item.get("plan_version") == resource.plan_version
            and any(
                subject.get("resource_id") == resource.resource_id
                and subject.get("sha256") == resource.sha256
                for subject in item.get("subjects", [])
            )
        ]
        return matching[-1]["status"] if matching else "pending_user_review"

    def require_approved(
        self,
        project_id: str,
        version: int,
        resource_ids: list[str] | None = None,
    ) -> list[ProjectResource]:
        snapshot = self.projects.snapshot(project_id, plan_version=version)
        if snapshot is None:
            raise ValueError("项目版本不存在。")
        resources = self.active_assets(snapshot, version)
        if resource_ids is not None:
            requested = set(resource_ids)
            resources = [item for item in resources if item.resource_id in requested]
            if not requested or {item.resource_id for item in resources} != requested:
                raise ValueError("请选择本版本实际生成的资产。")
        for resource in resources:
            self.path(project_id, version, resource)
            if self.decision(snapshot, resource) != "approved":
                raise ValueError("生成资产必须先由用户审阅，才能进入引擎导入。")
        return resources

    def write_manifest(self, project_id: str, version: int) -> AssetApprovalManifest:
        snapshot = self.projects.snapshot(project_id, plan_version=version)
        if snapshot is None or snapshot.plan is None:
            raise ValueError("项目版本尚未保存计划。")
        root = self.projects.production_workspace(project_id) / "versions" / f"v{version}"
        decisions = []
        for resource in self.active_assets(snapshot, version):
            path = self.path(project_id, version, resource)
            source = "blender" if path.suffix.lower() in {".glb", ".fbx", ".blend"} else "comfyui"
            item = next(
                (
                    item
                    for item in snapshot.plan.creative_review.items
                    if item.source == source
                    and Path(item.asset_path).stem.casefold() == path.stem.casefold()
                ),
                None,
            )
            decisions.append(
                AssetApprovalDecision(
                    asset_id=item.asset_id if item else resource.resource_id,
                    source=source,
                    asset_path=path.relative_to(root).as_posix(),
                    gameplay_role=item.gameplay_role if item else path.stem,
                    artifact_identity=ArtifactIdentity(digest=resource.sha256),
                    decision=self.decision(snapshot, resource),
                    risks=[] if item else ["素材尚无策划资产映射；导入前确认其玩法用途。"],
                )
            )
        manifest = AssetApprovalManifest(
            decisions=decisions,
            approved_asset_ids=[item.asset_id for item in decisions if item.decision == "approved"],
            rejected_asset_ids=[item.asset_id for item in decisions if item.decision == "rejected"],
            revision_asset_ids=[
                item.asset_id for item in decisions if item.decision == "needs_revision"
            ],
            pending_asset_ids=[
                item.asset_id for item in decisions if item.decision == "pending_user_review"
            ],
        )
        write_atomic(
            root / "generated/asset-approval-manifest.yaml",
            yaml.safe_dump(manifest.model_dump(mode="json"), allow_unicode=True, sort_keys=False),
        )
        return manifest

    def effective_plan(self, project_id: str, version: int) -> DirectorBuildPlan:
        snapshot = self.projects.snapshot(project_id, plan_version=version)
        if snapshot is None or snapshot.plan is None:
            raise ValueError("项目版本尚未保存计划。")
        plan = snapshot.plan.model_copy(deep=True)
        root = self.projects.production_workspace(project_id) / "versions" / f"v{version}"
        try:
            manifest = load_asset_approval_manifest(workspace_root=root)
        except FileNotFoundError:
            return plan
        if plan.production_spec_bundle is not None:
            plan.production_spec_bundle = sync_bundle_with_approval_manifest(
                plan.production_spec_bundle, manifest
            )
        return plan

    def review_report(self, snapshot: ProjectSnapshot) -> CreativeReviewReport | None:
        if snapshot.plan is None:
            return None
        report = snapshot.plan.creative_review.model_copy(deep=True)
        resources = self.active_assets(snapshot, snapshot.plan_version)
        if not resources:
            return report
        items = []
        for resource in resources:
            path = Path(resource.path)
            source = "blender" if path.suffix.lower() in {".glb", ".fbx", ".blend"} else "comfyui"
            planned = next(
                (
                    item
                    for item in report.items
                    if item.source == source
                    and Path(item.asset_path).stem.casefold() == path.stem.casefold()
                ),
                None,
            )
            status = self.decision(snapshot, resource)
            risks = list(planned.risks) if planned else ["确认素材在可玩循环中的用途。"]
            try:
                self.path(snapshot.project_id, snapshot.plan_version, resource)
            except (ValueError, OSError):
                status = "needs_revision"
                risks.append("文件已变化或不可读取，原审阅不能用于当前内容。")
            items.append(
                CreativeReviewItem(
                    asset_id=planned.asset_id if planned else resource.resource_id,
                    resource_id=resource.resource_id,
                    content_sha256=resource.sha256,
                    source=source,
                    asset_path=resource.path,
                    gameplay_role=planned.gameplay_role if planned else path.stem,
                    intended_use=planned.intended_use if planned else "用于当前项目的玩法验证。",
                    review_dimensions=planned.review_dimensions
                    if planned
                    else ["gameplay_readability"],
                    approval_status=status,
                    user_prompt=planned.user_prompt
                    if planned
                    else "是否符合本项目的玩法与美术方向？",
                    risks=risks,
                )
            )
        report.items = items
        report.approved_asset_ids = [
            item.asset_id for item in items if item.approval_status == "approved"
        ]
        report.revision_asset_ids = [
            item.asset_id for item in items if item.approval_status == "needs_revision"
        ]
        report.rejected_asset_ids = [
            item.asset_id for item in items if item.approval_status == "rejected"
        ]
        report.required_user_decisions = [
            item.asset_id for item in items if item.approval_status == "pending_user_review"
        ]
        return report
