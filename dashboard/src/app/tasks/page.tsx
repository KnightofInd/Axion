"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

import { DashboardShell } from "@/components/DashboardShell";
import { SectionCard } from "@/components/SectionCard";
import { useAxionEmail } from "@/hooks/useAxionEmail";
import { createTask, deleteTask, listTasks, updateTaskStatus } from "@/lib/api";
import { formatDateTime, toIsoOrNull } from "@/lib/format";
import type { AxionTask, TaskStatus } from "@/lib/types";

export default function TasksPage() {
  const { email, saveEmail } = useAxionEmail();
  const [tasks, setTasks] = useState<AxionTask[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState(3);
  const [dueAt, setDueAt] = useState("");

  const loadTasks = useCallback(async () => {
    if (!email) {
      setTasks([]);
      return;
    }

    setLoading(true);
    setError("");
    try {
      const data = await listTasks(email);
      setTasks(data.tasks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load tasks");
      setTasks([]);
    } finally {
      setLoading(false);
    }
  }, [email]);

  useEffect(() => {
    void loadTasks();
  }, [loadTasks]);

  const onCreate = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!email) {
      setError("Set an email first.");
      return;
    }

    if (!title.trim()) {
      setError("Task title is required.");
      return;
    }

    setError("");
    try {
      await createTask({
        email,
        title: title.trim(),
        description: description.trim() || null,
        priority,
        due_at: toIsoOrNull(dueAt),
      });
      setTitle("");
      setDescription("");
      setDueAt("");
      await loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create task");
    }
  };

  const onStatusChange = async (taskId: string, status: TaskStatus) => {
    if (!email) {
      return;
    }
    try {
      await updateTaskStatus(taskId, email, status);
      await loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update task");
    }
  };

  const onDelete = async (taskId: string) => {
    if (!email) {
      return;
    }
    try {
      await deleteTask(taskId, email);
      await loadTasks();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete task");
    }
  };

  return (
    <DashboardShell
      email={email}
      onEmailSave={saveEmail}
      title="Tasks"
      subtitle="Create, prioritize, and close out tasks from one queue"
      actions={
        <button
          type="button"
          onClick={loadTasks}
          className="rounded-lg border border-axion-border bg-white/5 px-3 py-2 text-sm text-axion-fg hover:bg-white/10"
        >
          Refresh
        </button>
      }
    >
      {error ? <p className="rounded-xl border border-rose-400/40 bg-rose-500/10 p-3 text-sm text-rose-200">{error}</p> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        <SectionCard title="New Task" subtitle="Add a manual task into AXION scoring">
          <form className="space-y-2" onSubmit={onCreate}>
            <input
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Task title"
              className="w-full rounded-lg border border-axion-border bg-slate-950/80 px-3 py-2 text-sm"
            />
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="Description"
              rows={3}
              className="w-full rounded-lg border border-axion-border bg-slate-950/80 px-3 py-2 text-sm"
            />
            <div className="grid grid-cols-2 gap-2">
              <select
                value={priority}
                onChange={(event) => setPriority(Number(event.target.value))}
                className="rounded-lg border border-axion-border bg-slate-950/80 px-3 py-2 text-sm"
              >
                <option value={1}>Priority 1</option>
                <option value={2}>Priority 2</option>
                <option value={3}>Priority 3</option>
                <option value={4}>Priority 4</option>
                <option value={5}>Priority 5</option>
              </select>
              <input
                type="datetime-local"
                value={dueAt}
                onChange={(event) => setDueAt(event.target.value)}
                className="rounded-lg border border-axion-border bg-slate-950/80 px-3 py-2 text-sm"
              />
            </div>
            <button
              type="submit"
              className="rounded-lg bg-axion-accent px-3 py-2 text-sm font-semibold text-slate-950 hover:brightness-105"
            >
              Create Task
            </button>
          </form>
        </SectionCard>

        <SectionCard title="Task Queue" subtitle={loading ? "Loading..." : `${tasks.length} tasks`}> 
          <ul className="space-y-2">
            {tasks.length === 0 && !loading ? <li className="text-sm text-axion-muted">No tasks yet.</li> : null}
            {tasks.map((task) => (
              <li key={task.id} className="rounded-lg border border-axion-border bg-black/20 p-3">
                <p className="font-medium text-white">{task.title}</p>
                <p className="text-xs text-axion-muted">
                  P{task.priority} | {task.source} | Score {task.computed_score ?? "-"}
                </p>
                <p className="mt-1 text-xs text-axion-muted">Due {formatDateTime(task.due_at)}</p>
                <div className="mt-2 flex items-center gap-2">
                  <select
                    value={task.status}
                    onChange={(event) => onStatusChange(task.id, event.target.value as TaskStatus)}
                    className="rounded-md border border-axion-border bg-slate-950/80 px-2 py-1 text-xs"
                  >
                    <option value="pending">pending</option>
                    <option value="in_progress">in_progress</option>
                    <option value="done">done</option>
                  </select>
                  <button
                    type="button"
                    onClick={() => onDelete(task.id)}
                    className="rounded-md border border-rose-400/40 bg-rose-500/10 px-2 py-1 text-xs text-rose-200"
                  >
                    Delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        </SectionCard>
      </div>
    </DashboardShell>
  );
}
