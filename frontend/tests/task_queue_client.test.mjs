import test from "node:test";
import assert from "node:assert/strict";

import {
  enqueueScraper,
  getTask,
  listTasks,
  cancelTask,
} from "../lib/api.ts";
import { TaskPoller } from "../lib/taskPoller.ts";

/**
 * Helper to mock globalThis.fetch for api.ts tests.
 */
function createMockFetch(resolver) {
  return async (url, init) => {
    const result = await resolver(String(url), init || {});
    return {
      ok: result.ok !== false,
      status: result.status || 200,
      headers: new Headers({ "content-type": "application/json" }),
      json: async () => result.body,
      text: async () => JSON.stringify(result.body),
    };
  };
}

// ── 1. Real API Client Methods Tests ──────────────────────────────────────────

test("enqueueScraper() calls /api/scraper/enqueue with POST and returns task", async () => {
  const originalFetch = globalThis.fetch;
  let recordedUrl = null;
  let recordedInit = null;

  try {
    globalThis.fetch = createMockFetch((url, init) => {
      recordedUrl = url;
      recordedInit = init;
      return {
        body: {
          data: {
            id: "task-100",
            task_type: "scrape",
            status: "queued",
            user_id: "user-1",
            idempotency_key: "scrape:user-1",
            attempt_count: 0,
            max_attempts: 3,
            created_at: new Date().toISOString(),
            started_at: null,
            completed_at: null,
            result: null,
            error_message: null,
          },
          error: null,
        },
      };
    });

    const task = await enqueueScraper();
    assert.ok(recordedUrl.endsWith("/api/scraper/enqueue"));
    assert.equal(recordedInit.method, "POST");
    assert.equal(task.id, "task-100");
    assert.equal(task.status, "queued");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("getTask() requests /api/tasks/{taskId} and returns task details", async () => {
  const originalFetch = globalThis.fetch;
  let recordedUrl = null;

  try {
    globalThis.fetch = createMockFetch((url) => {
      recordedUrl = url;
      return {
        body: {
          data: {
            id: "task-200",
            task_type: "scrape",
            status: "running",
            user_id: "user-1",
            idempotency_key: null,
            attempt_count: 1,
            max_attempts: 3,
            created_at: new Date().toISOString(),
            started_at: new Date().toISOString(),
            completed_at: null,
            result: null,
            error_message: null,
          },
          error: null,
        },
      };
    });

    const task = await getTask("task-200");
    assert.ok(recordedUrl.endsWith("/api/tasks/task-200"));
    assert.equal(task.id, "task-200");
    assert.equal(task.status, "running");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("listTasks() serializes query parameters correctly", async () => {
  const originalFetch = globalThis.fetch;
  const recordedUrls = [];

  try {
    globalThis.fetch = createMockFetch((url) => {
      recordedUrls.push(url);
      return { body: { data: [], error: null } };
    });

    await listTasks();
    assert.ok(recordedUrls[0].endsWith("/api/tasks"));

    await listTasks({ task_type: "scrape" });
    assert.ok(recordedUrls[1].endsWith("/api/tasks?task_type=scrape"));

    await listTasks({ status: "queued", limit: 15 });
    assert.ok(recordedUrls[2].endsWith("/api/tasks?status=queued&limit=15"));

    await listTasks({ task_type: "bulk_score", status: "succeeded", limit: 5 });
    assert.ok(recordedUrls[3].endsWith("/api/tasks?task_type=bulk_score&status=succeeded&limit=5"));
  } finally {
    globalThis.fetch = originalFetch;
  }
});

test("cancelTask() calls /api/tasks/{taskId}/cancel with POST", async () => {
  const originalFetch = globalThis.fetch;
  let recordedUrl = null;
  let recordedInit = null;

  try {
    globalThis.fetch = createMockFetch((url, init) => {
      recordedUrl = url;
      recordedInit = init;
      return {
        body: {
          data: {
            id: "task-300",
            task_type: "scrape",
            status: "cancelled",
            user_id: "user-1",
            idempotency_key: null,
            attempt_count: 0,
            max_attempts: 3,
            created_at: new Date().toISOString(),
            started_at: null,
            completed_at: new Date().toISOString(),
            result: null,
            error_message: null,
          },
          error: null,
        },
      };
    });

    const task = await cancelTask("task-300");
    assert.ok(recordedUrl.endsWith("/api/tasks/task-300/cancel"));
    assert.equal(recordedInit.method, "POST");
    assert.equal(task.status, "cancelled");
  } finally {
    globalThis.fetch = originalFetch;
  }
});

// ── 2. TaskPoller State Machine & Polling Coordinator Tests ───────────────────

test("TaskPoller starts polling and completes on task success", async () => {
  let pollCount = 0;
  const successResults = [];

  const mockFetchTask = async (id) => {
    pollCount++;
    if (pollCount === 1) {
      return { id, status: "queued" };
    }
    return {
      id,
      status: "succeeded",
      result: { total_new: 3, scoring_run_id: "score-1" },
    };
  };

  const poller = new TaskPoller(
    mockFetchTask,
    {
      onSuccess: (task) => {
        successResults.push(task);
      },
      onError: () => {
        assert.fail("onError should not be called on success");
      },
    },
    { intervalMs: 20, timeoutMs: 1000 },
  );

  poller.start("task-success-1");
  assert.equal(poller.active, true);

  // Wait for intervals to execute
  await new Promise((r) => setTimeout(r, 60));

  assert.equal(poller.active, false, "Poller should stop on terminal success");
  assert.equal(successResults.length, 1);
  assert.equal(successResults[0].status, "succeeded");
  assert.equal(successResults[0].result.total_new, 3);
});

test("TaskPoller handles task failure and cleans up state", async () => {
  let errorReceived = null;

  const mockFetchTask = async (id) => {
    return {
      id,
      status: "failed",
      error_message: "Scraper connection timed out on upstream source.",
    };
  };

  const poller = new TaskPoller(
    mockFetchTask,
    {
      onSuccess: () => {
        assert.fail("onSuccess should not be called on failure");
      },
      onError: (err) => {
        errorReceived = err;
      },
    },
    { intervalMs: 20, timeoutMs: 1000 },
  );

  poller.start("task-fail-1");
  await new Promise((r) => setTimeout(r, 40));

  assert.equal(poller.active, false);
  assert.equal(errorReceived, "Scraper connection timed out on upstream source.");
});

test("TaskPoller handles task cancellation", async () => {
  let cancelledTask = null;

  const mockFetchTask = async (id) => {
    return { id, status: "cancelled" };
  };

  const poller = new TaskPoller(
    mockFetchTask,
    {
      onSuccess: () => assert.fail("onSuccess must not be called"),
      onError: () => assert.fail("onError must not be called"),
      onCancelled: (task) => {
        cancelledTask = task;
      },
    },
    { intervalMs: 20, timeoutMs: 1000 },
  );

  poller.start("task-cancelled-1");
  await new Promise((r) => setTimeout(r, 40));

  assert.equal(poller.active, false);
  assert.equal(cancelledTask.status, "cancelled");
});

test("TaskPoller tolerates temporary polling errors without failing the task", async () => {
  let attempt = 0;
  let errorCount = 0;
  let succeededTask = null;

  const mockFetchTask = async (id) => {
    attempt++;
    if (attempt < 3) {
      throw new Error("Temporary network glitch");
    }
    return { id, status: "succeeded", result: { total_new: 1 } };
  };

  const poller = new TaskPoller(
    mockFetchTask,
    {
      onSuccess: (task) => {
        succeededTask = task;
      },
      onError: () => {
        errorCount++;
      },
    },
    { intervalMs: 25, timeoutMs: 1000 },
  );

  poller.start("task-temp-error-1");
  await new Promise((r) => setTimeout(r, 110));

  assert.equal(errorCount, 0, "Temporary network glitches must not trigger onError");
  assert.ok(succeededTask !== null, "Task should complete successfully once network recovers");
  assert.equal(succeededTask.status, "succeeded");
});

test("TaskPoller timeout stops polling without claiming task failed", async () => {
  let timeoutTriggered = false;
  let errorTriggered = false;

  const mockFetchTask = async (id) => {
    return { id, status: "running" };
  };

  const poller = new TaskPoller(
    mockFetchTask,
    {
      onSuccess: () => assert.fail("onSuccess must not be called on timeout"),
      onError: () => {
        errorTriggered = true;
      },
      onTimeout: () => {
        timeoutTriggered = true;
      },
    },
    { intervalMs: 15, timeoutMs: 50 },
  );

  poller.start("task-slow-1");
  await new Promise((r) => setTimeout(r, 80));

  assert.equal(poller.active, false);
  assert.equal(timeoutTriggered, true, "onTimeout must be called");
  assert.equal(errorTriggered, false, "Timeout must not mark the background task as failed");
});

test("Component cleanup stops poller and prevents stale updates", async () => {
  let successCalls = 0;

  const mockFetchTask = async (id) => {
    await new Promise((r) => setTimeout(r, 30));
    return { id, status: "succeeded" };
  };

  const poller = new TaskPoller(
    mockFetchTask,
    {
      onSuccess: () => {
        successCalls++;
      },
      onError: () => {},
    },
    { intervalMs: 20, timeoutMs: 1000 },
  );

  poller.start("task-unmount-1");
  // Component immediately unmounts or cancels
  poller.stop();

  await new Promise((r) => setTimeout(r, 60));
  assert.equal(successCalls, 0, "No callbacks should fire after poller is stopped");
  assert.equal(poller.active, false);
});
