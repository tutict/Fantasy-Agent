# UE Architect Skill

当需要根据 gameplay spec 准备 Unreal Engine 工程架构时使用此 skill。

## 职责

定义 UE5 工程结构和自动化交接。

## 输入

- `GameplaySpec`
- `UnrealProjectPlan`
- 生成的 asset import manifest

## 输出

- UE 目录计划
- 必需插件
- 地图列表
- Blueprint 类列表
- Data asset 计划
- Unreal Python 或 MCP 执行步骤

## 护栏

- 默认 Blueprint-first，只有性能需要时才引入 C++。
- 将机制保持在独立 actor 或 component 中。
- 暴露可调参数，方便 playtest。
- 打包前运行 validation commandlet。
