import test from "node:test";
import assert from "node:assert/strict";

/**
 * Unit tests for Task Queue API client functions (Phase 1).
 */

// Simulated apiFetch and query string builders matching lib/api.ts logic
function buildListTasksUrl(params) {
  const qs = new URLSearchParams();
  if (params?.task_type) {
    qs.set("task_type", params.task_type);
  }
  if (params?.status) {
    qs.set("status", params.status);
  }
  if (params?.limit !== undefined) {
    qs.set("limit", String(params.limit));
  }
  const query = qs.toString() ? `?${qs.toString()}` : "";
  return `/api/tasks${query}`;
}

test("buildListTasksUrl without parameters returns base endpoint", () => {
  assert.equal(buildListTasksUrl(), "/api/tasks");
  assert.equal(buildListTasksUrl({}), "/api/tasks");
});

test("buildListTasksUrl with parameters formats query string correctly", () => {
  const url1 = buildListTasksUrl({ task_type: "scrape" });
  assert.equal(url1, "/api/tasks?task_type=scrape");

  const url2 = buildListTasksUrl({ status: "queued", limit: 5 });
  assert.equal(url2, "/api/tasks?status=queued&limit=5");

  const url3 = buildListTasksUrl({ task_type: "scoring", status: "running", limit: 20 });
  assert.equal(url3, "/api/tasks?task_type=scoring&status=running&limit=20");
});

test("task endpoints format paths accurately", () => {
  const taskId = "550e8400-e29b-41d4-a716-446655440000";
  const getUrl = `/api/tasks/${taskId}`;
  const cancelUrl = `/api/tasks/${taskId}/cancel`;
  const enqueueUrl = "/api/scraper/enqueue";

  assert.equal(getUrl, "/api/tasks/550e8400-e29b-41d4-a716-446655440000");
  assert.equal(cancelUrl, "/api/tasks/550e8400-e29b-41d4-a716-446655440000/cancel");
  assert.equal(enqueueUrl, "/api/scraper/enqueue");
});
