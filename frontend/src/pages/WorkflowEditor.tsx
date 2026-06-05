import { useEffect, useState } from 'react';
import { workflowsApi } from '../services/api';
import type { Workflow, WorkflowNode } from '../types/index';

export default function WorkflowEditor() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<Workflow | null>(null);
  const [nodes, setNodes] = useState<WorkflowNode[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadWorkflows() {
    try {
      const response = await workflowsApi.getAll();
      setWorkflows(response.data);
      if (response.data.length > 0) {
        setSelectedWorkflow(response.data[0]);
      }
    } catch (error) {
      console.error('Failed to load workflows:', error);
    } finally {
      setLoading(false);
    }
  }

  async function loadNodes(workflowId: number) {
    try {
      const response = await workflowsApi.getNodes(workflowId);
      setNodes(response.data);
    } catch (error) {
      console.error('Failed to load nodes:', error);
    }
  }

  useEffect(() => {
    void loadWorkflows();
  }, []);

  useEffect(() => {
    if (selectedWorkflow) {
      void loadNodes(selectedWorkflow.id);
    }
  }, [selectedWorkflow]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success':
        return 'border-tertiary/50 glow-border';
      case 'running':
        return 'border-primary-container/50 glow-border';
      case 'failed':
        return 'border-error/50 border-2 ring-4 ring-error/10';
      default:
        return 'border-white/5 opacity-40';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'success':
        return 'check_circle';
      case 'running':
        return 'hourglass_empty';
      case 'failed':
        return 'error';
      default:
        return 'pending';
    }
  };

  if (loading) {
    return (
      <div className="p-6 flex items-center justify-center h-full">
        <div className="text-cyan-400">Loading...</div>
      </div>
    );
  }

  return (
    <div className="h-[calc(100vh-3.5rem)] flex flex-col">
      {/* Top Content Row: 3-column Layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Column: Templates */}
        <section className="w-72 border-r border-white/10 bg-surface-container-low flex flex-col">
          <div className="p-4 border-b border-white/10 bg-surface-container flex items-center justify-between">
            <span className="font-label-caps text-on-surface-variant uppercase">Workflows</span>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1">
            {workflows.map((workflow) => (
              <div
                key={workflow.id}
                onClick={() => setSelectedWorkflow(workflow)}
                className={`p-3 rounded-lg cursor-pointer transition-colors ${
                  selectedWorkflow?.id === workflow.id
                    ? 'bg-primary-container/10 border border-primary-container/30'
                    : 'hover:bg-white/5 border border-transparent'
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span
                    className={`font-bold text-sm ${
                      selectedWorkflow?.id === workflow.id ? 'text-primary' : 'text-on-surface'
                    }`}
                  >
                    {workflow.name}
                  </span>
                  <span className="text-[10px] text-on-surface-variant">{workflow.template_type}</span>
                </div>
                <p className="text-[11px] text-on-surface-variant leading-tight">{workflow.description}</p>
              </div>
            ))}
          </div>
        </section>

        {/* Middle Column: DAG Canvas */}
        <section className="flex-1 bg-surface-dim relative overflow-hidden flex flex-col" style={{ backgroundImage: 'radial-gradient(rgba(0, 102, 255, 0.1) 1px, transparent 0)', backgroundSize: '24px 24px' }}>
          <div className="p-4 border-b border-white/5 flex items-center justify-between bg-surface-dim/80 backdrop-blur">
            <div className="flex items-center gap-4">
              <h2 className="font-headline-md text-on-surface">
                Workflow DAG{' '}
                <span className="text-on-surface-variant font-normal text-sm ml-2">
                  / {selectedWorkflow?.name}
                </span>
              </h2>
            </div>
            <div className="flex items-center gap-2">
              <button className="bg-surface-container-high px-3 py-1.5 rounded text-xs flex items-center gap-2 border border-white/10 hover:bg-white/10 transition-colors">
                <span className="material-symbols-outlined text-sm">play_arrow</span> Resume
              </button>
              <button className="bg-surface-container-high px-3 py-1.5 rounded text-xs flex items-center gap-2 border border-white/10 hover:bg-white/10 transition-colors">
                <span className="material-symbols-outlined text-sm">settings_backup_restore</span> Re-run
              </button>
            </div>
          </div>

          {/* DAG Visual Area */}
          <div className="flex-1 p-12 overflow-auto">
            <div className="flex flex-col items-center gap-12">
              {nodes.map((node) => (
                <div key={node.id} className="flex items-center gap-20">
                  <div
                    className={`w-48 p-4 bg-surface-container border rounded-lg shadow-lg relative ${getStatusColor(
                      node.status
                    )}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      {node.status === 'running' ? (
                        <div className="flex gap-1">
                          <div className="w-2 h-2 rounded-full bg-primary-container animate-pulse"></div>
                          <span className="text-[9px] text-primary uppercase font-bold">Running</span>
                        </div>
                      ) : (
                        <span
                          className={`material-symbols-outlined ${
                            node.status === 'success'
                              ? 'text-tertiary'
                              : node.status === 'failed'
                              ? 'text-error'
                              : 'text-outline'
                          }`}
                        >
                          {getStatusIcon(node.status)}
                        </span>
                      )}
                      <span className="text-[10px] font-data-mono text-on-surface-variant">
                        ID: {node.id}
                      </span>
                    </div>
                    <div className="text-sm font-bold text-white mb-1">{node.node_name}</div>
                    <div className="w-full bg-surface-dim h-1 rounded overflow-hidden">
                      <div
                        className={`h-full ${
                          node.status === 'success'
                            ? 'bg-tertiary'
                            : node.status === 'running'
                            ? 'bg-primary-container'
                            : node.status === 'failed'
                            ? 'bg-error opacity-50'
                            : 'bg-outline'
                        }`}
                        style={{ width: `${node.progress}%` }}
                      ></div>
                    </div>
                    {node.error_message && (
                      <div className="mt-2 text-[10px] text-error">{node.error_message}</div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </section>

        {/* Right Column: Parameter Panel */}
        <section className="w-80 border-l border-white/10 bg-surface-container-low flex flex-col">
          <div className="p-4 border-b border-white/10 bg-surface-container">
            <span className="font-label-caps text-on-surface-variant uppercase">Node Parameters</span>
          </div>
          <div className="p-4 overflow-y-auto space-y-6">
            {nodes.length > 0 && (
              <>
                <div>
                  <label className="block text-[10px] text-on-surface-variant uppercase font-bold mb-2">
                    Selected Node
                  </label>
                  <div className="bg-surface-container-high p-3 rounded border border-white/5">
                    <div className="text-white font-bold text-sm">{nodes[0].node_name}</div>
                    <div className="text-[10px] text-cyan-400 font-data-mono">
                      Status: {nodes[0].status}
                    </div>
                  </div>
                </div>
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-[10px] text-on-surface-variant uppercase font-bold mb-1">
                        CPU Cores
                      </label>
                      <input
                        className="w-full bg-surface-container-highest border-white/10 text-white text-xs rounded p-2 focus:ring-1 focus:ring-cyan-500 outline-none"
                        type="number"
                        value={nodes[0].cpu_cores}
                        readOnly
                      />
                    </div>
                    <div>
                      <label className="block text-[10px] text-on-surface-variant uppercase font-bold mb-1">
                        Memory (GB)
                      </label>
                      <input
                        className="w-full bg-surface-container-highest border-white/10 text-white text-xs rounded p-2 focus:ring-1 focus:ring-cyan-500 outline-none"
                        type="number"
                        value={nodes[0].memory_gb}
                        readOnly
                      />
                    </div>
                  </div>
                </div>
              </>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
