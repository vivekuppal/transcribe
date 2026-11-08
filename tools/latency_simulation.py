"""Simulated end-to-end lag of the live transcriber with a fake speech to text engine.

The fake engine costs <fixed> + <per_second> x seconds of audio for each request and returns
one numbered word per second of audio, so lost or repeated words can be counted.

    python tools/latency_simulation.py <checkout folder> <old|new> <fixed> <per_second>

"old" = a checkout of the original code (commit 128256e), "new" = this version. Run it with
the app's requirements installed. Time is scaled by K (90 s of speech run in 9 s); every
figure is printed in real-time seconds. The README numbers come from:
    fixed 0.4, per_second 0.05   (cloud API)
    fixed 0.5, per_second 0.35   (slow local engine)
"""
import datetime, sys, threading, time, wave, queue
root, kind, fixed, per = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
sys.path[:0] = [root, root + "/app/transcribe"]
from sdk.transcription_result import TranscriptSegment, TranscriptionHypothesis
from app.transcribe import audio_transcriber as at
import numpy as np

K = 0.1
SPEECH = 90           # seconds of non-stop speech from the other side
PHRASE = 3.0          # recorder phrase length
T0 = datetime.datetime(2026, 1, 1)
lock = threading.Lock()
sent = []
first_seen = {}       # word second -> unscaled time it first appeared
start_wall = None

def cost(seconds):
    time.sleep((fixed + per * seconds) * K)

class Model:
    def _resp(self, seconds):
        with lock: sent.append(seconds)
        cost(seconds)
        return {"seconds": seconds}
    def get_transcription(self, path):
        with wave.open(path) as w: return self._resp(w.getnframes() / w.getframerate())
    def transcribe_pcm(self, data, rate):
        return self._resp(len(data) / 32000)
    def process_response(self, r): return "x" if r and r["seconds"] >= 1 else ""
    def normalize_response(self, r, audio_start_seconds=0.0, audio_end_seconds=0.0):
        words = [(s, f"w{s}") for s in range(int(round(audio_start_seconds)), int(audio_end_seconds))]
        segs = [TranscriptSegment(i // 2, float(c[0][0]), float(c[-1][0] + 1), " ".join(w for _, w in c))
                for i, c in ((i, words[i:i + 2]) for i in range(0, len(words), 2))]
        return TranscriptionHypothesis("fake", " ".join(w for _, w in words), segs,
                                       audio_start_seconds, audio_end_seconds)
    def set_lang(self, l): pass

class Convo:
    rows = []
    def update_conversation(self, persona, time_spoken, text, update_previous=False):
        now = (time.monotonic() - start_wall) / K
        with lock:
            for w in text.split():
                n = int(w[1:]); first_seen.setdefault(n, now)
    def clear_conversation_data(self): pass

class Src: SAMPLE_RATE = 16000; SAMPLE_WIDTH = 2; channels = 1
cfg = {"General": {"clear_transcript_periodically": False, "clear_transcript_interval_seconds": 90,
                   "live_transcription_window_seconds": 30, "live_transcription_mutable_tail_seconds": 5,
                   "live_transcription_stability_passes": 2, "live_transcription_commit_seconds": 10}}
tr = at.WhisperTranscriber(Src(), Src(), Model(), Convo(), cfg)
audio_q = queue.Queue()
threading.Thread(target=tr.transcribe_audio_queue, args=(audio_q,), daemon=True).start()
if kind == "new":
    # scale the tail wait of the new worker the same way as all other time
    for name, qq in tr._source_queues.items():
        def scaled_get(block=True, timeout=None, _q=qq):
            return queue.Queue.get(_q, block, None if timeout is None else timeout * K)
        qq.get = scaled_get
start_wall = time.monotonic()
chunk = np.full(int(PHRASE * 16000), 500, dtype="<i2").tobytes()
for i in range(int(SPEECH / PHRASE)):
    target = start_wall + (i + 1) * PHRASE * K          # phrase i ends at (i+1)*PHRASE
    time.sleep(max(0, target - time.monotonic()))
    audio_q.put(("Speaker", chunk, T0 + datetime.timedelta(seconds=(i + 1) * PHRASE)))
time.sleep(40 * K)
lags = [first_seen[s] - (int(s // PHRASE) + 1) * PHRASE for s in range(SPEECH) if s in first_seen]
missing = [s for s in range(SPEECH) if s not in first_seen]
late = [l for s, l in zip(range(SPEECH), lags) if s >= SPEECH - 30]
print(f"{kind}: requests={len(sent)} audio_sent={sum(sent):.0f}s longest_request={max(sent):.0f}s "
      f"avg_lag={np.mean(lags):.1f}s lag_last_30s={np.mean(late):.1f}s max_lag={max(lags):.1f}s missing_words={len(missing)}")
