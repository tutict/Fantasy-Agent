# GDD Writer Skill

当需要把已验证的 gameplay spec 转换为结构化 Markdown 游戏设计文档时使用此 skill。

## 职责

编写面向构建的 GDD，并保持玩法合约不变。

## 输入

- `GameplaySpec`
- 已知假设或约束

## 输出

- `GDDDocument`
- `generated/gdd.md`

## 章节

- 摘要
- 玩家幻想
- 设计支柱
- 核心动词
- 核心循环
- 系统
- 进程
- 胜利和失败状态
- 关卡节奏
- 资产需求
- Unreal 说明
- Blender 说明
- QA 重点

## 护栏

- 不添加 spec 不支持的机制。
- 不把美术方向当作玩法已经成立的证据。
- 保持需求可由小型原型团队实现。
