#!/usr/bin/env python3
"""Local planning, job accounting, editing and QA. Never submits paid jobs."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".pending")
    temp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(value, minimum=0):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= minimum


def integer(value, minimum=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def local(root, relative):
    require(isinstance(relative, str) and relative, "A project-relative file path is required")
    require(not Path(relative).is_absolute(), "Absolute asset paths are not portable; import into the project")
    candidate = (root / relative).resolve()
    require(candidate.is_relative_to(root.resolve()), "Path escapes project root")
    return candidate


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def run(command, cwd=None):
    result = subprocess.run([str(x) for x in command], cwd=cwd, capture_output=True, text=True,
                            encoding="utf-8", errors="replace", stdin=subprocess.DEVNULL)
    if result.returncode:
        raise RuntimeError(f"{Path(str(command[0])).name} failed ({result.returncode}): {result.stderr[-2500:]}")
    return result


def executable(name):
    found = os.environ.get(name.upper()) or shutil.which(name)
    require(found, f"Missing {name}; install it or set {name.upper()} to its executable path")
    return found


def probe(file):
    return json.loads(run([executable("ffprobe"), "-v", "error", "-count_frames", "-show_streams",
                           "-show_format", "-of", "json", file]).stdout)


@contextmanager
def lock(root):
    path = root / ".pipeline.lock"
    try:
        descriptor = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError("Project is locked; verify the original process ended before removing a stale lock")
    try:
        os.write(descriptor, f"pid={os.getpid()} {now()}".encode())
        os.close(descriptor)
        yield
    finally:
        path.unlink(missing_ok=True)


def load_project(project):
    root = Path(project).resolve()
    return root, read(root / "production.json")


def validation(m, root, ready=False):
    require(m.get("schema_version") == 1, "Unsupported schema_version")
    require(m.get("mode") in ("full", "quick"), "mode must be full or quick")
    v = m["video"]
    for key in ("width", "height", "fps", "target_frames"):
        require(integer(v.get(key), 1), f"video.{key} must be a positive integer")
    require(v["width"] % 2 == 0 and v["height"] % 2 == 0, "H.264 dimensions must be even")
    require(1 <= v["fps"] <= 120, "Invalid fps")
    if m["mode"] == "quick":
        require(v["target_frames"] <= 30 * v["fps"], "Quick samples cannot exceed 30 seconds")
    shots = m.get("shots", [])
    require(shots, "No authored shots; init only creates a scaffold")
    require(len({s["id"] for s in shots}) == len(shots), "Duplicate shot ID")
    total = 0
    for s in shots:
        require(re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", s["id"]), "Unsafe shot ID")
        require(integer(s.get("frames"), 1), f"{s['id']}: frames must be positive")
        total += s["frames"]
        for key in ("purpose", "image_prompt", "camera_prompt", "action_prompt"):
            require(isinstance(s.get(key), str) and s[key].strip(), f"{s['id']}: missing {key}")
        if ready:
            source = s.get("source") or {}
            path = local(root, source.get("file"))
            require(path.is_file(), f"{s['id']}: source file missing")
            start, end = source.get("in"), source.get("out")
            require(number(start) and number(end) and end > start, "Invalid source interval")
            review = s.get("review", {})
            require(review.get("status") == "accepted", f"{s['id']}: source has not been visually accepted")
            require(review.get("sha256") == sha(path), f"{s['id']}: source changed after review")
            require(number(review.get("in")) and number(review.get("out")), "Reviewed source interval is missing")
            require(review.get("in") <= start and review.get("out") >= end,
                    f"{s['id']}: selected interval extends beyond reviewed range")
            info = probe(path)
            video_stream = next((x for x in info["streams"] if x["codec_type"] == "video"), None)
            require(video_stream is not None, "Source contains no video")
            source_duration = float(video_stream.get("duration", info["format"]["duration"]))
            require(end <= source_duration + .002, f"{s['id']}: source out exceeds video duration")
            ratio = (s["frames"] / v["fps"]) / (end - start)
            require(.8 <= ratio <= 1.25 or source.get("retime_approved") is True,
                    f"{s['id']}: large speed change requires explicit retime_approved")
    require(total == v["target_frames"], f"Timeline is {total} frames; expected {v['target_frames']}")
    end = 0
    for caption in m.get("captions", []):
        a, b = caption["start_frame"], caption["end_frame"]
        require(integer(a) and integer(b, 1) and a >= end and a < b <= total, "Overlapping/out-of-range caption")
        require(isinstance(caption.get("text"), str) and caption["text"].strip(), "Empty caption")
        end = b
    for track in m.get("audio", []):
        require(track.get("role") in ("voice", "music", "fx"), "Audio role must be voice/music/fx")
        require(integer(track.get("start_frame")) and track["start_frame"] < total, "Invalid audio start")
        require(number(track.get("in")) and number(track.get("out")) and track["out"] > track["in"], "Invalid audio interval")
        require(number(track.get("gain_db", 0), -96) and track.get("gain_db", 0) <= 24, "Invalid gain_db")
        for key in ("fade_in", "fade_out"):
            require(number(track.get(key, 0)), f"Invalid {key}")
            require(track.get(key, 0) <= track["out"] - track["in"], f"{key} exceeds track duration")
        path = local(root, track["file"])
        if ready:
            require(path.is_file(), f"Missing audio: {track['file']}")
            media = probe(path)
            require(any(x["codec_type"] == "audio" for x in media["streams"]), "Audio asset has no audio stream")
            require(track["out"] <= float(media["format"]["duration"]) + .02, "Audio out exceeds source")
    if ready and m.get("audio_required", True):
        require(m.get("audio") or any(s.get("native_audio") for s in shots), "Required sound is missing")
    return {"shots": len(shots), "frames": total, "seconds": total / v["fps"], "ready": ready}


def shot_by_id(m, shot_id):
    result = next((s for s in m["shots"] if s["id"] == shot_id), None)
    require(result is not None, f"Unknown shot: {shot_id}")
    return result


def init(args):
    root = Path(args.project).resolve()
    require(not (root / "production.json").exists(), "Existing project: resume rather than initialize again")
    duration = Decimal(str(args.duration if args.duration is not None else (15 if args.mode == "quick" else 60)))
    fps = args.fps or (30 if args.mode == "quick" else 24)
    frames = duration * fps
    require(frames > 0 and frames == frames.to_integral_value(), "Duration must be a positive integer number of frames")
    require(args.mode != "quick" or duration <= 30, "Quick mode is limited to 30 seconds")
    aspect = args.aspect or ("9:16" if args.mode == "quick" else "16:9")
    w, h = {"16:9": (1920, 1080), "9:16": (1080, 1920), "1:1": (1080, 1080)}[aspect]
    root.mkdir(parents=True, exist_ok=True)
    for folder in ("assets", "sources", "audio", "receipts", "work", "outputs", "qa"):
        (root / folder).mkdir(exist_ok=True)
    save(root / "production.json", {"schema_version": 1, "mode": args.mode, "idea": args.idea,
         "video": {"width": w, "height": h, "fps": fps, "target_frames": int(frames)},
         "audio_required": True, "burn_captions": True, "assets": [], "shots": [], "audio": [], "captions": [],
         "authorization": {"paid_generation": False, "external_uploads": False, "credit_limit": None},
         "status": "PLANNING"})
    save(root / "jobs.json", {"schema_version": 1, "jobs": []})
    return {"project": str(root), "status": "PLANNING", "note": "Author the plan; no media has been generated"}


def reserve(args):
    root, m = load_project(args.project)
    require(m["authorization"].get("paid_generation") is True, "Paid generation authorization missing")
    cap = m["authorization"].get("credit_limit")
    require(number(cap) and number(args.estimate, .0001), "A user-authorized credit limit and positive estimate are required")
    shot_by_id(m, args.shot)
    request = read(local(root, args.request))
    # Hash the private request exactly. Uncertain prior attempts block different requests too.
    fingerprint = hashlib.sha256(json.dumps(request, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    with lock(root):
        ledger = read(root / "jobs.json")
        previous = [j for j in ledger["jobs"] if j["shot_id"] == args.shot]
        require(not any(j["status"] in ("RESERVED", "SUBMITTED", "UNKNOWN") for j in previous),
                "Unresolved prior request: reconcile its receipt/task; do not resubmit")
        require(not previous or bool(args.retry_authorization), "Another attempt requires explicit user retry authorization")
        used = sum(j["actual_credits"] if j.get("actual_credits") is not None else j["estimate_credits"] for j in ledger["jobs"])
        require(used + args.estimate <= cap, f"Credit reserve would exceed limit: {used}+{args.estimate}>{cap}")
        attempt = len(previous) + 1
        key = f"{args.shot}-a{attempt}"
        ledger["jobs"].append({"key": key, "shot_id": args.shot, "status": "RESERVED", "created": now(),
                              "request": args.request, "fingerprint": fingerprint, "estimate_credits": args.estimate,
                              "actual_credits": None, "generation_id": None,
                              "retry_authorization": args.retry_authorization or None})
        save(root / "jobs.json", ledger)
    return {"job": key, "status": "RESERVED", "reserved_total": used + args.estimate,
            "note": "Local guard only, not a provider-enforced spending cap"}


def record(args):
    root, _ = load_project(args.project)
    require(args.credits is None or number(args.credits), "credits must be a nonnegative actual amount")
    receipt = local(root, args.receipt)
    require(receipt.is_file(), "Persist the raw provider receipt first")
    with lock(root):
        ledger = read(root / "jobs.json")
        job = next((j for j in ledger["jobs"] if j["key"] == args.job), None)
        require(job is not None, "Unknown reserved job")
        transitions = {"RESERVED": {"SUBMITTED", "UNKNOWN", "FAILED"},
                       "SUBMITTED": {"SUBMITTED", "UNKNOWN", "SUCCEEDED", "FAILED"},
                       "UNKNOWN": {"UNKNOWN", "SUBMITTED", "SUCCEEDED", "FAILED"},
                       "SUCCEEDED": {"SUCCEEDED"}, "FAILED": {"FAILED"}}
        require(args.status in transitions[job["status"]], "Invalid job status transition")
        if job.get("generation_id") and args.generation_id:
            require(job["generation_id"] == args.generation_id, "Cannot replace a paid generation ID")
        if args.generation_id:
            require(not any(j["key"] != job["key"] and j.get("generation_id") == args.generation_id for j in ledger["jobs"]),
                    "generation_id already belongs to another attempt")
        if args.status in ("SUBMITTED", "SUCCEEDED"):
            require(args.generation_id or job.get("generation_id"), "Provider generation ID required")
        job.update(status=args.status, updated=now(), receipt=args.receipt)
        job.setdefault("events", []).append({"status": args.status, "receipt": args.receipt,
                                              "receipt_sha256": sha(receipt), "actual_credits": args.credits, "time": now()})
        if args.generation_id:
            job["generation_id"] = args.generation_id
        if args.credits is not None:
            job["actual_credits"] = args.credits
        save(root / "jobs.json", ledger)
    return job


def accept(args):
    root, m = load_project(args.project)
    s = shot_by_id(m, args.shot)
    require(args.notes.strip(), "Document what you inspected, including unresolved limitations")
    require(s.get("source"), "Set source file/in/out before acceptance")
    with lock(root):
        s["review"] = {"status": "accepted", "sha256": sha(local(root, s["source"]["file"])),
                       "in": s["source"]["in"], "out": s["source"]["out"], "notes": args.notes, "time": now()}
        save(root / "production.json", m)
    return {"shot": s["id"], "review": s["review"], "note": "Self-reported visual review, not automatic certification"}


def srt_time(frame, fps):
    ms = round(frame * 1000 / fps)
    h, ms = divmod(ms, 3600000)
    minute, ms = divmod(ms, 60000)
    sec, ms = divmod(ms, 1000)
    return f"{h:02}:{minute:02}:{sec:02},{ms:03}"


def tempo(ratio):
    parts = []
    while ratio > 2:
        parts.append("atempo=2")
        ratio /= 2
    while ratio < .5:
        parts.append("atempo=0.5")
        ratio /= .5
    return ",".join(parts + [f"atempo={ratio:.10f}"])


def assemble(args):
    root, m = load_project(args.project)
    validation(m, root, ready=True)
    ff = executable("ffmpeg")
    v = m["video"]
    fps, duration = v["fps"], v["target_frames"] / v["fps"]
    target = local(root, "outputs/" + args.output)
    require(target.is_relative_to((root / "outputs").resolve()), "Output must stay in outputs/")
    require(target.suffix.lower() == ".mp4", "Output must be an MP4")
    require(not target.exists(), "Final already exists; choose a new --output name")
    with lock(root):
        work = root / "work" / ("render-" + datetime.now().strftime("%Y%m%d-%H%M%S-%f"))
        work.mkdir(parents=True)
        audios = list(m.get("audio", []))
        cursor = 0
        for i, s in enumerate(m["shots"]):
            src = s["source"]
            length = src["out"] - src["in"]
            seconds = s["frames"] / fps
            vf = (f"trim=start={src['in']}:end={src['out']},setpts=(PTS-STARTPTS)*{seconds/length:.12f},"
                  f"scale={v['width']}:{v['height']}:force_original_aspect_ratio=decrease,"
                  f"pad={v['width']}:{v['height']}:(ow-iw)/2:(oh-ih)/2,setsar=1,"
                  f"fps={fps},tpad=stop_mode=clone:stop_duration={2/fps:.12f},format=yuv420p")
            part = work / f"segment-{i:04}.mp4"
            run([ff, "-v", "error", "-i", local(root, src["file"]), "-vf", vf, "-an", "-frames:v", s["frames"],
                 "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-video_track_timescale", fps * 1000, part])
            stream = next(x for x in probe(part)["streams"] if x["codec_type"] == "video")
            require(int(stream["nb_read_frames"]) == s["frames"], f"{s['id']}: normalized segment frame mismatch")
            if s.get("native_audio"):
                native = work / f"native-{i:04}.wav"
                run([ff, "-v", "error", "-i", local(root, src["file"]), "-vn", "-af",
                     f"atrim=start={src['in']}:end={src['out']},asetpts=PTS-STARTPTS,{tempo(length/seconds)},apad",
                     "-t", seconds, "-ar", "48000", "-ac", "2", native])
                audios.append({"file": native.relative_to(root).as_posix(), "role": "fx", "start_frame": cursor,
                               "in": 0, "out": seconds, "gain_db": 0})
            cursor += s["frames"]
        (work / "concat.txt").write_text("".join(f"file 'segment-{i:04}.mp4'\n" for i in range(len(m["shots"]))), encoding="utf-8")
        run([ff, "-v", "error", "-f", "concat", "-safe", "1", "-i", "concat.txt", "-c", "copy", "picture.mp4"], cwd=work)
        if m.get("captions"):
            srt = "\n\n".join(f"{i+1}\n{srt_time(c['start_frame'],fps)} --> {srt_time(c['end_frame'],fps)}\n{c['text']}"
                                for i, c in enumerate(m["captions"])) + "\n"
            (work / "captions.srt").write_text(srt, encoding="utf-8")
        if audios:
            filters, groups, command = [], {"voice": [], "music": [], "fx": []}, [ff, "-v", "error"]
            for i, a in enumerate(audios):
                command += ["-i", str(local(root, a["file"]))]
                length = a["out"] - a["in"]
                fadein, fadeout = a.get("fade_in", 0), a.get("fade_out", 0)
                chain = (f"[{i}:a]atrim=start={a['in']}:end={a['out']},asetpts=PTS-STARTPTS,"
                         f"aresample=48000,aformat=channel_layouts=stereo,volume={a.get('gain_db',0)}dB")
                if fadein:
                    chain += f",afade=t=in:d={fadein}"
                if fadeout:
                    chain += f",afade=t=out:st={length-fadeout}:d={fadeout}"
                chain += f",adelay={round(a['start_frame']*1000/fps)}:all=1,apad,atrim=duration={duration}[a{i}]"
                filters.append(chain)
                groups[a["role"]].append(f"[a{i}]")
            for group, labels in groups.items():
                if labels:
                    filters.append("".join(labels) + f"amix=inputs={len(labels)}:normalize=0[{group}]")
            final = [f"[{k}]" for k, labels in groups.items() if labels]
            if groups["voice"] and groups["music"]:
                filters += ["[voice]asplit=2[voiceout][duck]",
                            "[music][duck]sidechaincompress=threshold=0.03:ratio=4:attack=20:release=250[bed]"]
                final = ["[voiceout]", "[bed]"] + (["[fx]"] if groups["fx"] else [])
            filters.append("".join(final) + f"amix=inputs={len(final)}:normalize=0,alimiter=limit=0.95:level=0[out]")
            # Float intermediate avoids clipping before the two-pass loudness stage.
            run(command + ["-filter_complex", ";".join(filters), "-map", "[out]", "-t", duration,
                           "-c:a", "pcm_f32le", work / "mix.wav"])
            measured = run([ff, "-hide_banner", "-i", work / "mix.wav", "-af",
                            "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"]).stderr
            match = re.search(r'\{\s*"input_i".*?\}', measured, re.S)
            require(match, "Loudness measurement unavailable")
            data = json.loads(match.group())
            require(all(math.isfinite(float(data[k])) for k in ("input_i", "input_tp", "input_lra", "input_thresh", "target_offset")),
                    "Required audio is silent or cannot be normalized")
            af = (f"loudnorm=I=-16:TP=-1.5:LRA=11:measured_I={data['input_i']}:measured_TP={data['input_tp']}:"
                  f"measured_LRA={data['input_lra']}:measured_thresh={data['input_thresh']}:offset={data['target_offset']}:linear=true")
            run([ff, "-v", "error", "-i", work / "mix.wav", "-af", af, "-ar", "48000", "-ac", "2", work / "master.wav"])
        command = [ff, "-v", "error", "-i", "picture.mp4"]
        if audios:
            command += ["-i", "master.wav", "-map", "0:v:0", "-map", "1:a:0", "-c:a", "aac", "-b:a", "192k"]
        else:
            command += ["-an"]
        if m.get("captions") and m.get("burn_captions", True):
            command += ["-vf", "subtitles=captions.srt:force_style='FontSize=18,MarginV=24,Outline=1'", "-c:v", "libx264", "-crf", "18"]
        else:
            command += ["-c:v", "copy"]
        staged = work / "final.mp4"
        run(command + ["-t", duration, "-movflags", "+faststart", staged.name], cwd=work)
        report = qa_file(root, m, staged)
        require(report["technical_pass"], "Export failed technical QA; intermediate files retained")
        target.parent.mkdir(parents=True, exist_ok=True)
        require(not target.exists(), "Output appeared during render; refusing overwrite")
        shutil.copyfile(staged, target)
        if (work / "captions.srt").exists():
            shutil.copyfile(work / "captions.srt", target.with_suffix(".srt"))
        run([ff, "-v", "error", "-i", target, "-frames:v", "1", target.with_name(target.stem + "-cover.jpg")])
        save(root / "qa" / (target.stem + "-technical.json"), report)
    return {"video": str(target), "technical_pass": True, "final_visual_and_listening_review": "REQUIRED"}


def qa_file(root, m, file):
    info = probe(file)
    v = next((x for x in info["streams"] if x["codec_type"] == "video"), None)
    require(v is not None, "No video stream")
    audio = [x for x in info["streams"] if x["codec_type"] == "audio"]
    spec = m["video"]
    count = int(v.get("nb_read_frames", 0))
    checks = {"frames": count == spec["target_frames"], "dimensions": (v["width"], v["height"]) == (spec["width"], spec["height"]),
              "fps": abs(float(__import__('fractions').Fraction(v["avg_frame_rate"])) - spec["fps"]) < .001,
              "duration": abs(float(v.get("duration", info["format"]["duration"])) - spec["target_frames"] / spec["fps"]) <= 1/spec["fps"],
              "audio_present_if_required": bool(audio) or not m.get("audio_required", True)}
    run([executable("ffmpeg"), "-v", "error", "-xerror", "-i", file, "-f", "null", "-"])
    checks["full_decode"] = True
    loudness = None
    if audio:
        log = run([executable("ffmpeg"), "-hide_banner", "-i", file, "-vn", "-af",
                   "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"]).stderr
        match = re.search(r'\{\s*"input_i".*?\}', log, re.S)
        if match:
            loudness = json.loads(match.group())
            checks["non_silent_audio"] = math.isfinite(float(loudness["input_i"]))
            checks["true_peak_below_0_dbfs"] = float(loudness["input_tp"]) < 0
        else:
            checks["loudness_measurement"] = False
    return {"sha256": sha(file), "checks": checks, "technical_pass": all(checks.values()), "loudness": loudness,
            "frames": count, "visual_review": "NOT_PERFORMED_BY_SCRIPT", "listening": "NOT_PERFORMED_BY_SCRIPT", "time": now()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    for name in ("init", "validate", "reserve", "record", "accept", "assemble", "qa", "frames", "costs"):
        parser = sub.add_parser(name)
        parser.add_argument("--project", required=True)
        if name == "init":
            parser.add_argument("--mode", choices=["full", "quick"], default="full")
            parser.add_argument("--idea", required=True)
            parser.add_argument("--duration", type=float)
            parser.add_argument("--fps", type=int, choices=range(1, 121))
            parser.add_argument("--aspect", choices=["16:9", "9:16", "1:1"])
        if name == "validate":
            parser.add_argument("--ready", action="store_true")
        if name == "reserve":
            parser.add_argument("--shot", required=True)
            parser.add_argument("--request", required=True)
            parser.add_argument("--estimate", type=float, required=True)
            parser.add_argument("--retry-authorization", default="")
        if name == "record":
            parser.add_argument("--job", required=True)
            parser.add_argument("--status", required=True, choices=["SUBMITTED", "UNKNOWN", "SUCCEEDED", "FAILED"])
            parser.add_argument("--receipt", required=True)
            parser.add_argument("--generation-id")
            parser.add_argument("--credits", type=float)
        if name == "accept":
            parser.add_argument("--shot", required=True)
            parser.add_argument("--notes", required=True)
        if name == "assemble":
            parser.add_argument("--output", default="final-v1.mp4")
        if name in ("qa", "frames"):
            parser.add_argument("--file", required=True)
        if name == "frames":
            parser.add_argument("--start", type=float, default=0)
            parser.add_argument("--duration", type=float, default=10)
            parser.add_argument("--rate", type=float, default=3)
            parser.add_argument("--out", default="qa/frames")
    args = p.parse_args()
    if args.command == "doctor":
        result = {n: run([executable(n), "-version"]).stdout.splitlines()[0] for n in ("ffmpeg", "ffprobe")}
        result["provider_check"] = "Agent must discover native image generation and Kling separately"
    elif args.command in ("init", "reserve", "record", "accept", "assemble"):
        result = globals()[args.command](args)
    else:
        root, m = load_project(args.project)
        if args.command == "costs":
            jobs = read(root / "jobs.json")["jobs"]
            known = sum(j["actual_credits"] for j in jobs if j.get("actual_credits") is not None)
            unknown = [j for j in jobs if j.get("actual_credits") is None]
            result = {"actual_credits_known": known, "unknown_cost_attempts": len(unknown),
                      "reserved_for_unknown": sum(j["estimate_credits"] for j in unknown),
                      "complete_actual_bill": not unknown, "attempts": len(jobs),
                      "note": "No currency conversion or refund inferred from balance changes"}
        elif args.command == "validate":
            result = validation(m, root, args.ready)
        elif args.command == "qa":
            result = qa_file(root, m, local(root, args.file))
            save(root / "qa" / "latest-technical.json", result)
            require(result["technical_pass"], "Technical QA failed; see qa/latest-technical.json")
        else:
            require(number(args.start) and number(args.duration, .001) and number(args.rate, .001), "Invalid sampling range")
            require(args.duration * args.rate <= 2000, "Split dense inspection into intervals of at most 2000 frames")
            dest = local(root, args.out)
            require(not dest.exists(), "Choose a fresh frame directory")
            dest.mkdir(parents=True)
            run([executable("ffmpeg"), "-v", "error", "-i", local(root, args.file), "-ss", args.start,
                 "-t", args.duration, "-vf", f"fps={args.rate},scale=960:-2", dest / "frame-%05d.jpg"])
            result = {"directory": str(dest), "images": len(list(dest.glob("*.jpg"))), "inspection": "Still required"}
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, OSError, RuntimeError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(2)
