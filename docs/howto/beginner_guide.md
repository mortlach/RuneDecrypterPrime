# Hello Cipher — First Steps (Beginner Guide)

*Goal:* get a first, successful solve in a few minutes, understand the idea at a high level, and learn how to make one small change and re‑run. Use whichever workflow you prefer (IDE, terminal, notebook, or Python interpreter).

---

## 1) What you’re about to do

* Open the ready‑made **Hello Cipher** tutorial.
* Press **Run** and watch it solve a short message.
* Change **one setting** and run again to see the effect.
* Learn the five ideas the app uses (cipher, key, scorer, strategy, device).

If you enjoy that, there’s a tiny starter script template at the end so you can write your own.

---

## 2) Run your first solve (no setup tricks)

1. Open the tutorials folder and look for the Vigenère tutorial (the name will mention *Vigenère* or *GeneralMap*).
2. Open the file and run it with your preferred tool.
3. You should see a short summary in the console and a solved plaintext. The run also writes a small audit trail under an `output/` folder so you can repeat or share the result later.

> If you don’t have a GPU, that’s fine—the code will use the CPU with the **same meaning** to the numbers.

---

## 3) What just happened (the five ideas)

Think of the app as five simple boxes:

* **Cipher** — the maths used to turn text into secret text and back again (e.g., Vigenère).
* **Key** — the small set of numbers the cipher needs (e.g., a list of shifts).
* **Scorer** — a way to tell if a guess “looks right” (e.g., language‑like text scores higher).
* **Strategy** — how we search for better keys (Simulated Annealing, Genetic Algorithm, or Hybrid).
* **Device** — where the work runs (CPU by default; GPU if available). Meaning stays the same.

One more: a **seed** makes the run **repeatable**. Same seed ⇒ same path ⇒ same result.

---

## 4) Make one small change and re‑run

Open the tutorial file you just ran and try any one of these:

* **Change the key length** (e.g., from 7 to 5). Look for a number near a setting called *key* or *length* and change it.
* **Switch strategy** (e.g., from SA to GA). Look for a line that names the optimiser and swap the name.
* **Toggle device** (e.g., "auto" to "cpu"). If you have a GPU, try "cuda" and see that the answer is the same, just faster.

> Tip: keep the **seed** the same when you change one thing. That way you can tell which change made the difference.

---

## 5) Your first tiny script (paste into a new file)

This is a small, IDE‑friendly template. The only line you may need to adjust is the **import**: copy the import used at the top of the tutorial you just ran and use it here.

```python
# hello_cipher.py — minimal example
# 1) Copy the import style from the tutorial you just ran.
from rune_decrypter_prime.api import run   # or: from rune_decrypter_prime.api import RunAPI

# 2) A tiny sample message (you can paste your own later)
sample_text = "ᚦᛖᚱᛖ ᚹᚪᛋ ᚪ ᛏᚪᛒᛚᛖ"  # or use a short text from the tutorial

# 3) Minimal settings — simple and readable
config = {
    "cipher": "vigenere",             # which maths
    "key_model": {"length": 7},       # how long the key is
    "objective": "language_lm",       # what “good” means
    "device": "auto",                 # cpu by default; gpu if available
    "seed": 1234,                      # repeatable result
    "budget": {"iterations": 10_000}, # how long to search
    "telemetry": {"redact_identity": True},  # safe to share outputs
}

# 4) Run — function style or class style, depending on your import
try:
    result = run(text=sample_text, **config)           # function style
except NameError:
    from rune_decrypter_prime.api import RunAPI        # class style fallback
    result = RunAPI().run(text=sample_text, **config)

# 5) Show the essentials
print("best key:", getattr(result, "best_key", None))
print("plaintext:", getattr(result, "best_plaintext", None))
print("output folder:", getattr(result, "output_dir", "./output"))
```

> If your environment says an import name is different, copy the import line from the tutorial and paste it over the import here. Keep the rest the same.

---

## 6) Where did the files go?

Every run writes a little bundle under `output/` with what you ran, the seed, and the result. This makes it easy to re‑run exactly the same thing later, or share it with a friend without leaking your computer’s name.

---

## 7) Common bumps and easy fixes

* **“No GPU found”** — the run uses the CPU automatically. Results mean the same thing; they may just take a bit longer.
* **“Unknown characters in text”** — start with the sample text in the tutorial, then paste your own. If you see an error, it will point out the character it didn’t understand.
* **“Permission denied when writing output”** — pick a folder you can write to, or run from your home directory.

---

## 8) What to try next

* Swap the **cipher** to a different one and re‑run.
* Change the **key length** and see when the answer gets better or worse.
* Run **SA vs GA** with the same seed and compare.
* Paste your own short message as the input and run with the same simple settings.

Keep it small, keep the seed, change one thing at a time—that’s the quickest way to learn what each knob does.

---

## 9) A quick mental model (why this works)

* The solver makes a lot of **guesses** for the key.
* The scorer tells it which guesses look **more like real language**.
* The strategy keeps the **better** guesses and tries **variations** of them.
* After a while it settles on a key and the plaintext that make the most sense.

That’s it. When you’re ready to go deeper, you can explore custom ciphers and keys—but this first run is the sweet spot to get moving fast and have fun.
