"""Print live counts from data/systems. README and site copy point here instead of hard-coding numbers."""
import collections, glob, yaml
cards = [yaml.safe_load(open(p)) for p in sorted(glob.glob("data/systems/*.yaml"))]
print("card files", len(cards), "| status", dict(collections.Counter(c.get("status", "active") for c in cards)))
cards = [c for c in cards if c.get("status", "active") == "active"]
print("active cards", len(cards))
print("era", dict(collections.Counter(c["era"] for c in cards)))
print("code", dict(collections.Counter((c.get("code") or {}).get("status") for c in cards)))
print("generative by year", dict(sorted(collections.Counter(c["year"] for c in cards if c["era"] == "generative").items())))
