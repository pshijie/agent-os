/**
 * ArchitectureGraph — React Flow 交互式架构图组件
 *
 * Props:
 *   nodes  - Array<{ id, label, description, position, status? }>
 *   edges  - Array<{ id, source, target, label?, animated? }>
 *   height - 画布高度（默认 500）
 *
 * 节点颜色编码：completed=green, in-progress=blue, draft=gray
 * 悬停显示 tooltip（description），点击跳转到 /docs/<id>/index
 * 整体包裹 ErrorBoundary，降级时显示静态占位文本
 */

import React, { useCallback, useState } from 'react';
import ReactFlow, {
    MiniMap,
    Controls,
    Background,
    ReactFlowProvider,
    useNodesState,
    useEdgesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

import styles from './index.module.css';

// 节点状态 → 边框颜色映射
const STATUS_COLOR = {
    completed: '#22c55e',    // 绿
    'in-progress': '#3b82f6', // 蓝
    draft: '#9ca3af',         // 灰
};

// ─────────────────────────────────────────
// 自定义节点：AgentOsNode
// ─────────────────────────────────────────
function AgentOsNode({ data }) {
    const [hovered, setHovered] = useState(false);
    const borderColor = STATUS_COLOR[data.status] || STATUS_COLOR.draft;

    return (
        <div
            className={styles.agentOsNode}
            style={{ borderColor }}
            onMouseEnter={() => setHovered(true)}
            onMouseLeave={() => setHovered(false)}
        >
            <div className={styles.nodeLabel}>{data.label}</div>

            {/* 悬停 tooltip */}
            {hovered && data.description && (
                <div className={styles.nodeTooltip}>{data.description}</div>
            )}
        </div>
    );
}

// nodeTypes 必须在组件外部定义，否则每次渲染都会触发 React Flow 重建
const NODE_TYPES = { agentOsNode: AgentOsNode };

// ─────────────────────────────────────────
// ErrorBoundary
// ─────────────────────────────────────────
class ErrorBoundary extends React.Component {
    constructor(props) {
        super(props);
        this.state = { hasError: false };
    }

    static getDerivedStateFromError() {
        return { hasError: true };
    }

    componentDidCatch(error, info) {
        // 生产环境可接入日志系统
        console.error('[ArchitectureGraph] ErrorBoundary caught:', error, info);
    }

    render() {
        if (this.state.hasError) {
            return (
                <div className={styles.errorFallback}>
                    交互式架构图加载失败，请刷新页面
                </div>
            );
        }
        return this.props.children;
    }
}

// ─────────────────────────────────────────
// 内部图表组件（需在 ReactFlowProvider 内）
// ─────────────────────────────────────────
function ArchitectureGraphInner({ rawNodes, rawEdges, onNodeClick }) {
    // 将外部 props 转换为 React Flow 格式
    const initialNodes = rawNodes.map((n) => ({
        id: n.id,
        type: 'agentOsNode',
        position: n.position || { x: 0, y: 0 },
        data: {
            label: n.label,
            description: n.description || '',
            status: n.status || 'draft',
        },
        style: {
            border: 'none',   // 边框由 CSS 类控制
            background: 'transparent',
            padding: 0,
        },
    }));

    const initialEdges = rawEdges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label || '',
        type: 'smoothstep',
        animated: e.animated || false,
        style: { stroke: '#64748b' },
        labelStyle: { fontSize: 11, fill: '#475569' },
        labelBgStyle: { fill: '#f8fafc', fillOpacity: 0.85 },
    }));

    const [nodes, , onNodesChange] = useNodesState(initialNodes);
    const [edges, , onEdgesChange] = useEdgesState(initialEdges);

    const handleNodeClick = useCallback(
        (_, node) => {
            if (onNodeClick) {
                onNodeClick(node);
            }
        },
        [onNodeClick]
    );

    return (
        <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            nodeTypes={NODE_TYPES}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            attributionPosition="bottom-right"
        >
            <MiniMap
                nodeStrokeColor={(n) =>
                    STATUS_COLOR[n.data?.status] || STATUS_COLOR.draft
                }
                nodeColor={(n) => STATUS_COLOR[n.data?.status] || STATUS_COLOR.draft}
                nodeStrokeWidth={2}
                zoomable
                pannable
            />
            <Controls />
            <Background color="#e2e8f0" gap={16} />
        </ReactFlow>
    );
}

// ─────────────────────────────────────────
// 默认导出：ArchitectureGraph
// ─────────────────────────────────────────
export default function ArchitectureGraph({ nodes = [], edges = [], height = 500 }) {
    const handleNodeClick = useCallback((node) => {
        window.location.href = `/docs/${node.id}/index`;
    }, []);

    return (
        <ErrorBoundary>
            <div className={styles.graphContainer} style={{ height }}>
                <ReactFlowProvider>
                    <ArchitectureGraphInner
                        rawNodes={nodes}
                        rawEdges={edges}
                        onNodeClick={handleNodeClick}
                    />
                </ReactFlowProvider>
            </div>
        </ErrorBoundary>
    );
}
