from __future__ import annotations

from pathlib import Path
import py_compile

REPO_ROOT = Path(__file__).resolve().parents[1]
TARGET = REPO_ROOT / "RuneDecrypterPrime" / "src" / "rune_decrypter_prime" / "scoring" / "rune_scorer.py"

TOP_LEVEL_IMPORT = "from rune_decrypter_prime.scoring.word_ngrams import RuneTokenWordNgramJudgeRuntime\n"
START = "        if self._word_ngram_judge_enabled:\n"
END = "        if not (0.0 < self._span_hamming_ecdf_clamp_min < self._span_hamming_ecdf_clamp_max < 1.0):\n"

REPLACEMENT = """        if self._word_ngram_judge_enabled:
            try:
                from rune_decrypter_prime.scoring.word_ngrams import RuneTokenWordNgramJudgeRuntime
            except ModuleNotFoundError as exc:
                if exc.name == "rune_decrypter_prime.scoring.word_ngrams":
                    raise RuntimeError(
                        "word_ngram_judge_enabled=True, but the experimental word-ngram "
                        "judge module is not present in this V1 release build. "
                        "Disable word_ngram_judge_enabled or install the experimental "
                        "ngram tooling branch."
                    ) from exc
                raise

            self._word_ngram_judge = RuneTokenWordNgramJudgeRuntime.open_sqlite(
                self._word_ngram_judge_sqlite_path,
                alpha=float(self._word_ngram_judge_alpha),
                miss_logp=float(self._word_ngram_judge_miss_logp),
                min_positions=int(self._word_ngram_judge_min_positions),
                prefix_total_thresholds=self._word_ngram_judge_prefix_total_thresholds,
            )
"""


def main() -> int:
    if not TARGET.is_file():
        raise SystemExit(f"Missing target file: {TARGET}")

    text = TARGET.read_text(encoding="utf-8")
    text = text.replace(TOP_LEVEL_IMPORT, "")

    start = text.find(START)
    if start < 0:
        raise SystemExit("Could not find word-ngram enabled block start")
    end = text.find(END, start)
    if end < 0:
        raise SystemExit("Could not find word-ngram enabled block end")

    repaired = text[:start] + REPLACEMENT + text[end:]

    compile(repaired, str(TARGET), "exec")
    if TOP_LEVEL_IMPORT in repaired:
        raise SystemExit("Top-level word_ngrams import is still present")
    if "except ModuleNotFoundError as exc:" not in repaired:
        raise SystemExit("Lazy missing-module error block was not inserted")
    if "try:\n                            except" in repaired:
        raise SystemExit("Broken try/except pattern is still present")

    TARGET.write_text(repaired, encoding="utf-8", newline="\n")
    py_compile.compile(str(TARGET), doraise=True)
    print(f"Repaired and compiled: {TARGET.relative_to(REPO_ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
