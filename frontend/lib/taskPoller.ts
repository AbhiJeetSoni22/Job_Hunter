/**
 * lib/taskPoller.ts — Reusable polling coordinator for PostgreSQL background tasks.
 *
 * Handles:
 * - Interval-based polling with configurable frequency and timeout.
 * - Safe terminal state handling (succeeded, failed, cancelled).
 * - Stale token fencing (prevents out-of-order or superseded task updates).
 * - Transient polling error tolerance (network glitches do not falsely fail tasks).
 * - Clean teardown and timer cleanup on unmount or cancellation.
 */

import type { TaskResponse } from "./types";

export interface TaskPollerCallbacks {
  onSuccess: (task: TaskResponse) => void | Promise<void>;
  onError: (errorMessage: string) => void | Promise<void>;
  onCancelled?: (task: TaskResponse) => void | Promise<void>;
  onTimeout?: () => void | Promise<void>;
}

export interface TaskPollerConfig {
  intervalMs?: number;
  timeoutMs?: number;
}

export class TaskPoller {
  private timerId: ReturnType<typeof setInterval> | null = null;
  private timeoutId: ReturnType<typeof setTimeout> | null = null;
  private currentToken = 0;
  private isRunning = false;
  private fetchTask: (taskId: string) => Promise<TaskResponse>;
  private getCallbacks: () => TaskPollerCallbacks;
  private intervalMs: number;
  private timeoutMs: number;

  constructor(
    fetchTask: (taskId: string) => Promise<TaskResponse>,
    callbacks: TaskPollerCallbacks | (() => TaskPollerCallbacks),
    config?: TaskPollerConfig,
  ) {
    this.fetchTask = fetchTask;
    this.getCallbacks = typeof callbacks === "function" ? callbacks : () => callbacks;
    this.intervalMs = config?.intervalMs ?? 2000;
    this.timeoutMs = config?.timeoutMs ?? 120000;
  }

  get active(): boolean {
    return this.isRunning;
  }

  stop(): void {
    this.currentToken++;
    this.isRunning = false;
    if (this.timerId !== null) {
      clearInterval(this.timerId);
      this.timerId = null;
    }
    if (this.timeoutId !== null) {
      clearTimeout(this.timeoutId);
      this.timeoutId = null;
    }
  }

  start(taskId: string): void {
    this.stop();
    const token = this.currentToken;
    this.isRunning = true;

    const check = async (): Promise<void> => {
      if (!this.isRunning || this.currentToken !== token) return;
      try {
        const task = await this.fetchTask(taskId);
        if (!this.isRunning || this.currentToken !== token) return;

        const callbacks = this.getCallbacks();

        if (task.status === "succeeded") {
          this.stop();
          await callbacks.onSuccess(task);
        } else if (task.status === "failed") {
          this.stop();
          const msg = task.error_message || "Background task failed.";
          await callbacks.onError(msg);
        } else if (task.status === "cancelled") {
          this.stop();
          if (callbacks.onCancelled) {
            await callbacks.onCancelled(task);
          } else {
            await callbacks.onError("Background task was cancelled.");
          }
        }
        // "queued" and "running" keep polling
      } catch {
        // Transient fetch or network error — ignore and retry on next tick
      }
    };

    this.timerId = setInterval(check, this.intervalMs);

    this.timeoutId = setTimeout(async () => {
      if (!this.isRunning || this.currentToken !== token) return;
      this.stop();
      const callbacks = this.getCallbacks();
      if (callbacks.onTimeout) {
        await callbacks.onTimeout();
      }
    }, this.timeoutMs);

    // Initial check right away
    void check();
  }
}
