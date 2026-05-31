from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeCandidate:
    title: str
    problem: str
    novelty: str
    required_evidence: tuple[str, ...]
    related_deliverable: str


def patent_candidates() -> list[KnowledgeCandidate]:
    return [
        KnowledgeCandidate("面向阶段条件的多域设备时序基础模型输入编码方法", "同一传感器在不同炉体阶段语义不同。", "联合编码阶段 token、传感器 token、物理域 token 与不规则时间。", ("模拟数据消融", "真实数据线性探针", "跨阶段预测误差"), "model-io-definition"),
        KnowledgeCandidate("基于退化先兆注入的设备时序基础模型评测数据生成方法", "故障样本稀缺导致模型路线难决策。", "用可解释退化模式生成早期标签、风险代理和多任务监督。", ("退化曲线", "提前量统计", "benchmark 稳定性"), "data-simulation-scenario"),
        KnowledgeCandidate("面向阶段切换工况的多头时序模型微调与路由决策方法", "难以判断开源模型应引用、微调还是自训。", "以多头指标和 IO 覆盖率驱动 Go/No-Go。", ("开源矩阵", "baseline 对比", "路线记录"), "model-route-decision"),
    ]
