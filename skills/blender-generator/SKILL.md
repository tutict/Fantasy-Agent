# Blender Generator Skill

当需要通过 Blender Python 或 Blender MCP 准备程序化资产时使用此 skill。

## 职责

生成玩法可读的灰盒和模块化资产。

## 输入

- `GameplaySpec`
- `BlenderAssetPlan`

## 输出

- Blender Python job manifest
- 用于 Blender 执行的 `.py` 脚本
- FBX 或 GLB 导出
- Unreal import manifest

## 工作流

1. 生成比例正确的基础几何体。
2. 根据玩法角色命名。
3. 生成模块化墙体、门、坡道、危险标记、目标道具、出口门和 UI proxy mesh。
4. 分配 collection、材质色块、origin 和 `UCX_` 碰撞名称。
5. 导出到 `generated/assets/`。
6. 产出 Unreal import manifest。
7. 只有在确认执行后，才把生成脚本交给 Blender MCP。

## 护栏

- 核心循环跑通前，不把程序化精力花在装饰细节上。
- 不把资产导出到 generated asset 目录之外。
- 保持 mesh 模块化，方便替换。
- 不从规划工具自动启动 Blender。
