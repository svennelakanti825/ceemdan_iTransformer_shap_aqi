# C2 pre-registration, addendum A2: platform of the real run and its rerun

**Status: approved by the user on 10 Oct 2026. Written before any C2 result exists.**
- No full C2 run has been made, and no `c2x_*` output exists.
- The approved pre-registration `C2_PREREGISTRATION.md` (SHA-256
  c3b38c294ba09b1f872e414d48e40623adb1f9d1382473099c2cc78494debd50) and addendum A1 (SHA-256
  c2d32acd5cbe91dede7cd460ee0ceee2deb029755f0d58964e8d39915e134ed7) are unchanged. This file adds to them, and all
  three are checked by hash before every build.

## A2.1 Section 2, software and hardware

**Before.** Python 3.13.0, xgboost 3.2.0, numpy 2.4.2, pandas 3.0.1 and scipy 1.17.1 on the laptop CPU (Intel
i5-1135G7, Windows 11). The XGBoost thread count is fixed before the run and recorded in the verdict.

**Change.** The real run (C2-T6) and its rerun (C2-T7) are made on Linux x86-64, on a Google Colab CPU runtime.
- The environment is a fresh Python 3.13.0 holding exactly the 13 package versions of `c2_requirements.txt`. These
  include the same xgboost, numpy, pandas and scipy versions as above.
- XGBoost uses 2 threads per fit (n_jobs 2). The number of parallel processes is half the threads the machine
  allows.
- The verdict records the processor, the thread count and the process count.

**Reason.** The evidence is from the C2-T5 platform test of 10 Oct, on the made-up target (`C2_TASK_TRACKER.md`):
- On Linux, the outputs were byte-identical on two processor types (AMD EPYC and Intel Xeon) and at 2 and 8 threads.
  This held for the dry run and for full-size models.
- XGBoost's Windows build gives slightly different models from its Linux build, even with identical inputs. The
  largest arm-mean MAE difference was 0.03, and every decision was the same.
- Most readers and reviewers use Linux or Colab. On Linux they can reproduce the numbers exactly.

## A2.2 Section 10, reproducibility

**Change.** The C2-T7 rerun is made on a Colab machine with a different processor type from C2-T6 if Colab assigns
one, and otherwise on the same type.
- It must give byte-identical `c2x_pooled.csv`, `c2x_city.csv` and `c2x_predictions.npz`.
- It must give the same verdict apart from the provenance block, which names the machine.
- If it is not identical, the rerun is repeated on the processor type of C2-T6. Both outcomes are reported, and the
  first run stays the result of record (section 13).

## A2.3 Interruptions

A run interrupted by Colab resumes from its saved parts, which are stored on Google Drive.
- Each part records the processor that made it.
- The verdict lists those processors, so a resumed run that mixed machines is visible.

**Unchanged:**
- every rule, threshold, test, statistic, arm, seed, input and sentence of the wording;
- a real run uses the CPU, never the GPU;
- the verdict records the hashes of all three files.
