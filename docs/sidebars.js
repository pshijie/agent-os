// @ts-check

/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
    tutorialSidebar: [
        {
            type: 'doc',
            id: 'intro',
            label: 'Agent OS 全景',
        },
        {
            type: 'category',
            label: '01 · 记忆系统',
            collapsed: false,
            items: [
                'memory/index',
                'memory/working',
                'memory/episodic',
                'memory/semantic',
                'memory/perceptual',
            ],
        },
        {
            type: 'category',
            label: '02 · 感知与输入',
            collapsed: true,
            items: [
                'perception/index',
            ],
        },
        {
            type: 'category',
            label: '03 · 规划与推理',
            collapsed: true,
            items: [
                'planning/index',
                'planning/react',
                'planning/plan-and-solve',
                'planning/reflection',
            ],
        },
        {
            type: 'category',
            label: '04 · 工具执行层',
            collapsed: true,
            items: [
                'action-tools/index',
                'action-tools/tool-design',
                'action-tools/tool-executor',
            ],
        },
        {
            type: 'category',
            label: '05 · RAG 检索增强',
            collapsed: true,
            items: [
                'rag/index',
                'rag/pipeline',
                'rag/knowledge-base',
            ],
        },
        {
            type: 'category',
            label: '06 · 上下文工程',
            collapsed: true,
            items: [
                'context-engineering/index',
                'context-engineering/gssc-pipeline',
                'context-engineering/compression',
            ],
        },
        {
            type: 'category',
            label: '07 · 成本与资源治理',
            collapsed: true,
            items: [
                'cost-governance/index',
                'cost-governance/token-budget',
                'cost-governance/monitoring',
            ],
        },
        {
            type: 'category',
            label: '08 · 通信协议',
            collapsed: true,
            items: [
                'protocols/index',
                'protocols/mcp',
                'protocols/a2a',
            ],
        },
        {
            type: 'category',
            label: '09 · 评估体系',
            collapsed: true,
            items: [
                'evaluation/index',
                'evaluation/metrics',
            ],
        },
        {
            type: 'category',
            label: '10 · 多智能体协作',
            collapsed: true,
            items: [
                'multi-agent/index',
                'multi-agent/orchestration',
                'multi-agent/collaboration',
            ],
        },
    ],
};

module.exports = sidebars;
