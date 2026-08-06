/**
 * lib/navigationHistory.ts
 *
 * Tracks how many pages have been visited in the current browser tab so
 * <BackButton> can tell the difference between:
 *
 *   - The user navigated here from inside the app (Dashboard → Jobs →
 *     Job Detail) — browser history has an app page to go back to.
 *   - The user opened this page directly (typed URL, refreshed a
 *     bookmark, followed an external link) — there is no in-app page
 *     to return to, so we should fall back to a fixed route instead.
 *
 * `window.history.length` is not a reliable signal for this (it counts
 * every entry in the tab, including pages outside the app), so instead
 * we keep our own counter in sessionStorage, bumped once per page via
 * app/template.tsx (which Next.js remounts on every navigation). A new
 * tab/session always starts this counter at zero.
 */

const STORAGE_KEY = "jh_nav_depth";

/** Call once per page mount (see app/template.tsx). Returns the new depth. */
export function markPageVisit(): number {
  if (typeof window === "undefined") return 0;
  try {
    const current = Number(window.sessionStorage.getItem(STORAGE_KEY) ?? "0");
    const next = current + 1;
    window.sessionStorage.setItem(STORAGE_KEY, String(next));
    return next;
  } catch {
    // Private browsing / storage disabled — degrade to "no history".
    return 0;
  }
}

/** True once at least one earlier page has been visited this tab session. */
export function hasInAppHistory(): boolean {
  if (typeof window === "undefined") return false;
  try {
    return Number(window.sessionStorage.getItem(STORAGE_KEY) ?? "0") > 1;
  } catch {
    return false;
  }
}
