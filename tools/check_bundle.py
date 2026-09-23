"""Check self-contained installs and public Markdown links, without network access."""
from pathlib import Path
import re

root = Path(__file__).resolve().parents[1]
skills = [root / "project_039_skill_ai-video-director", root / "project_040_skill_ai-video-quick"]
for rel in ("scripts/video_pipeline.py", "references/providers.md", "references/production-contract.md"):
    assert (skills[0] / rel).read_bytes() == (skills[1] / rel).read_bytes(), f"Independent copies drifted: {rel}"
count = 0
for file in root.rglob("*.md"):
    if any(x in file.parts for x in ("work", ".git")):
        continue
    for target in re.findall(r'\]\(([^)]+)\)', file.read_text(encoding="utf-8")):
        if "://" in target or target.startswith("#"):
            continue
        path = (file.parent / target.split("#")[0]).resolve()
        assert path.is_file(), f"Broken link in {file.relative_to(root)}: {target}"
        count += 1
for skill in skills:
    text = (skill / "SKILL.md").read_text(encoding="utf-8")
    assert text.startswith("---\n") and text.count("---") >= 2
    name = re.search(r'^name: (.+)$', text, re.M).group(1)
    assert re.fullmatch(r'[a-z0-9-]{1,64}', name)
    assert "$" + name in (skill / "agents/openai.yaml").read_text(encoding="utf-8")
print(f"PASS: two independent skill installs, matching helpers, {count} local document links")
