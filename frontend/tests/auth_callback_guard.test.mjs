import test from "node:test";
import assert from "node:assert/strict";

/**
 * Unit test simulating React Strict Mode and effect guard behavior
 * for the Google OAuth handoff code exchange.
 */
test("exchange guard executes exchange exactly once under React Strict Mode double-invocation", async () => {
  let exchangeCallCount = 0;
  const exchangedCodes = [];

  // Simulated exchange function
  async function mockExchangeGoogleCode(code) {
    exchangeCallCount++;
    exchangedCodes.push(code);
    return { access_token: "mock_jwt_token", token_type: "bearer" };
  }

  // Simulated component ref guard (as implemented in CallbackContent)
  const exchangedCodeRef = { current: null };

  function simulateEffectExecution(code) {
    if (!code) return;
    if (exchangedCodeRef.current === code) {
      return; // Guard prevents duplicate invocation
    }
    exchangedCodeRef.current = code;
    return mockExchangeGoogleCode(code);
  }

  const handoffCode = "valid_handoff_code_123";

  // 1. First mount in React Strict Mode
  const promise1 = simulateEffectExecution(handoffCode);

  // 2. Strict mode immediate remount / re-run of effect with same code
  const promise2 = simulateEffectExecution(handoffCode);

  // 3. Additional state change / dependency update with same code
  const promise3 = simulateEffectExecution(handoffCode);

  await promise1;
  assert.equal(promise2, undefined, "Second execution should be blocked by guard");
  assert.equal(promise3, undefined, "Third execution should be blocked by guard");

  assert.equal(exchangeCallCount, 1, "exchangeGoogleCode must be called exactly once");
  assert.deepEqual(exchangedCodes, [handoffCode]);
});

test("exchange guard permits new code if a different callback code is provided later", async () => {
  let exchangeCallCount = 0;
  const exchangedCodeRef = { current: null };

  function simulateEffectExecution(code) {
    if (!code) return;
    if (exchangedCodeRef.current === code) return;
    exchangedCodeRef.current = code;
    exchangeCallCount++;
  }

  simulateEffectExecution("code_attempt_1");
  simulateEffectExecution("code_attempt_1"); // duplicate blocked
  assert.equal(exchangeCallCount, 1);

  simulateEffectExecution("code_attempt_2"); // new code allowed
  simulateEffectExecution("code_attempt_2"); // duplicate blocked
  assert.equal(exchangeCallCount, 2);
});
