# C2 pre-registration, addendum A1: wording when only the origin-day weather passes

**Status: approved by the user on 10 Oct 2026. Written before any C2 result exists.**
- No full C2 run has been made, and no `c2x_*` output exists.
- The approved pre-registration `C2_PREREGISTRATION.md` (SHA-256
  c3b38c294ba09b1f872e414d48e40623adb1f9d1382473099c2cc78494debd50) is unchanged. This file adds to it, and both are
  checked by hash before every build.

## A1. Section 9, the operational sentence when H1 fails and P's H1 passes

**Reason.** The gap was found while the verdict module was implemented (task C2-T4).
- When H1 fails, section 9 gives "No weather claim. Reported as found."
- If P's H1 passes in the same run, the fixed operational sentence "Weather known at the forecast origin also lowers
  the error beyond seasonal climatology (MAE X% lower, 90% interval a to b)." follows it.
- "Also" then refers to nothing.

**Change.** In that case only, the operational sentence is:

"Weather known at the forecast origin lowers the error beyond seasonal climatology (MAE X% lower, 90% interval a to b)."

**Unchanged:**
- every other case uses section 9 as approved;
- no rule, threshold, test, statistic, arm or seed changes;
- the verdict records the hashes of both files.
